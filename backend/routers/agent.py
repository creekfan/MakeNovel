import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/agent", tags=["agent"])


class AgentRunParams(BaseModel):
    section_id: str
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    temperature: float = 0.7
    max_tokens: int = 4096
    instruction: str = "请阅读当前节的大纲概要，创作正文内容"
    style_id: Optional[str] = None


class SummrizeRequest(BaseModel):
    section_id: str
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    content: str


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/run")
async def run_agent(novel_id: str, body: AgentRunParams):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")

    from ..app.agent import NovelAgent

    agent = NovelAgent(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    async def generate():
        try:
            async for event in agent.astream(novel_id, body.section_id, body.instruction, body.style_id):
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

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=0.3,
        max_tokens=1024,
    )

    skills_dir = Path(__file__).resolve().parents[1] / "app" / "skills"
    summary_skill = (skills_dir / "summary.md").read_text(encoding="utf-8") if (skills_dir / "summary.md").exists() else ""

    result = await llm.ainvoke([
        {"role": "system", "content": summary_skill or "你是小说摘要助手，生成JSON格式摘要。"},
        {"role": "user", "content": body.content},
    ])

    try:
        parsed = json.loads(result.content)
    except (json.JSONDecodeError, AttributeError):
        parsed = {"summary": result.content if hasattr(result, "content") else str(result), "key_events": [], "character_state_changes": {}, "world_setting_changes": {}}

    summary_text = parsed.get("summary", "")
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
    })
    storage.save_summaries(novel_id, summaries)

    return {
        "section_id": body.section_id,
        "summary": summary_text,
        "key_events": key_events,
        "character_state_changes": character_state,
        "world_setting_changes": world_state,
    }
