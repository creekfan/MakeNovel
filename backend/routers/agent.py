import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/agent", tags=["agent"])


class PlanParams(BaseModel):
    section_id: str
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    temperature: float = 0.7
    max_tokens: int = 10000
    instruction: str = "请根据本节大纲概要统筹并创作正文"
    style_id: Optional[str] = None


class ResumeParams(BaseModel):
    thread_id: str
    action: str  # confirm_plan | revise | polish
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    temperature: float = 0.7
    max_tokens: int = 10000
    edited_plan: Optional[dict] = None
    edited_draft: Optional[str] = None


class SummrizeRequest(BaseModel):
    section_id: str
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    content: str


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _make_agent(body):
    from ..app.agent import NovelAgent
    return NovelAgent(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )


@router.post("/plan")
async def start_plan(novel_id: str, body: PlanParams):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")
    agent = _make_agent(body)

    async def generate():
        try:
            async for event in agent.start_plan(novel_id, body.section_id, body.instruction, body.style_id):
                yield event
        except Exception as e:
            yield _sse({"step": "error", "status": "error", "message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/resume")
async def resume_pipeline(novel_id: str, body: ResumeParams):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")
    agent = _make_agent(body)

    async def generate():
        try:
            async for event in agent.resume(novel_id, body.thread_id, body.action, body.edited_plan, body.edited_draft):
                yield event
        except Exception as e:
            yield _sse({"step": "error", "status": "error", "message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/summrize")
async def summarize(novel_id: str, body: SummrizeRequest):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")
    if not body.content.strip():
        raise HTTPException(400, "Content is empty")

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise HTTPException(500, "langchain_openai not installed")

    llm = ChatOpenAI(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=0.3,
        max_tokens=4096,
    )

    skills_dir = Path(__file__).resolve().parents[1] / "app" / "skills"
    summary_skill = (skills_dir / "summary.md").read_text(encoding="utf-8") if (skills_dir / "summary.md").exists() else ""

    try:
        result = await llm.ainvoke([
            {"role": "system", "content": summary_skill or "你是小说摘要助手，生成JSON格式摘要。"},
            {"role": "user", "content": body.content},
        ])
    except Exception as e:
        raise HTTPException(502, f"LLM call failed: {e}")

    try:
        parsed = json.loads(result.content)
    except (json.JSONDecodeError, AttributeError):
        content_str = result.content if hasattr(result, "content") else str(result)
        start = content_str.find("{")
        end = content_str.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(content_str[start:end + 1])
            except json.JSONDecodeError:
                parsed = {"summary": content_str, "key_events": [], "character_state_changes": {}, "world_setting_changes": {}}
        else:
            parsed = {"summary": content_str, "key_events": [], "character_state_changes": {}, "world_setting_changes": {}}

    summary_text = parsed.get("detailed_summary") or parsed.get("summary", "")
    key_events = parsed.get("key_events", [])
    character_state = parsed.get("character_state_changes", {})
    world_state = parsed.get("world_setting_changes", {})

    outline = storage.get_outline(novel_id)
    section_title = ""
    if outline:
        def find_title(nodes):
            for n in nodes:
                if n.get("id") == body.section_id:
                    return n.get("title", "")
                r = find_title(n.get("children", []))
                if r is not None:
                    return r
            return None
        section_title = find_title(outline.get("volumes", [])) or ""

    storage.update_outline_node(novel_id, body.section_id, {
        "summary": summary_text,
        "status": "done",
    })

    summaries = storage.get_summaries(novel_id)
    summaries = [s for s in summaries if s.get("section_id") != body.section_id]
    summaries.append({
        "section_id": body.section_id,
        "section_title": section_title,
        "summary": summary_text,
        "key_events": key_events,
        "character_state_changes": character_state,
        "world_setting_changes": world_state,
        "scene_breakdown": parsed.get("scene_breakdown", []),
        "characters_summary": parsed.get("characters_summary", {}),
        "objects_of_interest": parsed.get("objects_of_interest", []),
        "new_elements_introduced": parsed.get("new_elements_introduced", []),
        "conflicts_and_tensions": parsed.get("conflicts_and_tensions", []),
        "unresolved_hooks": parsed.get("unresolved_hooks", []),
    })
    storage.save_summaries(novel_id, summaries)

    return {
        "section_id": body.section_id,
        "summary": summary_text,
        "key_events": key_events,
        "character_state_changes": character_state,
        "world_setting_changes": world_state,
        "scene_breakdown": parsed.get("scene_breakdown", []),
        "characters_summary": parsed.get("characters_summary", {}),
        "objects_of_interest": parsed.get("objects_of_interest", []),
        "new_elements_introduced": parsed.get("new_elements_introduced", []),
        "conflicts_and_tensions": parsed.get("conflicts_and_tensions", []),
        "unresolved_hooks": parsed.get("unresolved_hooks", []),
    }


@router.get("/logs")
def list_logs(novel_id: str):
    return storage.list_agent_logs(novel_id)


@router.get("/logs/{run_id}")
def get_log(novel_id: str, run_id: str):
    log = storage.get_agent_log(novel_id, run_id)
    if log is None:
        raise HTTPException(404, "Log not found")
    return log


@router.delete("/logs/{run_id}")
def delete_log(novel_id: str, run_id: str):
    storage.delete_agent_log(novel_id, run_id)
    return {"ok": True}
