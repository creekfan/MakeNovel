import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/outline", tags=["outline"])


class OutlineNodeUpdate(BaseModel):
    id: str
    title: str
    node_type: str
    summary: str = ""
    status: str = "planned"
    content: Optional[str] = None
    chapter_prompt: Optional[str] = None
    children: list["OutlineNodeUpdate"] = []
    sort_order: float = 0.0


OutlineNodeUpdate.model_rebuild()


class OutlineUpdate(BaseModel):
    novel_id: str
    novel_title: str = ""
    volumes: list[OutlineNodeUpdate] = []


@router.get("")
def get_outline(novel_id: str):
    data = storage.get_outline(novel_id)
    if data is None:
        raise HTTPException(404, "Outline not found")
    return data


def _collect_ids(nodes: list, section_ids: set, node_ids: set):
    for n in nodes:
        node_ids.add(n.get("id", n.get("node_id", "")))
        if n.get("node_type") == "section":
            section_ids.add(n.get("id", ""))
        _collect_ids(n.get("children", []), section_ids, node_ids)


@router.put("")
def update_outline(novel_id: str, body: OutlineUpdate):
    old = storage.get_outline(novel_id) or {}
    old_sections: set[str] = set()
    old_nodes: set[str] = set()
    _collect_ids(old.get("volumes", []), old_sections, old_nodes)

    new_data = body.model_dump()
    new_sections: set[str] = set()
    new_nodes: set[str] = set()
    _collect_ids(new_data.get("volumes", []), new_sections, new_nodes)

    deleted_sections = old_sections - new_sections
    deleted_nodes = old_nodes - new_nodes

    storage.save_outline(novel_id, new_data)

    if deleted_sections:
        storage.delete_section_summaries(novel_id, deleted_sections)
        storage.delete_section_files(novel_id, deleted_sections)
        for sid in deleted_sections:
            try:
                from ..app.memory import delete_section_embedding
                delete_section_embedding(novel_id, sid)
            except Exception:
                pass

    if deleted_nodes:
        storage.delete_canvas_nodes(novel_id, deleted_nodes)

    return {"ok": True}


@router.get("/section/{section_id}/content")
def get_section_content(novel_id: str, section_id: str):
    content = storage.get_section_content(novel_id, section_id)
    return {"section_id": section_id, "content": content or ""}


@router.put("/section/{section_id}/content")
def save_section_content(novel_id: str, section_id: str, body: dict):
    content = body.get("content", "")
    storage.save_section_content(novel_id, section_id, content)
    return {"ok": True}


_GUIDELINES: str = ""
_GUIDELINES_PATH = Path(__file__).resolve().parents[1] / "大纲：矛盾铺设与解决.md"


def _load_guidelines() -> str:
    global _GUIDELINES
    if _GUIDELINES:
        return _GUIDELINES
    try:
        _GUIDELINES = _GUIDELINES_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        _GUIDELINES = "（矛盾铺设与解决方法论文件未找到）"
    return _GUIDELINES


def _outline_context(novel_id: str) -> str:
    """收集小说当前状态的只读摘要上下文。"""
    outline = storage.get_outline(novel_id) or {}
    chars = storage.get_characters(novel_id)
    settings = storage.get_world_settings(novel_id)
    summaries = storage.get_summaries(novel_id)
    flat = _flatten(outline.get("volumes", []))

    parts = []
    parts.append(f"# 小说：{outline.get('novel_title', '未命名')}")

    # 大纲结构（节级别扁平列表）
    tree_lines = []
    for vol in outline.get("volumes", []):
        tree_lines.append(f"\n## {vol.get('title','未命名卷')} [{vol.get('status','')}]")
        if vol.get("summary"):
            tree_lines.append(f"概要：{vol['summary']}")
        for ch in vol.get("children", []):
            tree_lines.append(f"### {ch.get('title','未命名章')} [{ch.get('status','')}]")
            if ch.get("chapter_prompt"):
                tree_lines.append(f"重点：{ch['chapter_prompt']}")
            for sec in ch.get("children", []):
                st = sec.get("status", "planned")
                line = f"- {sec.get('title','未命名')} [{st}]"
                if sec.get("summary"):
                    line += f" 概要：{sec['summary']}"
                tree_lines.append(line)
    parts.append("## 大纲结构\n" + "\n".join(tree_lines))

    # 角色
    char_lines = []
    for c in chars:
        char_lines.append(f"- {c.get('name','')}（{c.get('role','')}）")
        if c.get("personality"):
            char_lines.append(f"  性格：{c['personality'][:80]}")
    parts.append("## 角色（{0}个）\n{1}".format(len(chars), "\n".join(char_lines) or "（无）"))

    # 设定
    set_lines = [f"- {s.get('name','')}（{s.get('category','')}）" for s in settings]
    parts.append("## 世界观设定（{0}个）\n{1}".format(len(settings), "\n".join(set_lines) or "（无）"))

    # 摘要
    sm_lines = [f"- {s.get('section_title','未知')}: {s.get('summary','')[:200]}" for s in (summaries or [])[-10:]]
    parts.append("## 已完成章节摘要\n" + ("\n".join(sm_lines) or "（暂无）"))

    # 已完成正文概要（最近5节）
    done = [s for s in flat if s.get("status") == "done"]
    if done:
        content_lines = []
        for s in done[-5:]:
            txt = (storage.get_section_content(novel_id, s["id"]) or "")[:300]
            content_lines.append(f"### {s['title']}\n{txt}")
        parts.append("## 已完成章节内容概要（最近5节）\n" + "\n".join(content_lines))
    parts.append("\n---\n## 你的对话任务\n请基于以上真实小说状态，严格遵循「矛盾铺设与解决」方法论，回答用户关于大纲设计的问题。你可以建议用户添加新角色或设定来丰富矛盾，但绝不能直接修改数据。回答应具体、可操作。\n---")

    return "\n\n".join(parts)


def _flatten(volumes: list) -> list[dict]:
    result = []
    for vol in volumes:
        for ch in vol.get("children", []):
            for sec in ch.get("children", []):
                result.append({"id": sec.get("id", ""), "title": sec.get("title", ""),
                               "status": sec.get("status", "planned"), "summary": sec.get("summary", "")})
    return result


class AssistantRequest(BaseModel):
    messages: list[dict] = []  # [{role:"user"|"assistant", content:str}, ...]
    api_key: str
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    temperature: float = 0.7


class AssistantReply(BaseModel):
    reply: str


@router.post("/assistant")
async def outline_assistant(novel_id: str, body: AssistantRequest):
    if not body.api_key:
        raise HTTPException(400, "API Key is required")
    if not body.messages:
        raise HTTPException(400, "Messages are required")

    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        api_key=body.api_key,
        base_url=body.base_url,
        model=body.model,
        temperature=body.temperature,
        max_tokens=4096,
    )
    guidelines = _load_guidelines()
    context = _outline_context(novel_id)
    system_prompt = (
        f"你是小说大纲创作助手，帮助作者设计情节与矛盾结构。\n\n"
        f"# 方法论（必须严格遵循）\n{guidelines}\n\n"
        f"{context}"
    )
    msgs = [{"role": "system", "content": system_prompt}]
    for m in body.messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        msgs.append({"role": role if role in ("user", "assistant") else "user", "content": content})

    resp = await llm.ainvoke(msgs)
    reply = resp.content if hasattr(resp, "content") else str(resp)
    return AssistantReply(reply=reply)
