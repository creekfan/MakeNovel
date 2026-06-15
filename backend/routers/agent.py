import sys
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Generator

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Agent"))

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/agent", tags=["agent"])


class SummarizeRequest(BaseModel):
    section_id: str
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    content: str


class AgentRunRequest(BaseModel):
    section_id: str
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    temperature: float = 0.7
    max_tokens: int = 4096


class AgentSingleRequest(BaseModel):
    section_id: str
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    temperature: float = 0.7
    max_tokens: int = 4096
    agent_name: str
    content: Optional[str] = None


@router.post("/run")
def run_pipeline(novel_id: str, body: AgentRunRequest):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")
    from makenovel_agent.llm import LLMClient, LLMConfig
    from makenovel_agent.models.character import CharacterCard
    from makenovel_agent.models.outline import OutlineTree
    from makenovel_agent.models.summary import SectionSummary
    from makenovel_agent.models.world import WorldSetting
    from makenovel_agent.pipeline import NovelAgentPipeline

    outline_data = storage.get_outline(novel_id)
    if not outline_data:
        raise HTTPException(404, "Outline not found")

    characters_data = storage.get_characters(novel_id)
    world_data = storage.get_world_settings(novel_id)
    summaries_data = storage.get_summaries(novel_id)

    outline_tree = OutlineTree(**outline_data)
    characters = [CharacterCard(**c) for c in characters_data]
    world_settings = [WorldSetting(**w) for w in world_data]
    summaries = [SectionSummary(**s) for s in summaries_data]

    existing_content = storage.get_section_content(novel_id, body.section_id)

    config = LLMConfig(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    llm = LLMClient(config)

    pipeline = NovelAgentPipeline(llm=llm)
    result = pipeline.run(
        section_id=body.section_id,
        outline_tree=outline_tree,
        characters=characters,
        world_settings=world_settings,
        summaries=summaries,
        content_override=existing_content if existing_content else None,
    )

    storage.save_section_content(novel_id, body.section_id, result.final_content)

    return {
        "section_id": result.section_id,
        "final_content": result.final_content,
        "draft_content": result.draft_content,
        "logs": result.logs,
        "review_issues": [i.model_dump() for i in result.review_result.issues],
    }


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/run-stream")
def run_pipeline_stream(novel_id: str, body: AgentRunRequest):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")

    from makenovel_agent.llm import LLMClient, LLMConfig
    from makenovel_agent.models.character import CharacterCard
    from makenovel_agent.models.outline import OutlineTree
    from makenovel_agent.models.summary import SectionSummary
    from makenovel_agent.models.world import WorldSetting
    from makenovel_agent.agents.preparer import PreparerAgent
    from makenovel_agent.agents.creator import CreatorAgent
    from makenovel_agent.agents.reviewer import ReviewerAgent
    from makenovel_agent.agents.reviser import ReviserAgent
    from makenovel_agent.agents.polisher import PolisherAgent

    outline_data = storage.get_outline(novel_id)
    if not outline_data:
        raise HTTPException(404, "Outline not found")

    characters_data = storage.get_characters(novel_id)
    world_data = storage.get_world_settings(novel_id)
    summaries_data = storage.get_summaries(novel_id)

    outline_tree = OutlineTree(**outline_data)
    characters = [CharacterCard(**c) for c in characters_data]
    world_settings = [WorldSetting(**w) for w in world_data]
    summaries = [SectionSummary(**s) for s in summaries_data]

    existing_content = storage.get_section_content(novel_id, body.section_id)

    config = LLMConfig(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    llm = LLMClient(config)
    skills_dir = Path(__file__).resolve().parents[2] / "Agent" / "makenovel_agent" / "skills"

    def generate() -> Generator[str, None, None]:
        try:
            yield _sse_event({"step": "preparer", "status": "running", "message": "准备写作材料..."})
            preparer = PreparerAgent(skills_dir)
            preparation = preparer.prepare(
                section_id=body.section_id,
                outline_tree=outline_tree,
                summaries=summaries,
                characters=characters,
                world_settings=world_settings,
                llm=llm,
            )
            yield _sse_event({
                "step": "preparer", "status": "done",
                "message": f"完成 — 涉及 {len(preparation.involved_characters)} 个角色, {len(preparation.involved_world_settings)} 个设定",
                "detail": {
                    "current_section": preparation.current_section_title,
                    "starting_state": preparation.starting_state,
                    "what_to_write": preparation.what_to_write,
                    "ending_state": preparation.ending_state,
                    "involved_characters": [c.name for c in preparation.involved_characters],
                    "involved_world_settings": [w.name for w in preparation.involved_world_settings],
                    "context_summaries": [s.summary for s in preparation.context_summaries] if preparation.context_summaries else [],
                },
            })

            yield _sse_event({"step": "creator", "status": "running", "message": "创作正文..."})
            creator = CreatorAgent(skills_dir)
            draft = creator.write(
                preparation, llm=llm,
                content=existing_content if existing_content else None,
            )
            yield _sse_event({
                "step": "creator", "status": "done",
                "message": f"完成 — {len(draft)} 字",
                "detail": {"content": draft},
            })

            yield _sse_event({"step": "reviewer", "status": "running", "message": "审查正文..."})
            reviewer = ReviewerAgent(skills_dir)
            review_result = reviewer.review(
                content=draft,
                characters=preparation.involved_characters,
                world_settings=preparation.involved_world_settings,
                llm=llm,
            )
            issue_count = len(review_result.issues)
            yield _sse_event({
                "step": "reviewer", "status": "done",
                "message": f"完成 — 发现 {issue_count} 个问题",
                "detail": {
                    "overall": review_result.overall_assessment,
                    "issues": [
                        {"type": i.issue_type, "severity": i.severity, "description": i.description, "suggestion": i.suggestion}
                        for i in review_result.issues
                    ],
                },
            })

            revised = draft
            if review_result.issues:
                yield _sse_event({"step": "reviser", "status": "running", "message": "修订中..."})
                reviser = ReviserAgent(skills_dir)
                revised = reviser.revise(draft, review_result, llm=llm)
                yield _sse_event({
                    "step": "reviser", "status": "done",
                    "message": "修订完成",
                    "detail": {"content": revised},
                })
            else:
                yield _sse_event({"step": "reviser", "status": "skipped", "message": "无需修订"})

            yield _sse_event({"step": "polisher", "status": "running", "message": "润色中..."})
            polisher = PolisherAgent(skills_dir)
            final = polisher.polish(revised, llm=llm)
            yield _sse_event({
                "step": "polisher", "status": "done",
                "message": f"完成 — 最终 {len(final)} 字",
                "detail": {"content": final},
            })

            storage.save_section_content(novel_id, body.section_id, final)

            yield _sse_event({
                "step": "complete", "status": "done",
                "message": "全部完成",
                "final_content": final,
            })
        except Exception as e:
            yield _sse_event({"step": "error", "status": "error", "message": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/single")
def run_single_agent(novel_id: str, body: AgentSingleRequest):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")
    from makenovel_agent.llm import LLMClient, LLMConfig
    from makenovel_agent.models.character import CharacterCard
    from makenovel_agent.models.outline import OutlineTree
    from makenovel_agent.models.summary import SectionSummary
    from makenovel_agent.models.world import WorldSetting
    from makenovel_agent.agents.preparer import PreparerAgent
    from makenovel_agent.agents.creator import CreatorAgent
    from makenovel_agent.agents.reviewer import ReviewerAgent
    from makenovel_agent.agents.reviser import ReviserAgent
    from makenovel_agent.agents.polisher import PolisherAgent
    from makenovel_agent.models.messages import ReviewResult

    outline_data = storage.get_outline(novel_id)
    if not outline_data:
        raise HTTPException(404, "Outline not found")

    characters_data = storage.get_characters(novel_id)
    world_data = storage.get_world_settings(novel_id)
    summaries_data = storage.get_summaries(novel_id)

    outline_tree = OutlineTree(**outline_data)
    characters = [CharacterCard(**c) for c in characters_data]
    world_settings = [WorldSetting(**w) for w in world_data]
    summaries = [SectionSummary(**s) for s in summaries_data]

    config = LLMConfig(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    llm = LLMClient(config)

    skills_dir = Path(__file__).resolve().parents[2] / "Agent" / "makenovel_agent" / "skills"

    if body.agent_name == "preparer":
        agent = PreparerAgent(skills_dir)
        result = agent.prepare(
            section_id=body.section_id,
            outline_tree=outline_tree,
            summaries=summaries,
            characters=characters,
            world_settings=world_settings,
            llm=llm,
        )
        return {"agent": "preparer", "result": result.model_dump()}

    elif body.agent_name == "creator":
        agent_p = PreparerAgent(skills_dir)
        preparation = agent_p.prepare(
            section_id=body.section_id,
            outline_tree=outline_tree,
            summaries=summaries,
            characters=characters,
            world_settings=world_settings,
            llm=llm,
        )
        agent = CreatorAgent(skills_dir)
        content = agent.write(preparation, llm=llm, content=body.content)
        return {"agent": "creator", "result": content}

    elif body.agent_name == "reviewer":
        if not body.content:
            raise HTTPException(400, "Content required for reviewer")
        agent = ReviewerAgent(skills_dir)
        result = agent.review(
            content=body.content,
            characters=characters,
            world_settings=world_settings,
            llm=llm,
        )
        return {"agent": "reviewer", "result": result.model_dump()}

    elif body.agent_name == "polisher":
        if not body.content:
            raise HTTPException(400, "Content required for polisher")
        agent = PolisherAgent(skills_dir)
        result = agent.polish(body.content, llm=llm)
        return {"agent": "polisher", "result": result}

    else:
        raise HTTPException(400, f"Unknown agent: {body.agent_name}")


SUMMARIZE_SYSTEM_PROMPT = """你是一个小说摘要助手。根据用户提供的小说正文内容，生成结构化摘要。
严格按以下 JSON 格式输出，不要输出其他内容：
{
  "summary": "100-200字的情节概要",
  "key_events": ["关键事件1", "关键事件2", ...],
  "character_state_changes": {"角色名": "状态变化描述", ...},
  "world_setting_changes": {"设定名": "变化描述", ...}
}
如果没有角色状态变化或世界观变化，对应字段返回空对象 {}。"""


@router.post("/summarize")
def summarize_section(novel_id: str, body: SummarizeRequest):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")
    if not body.content.strip():
        raise HTTPException(400, "Content is empty")

    from makenovel_agent.llm import LLMClient, LLMConfig

    config = LLMConfig(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=0.3,
        max_tokens=1024,
    )
    llm = LLMClient(config)

    result = llm.chat_json(
        system_prompt=SUMMARIZE_SYSTEM_PROMPT,
        user_message=body.content,
        temperature=0.3,
        max_tokens=1024,
    )

    summary_text = result.get("summary", "")
    key_events = result.get("key_events", [])
    character_state_changes = result.get("character_state_changes", {})
    world_setting_changes = result.get("world_setting_changes", {})

    outline_data = storage.get_outline(novel_id)
    section_title = ""
    if outline_data:
        def find_title(nodes):
            for n in nodes:
                if n.get("id") == body.section_id:
                    return n.get("title", "")
                r = find_title(n.get("children", []))
                if r is not None:
                    return r
            return None
        section_title = find_title(outline_data.get("volumes", [])) or ""

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
        "character_state_changes": character_state_changes,
        "world_setting_changes": world_setting_changes,
    })
    storage.save_summaries(novel_id, summaries)

    return {
        "section_id": body.section_id,
        "summary": summary_text,
        "key_events": key_events,
        "character_state_changes": character_state_changes,
        "world_setting_changes": world_setting_changes,
    }
