"""小说写作流水线：plan → write → review →（revise 循环｜polish）→ save

基于 LangGraph StateGraph，在 plan 后与 review 后用 interrupt() 暂停，等待前端确认/编辑。
状态用 AsyncSqliteSaver 跨请求持久化（thread_id = run_id）。
"""

import json
import re
from datetime import datetime
from typing import Any, Optional, TypedDict

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph, START, END

from .. import storage
from .memory import embed_section
from .prompts import load_skill

CHECKPOINT_DB = storage.DATA_DIR / "checkpoints.sqlite"
_MAX_LOG_FIELD = 8000

_saver: Optional[AsyncSqliteSaver] = None


async def get_saver() -> AsyncSqliteSaver:
    global _saver
    if _saver is None:
        storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(CHECKPOINT_DB))
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        _saver = saver
    return _saver


# ─────────────────────────── helpers ───────────────────────────

def _truncate(text: Any, limit: int = _MAX_LOG_FIELD) -> str:
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= limit else text[:limit] + f"... [截断，共{len(text)}字]"


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _parse_json(text: str) -> dict:
    if not text:
        return {}
    cleaned = _FENCE.sub("", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return {}
        return {}


_META_PATTERNS = [
    r"^正文已创作完成[。，]?",
    r"^创作完成[。，]?",
    r"^本节(写的是|围绕|讲述).*?[。，]",
    r"^以下是.*?[：:]\s*",
    r"^这一节.*?展开[。，]",
]


def _clean_content(text: str) -> str:
    if not text:
        return ""
    original = text
    for pat in _META_PATTERNS:
        text = re.sub(pat, "", text.strip())
    text = text.strip()
    if len(text) < 50 <= len(original):
        return original.strip()
    return text


def _flatten_sections(outline: dict) -> list[dict]:
    out = []
    for vol in outline.get("volumes", []):
        for ch in vol.get("children", []):
            for sec in ch.get("children", []):
                out.append({
                    "id": sec.get("id", ""),
                    "title": sec.get("title", ""),
                    "summary": sec.get("summary", ""),
                    "volume_title": vol.get("title", ""),
                    "chapter_title": ch.get("title", ""),
                })
    return out


def _format_characters(chars: list[dict]) -> str:
    lines = []
    for c in chars:
        lines.append(f"### {c.get('name','')}（{c.get('role','')}）")
        for key, label in [("appearance", "外貌"), ("personality", "性格"), ("background", "背景"),
                           ("current_state", "当前状态"), ("arc", "角色弧"), ("abilities", "能力"),
                           ("speech_style", "说话风格")]:
            if c.get(key):
                lines.append(f"{label}：{c[key]}")
    return "\n".join(lines)


def _format_settings(settings: list[dict]) -> str:
    lines = []
    for s in settings:
        lines.append(f"### {s.get('name','')}（{s.get('category','')}）")
        if s.get("description"):
            lines.append(f"描述：{s['description']}")
        if s.get("notable_features"):
            lines.append("特征：" + "、".join(s["notable_features"]))
    return "\n".join(lines)


def gather_plan_context(novel_id: str, section_id: str) -> dict:
    outline = storage.get_outline(novel_id) or {}
    flat = _flatten_sections(outline)
    idx = next((i for i, s in enumerate(flat) if s["id"] == section_id), -1)
    cur = flat[idx] if idx >= 0 else {"id": section_id, "title": "", "summary": ""}
    prev_s = flat[idx - 1] if idx > 0 else None
    next_s = flat[idx + 1] if 0 <= idx < len(flat) - 1 else None
    chars = storage.get_characters(novel_id)
    settings = storage.get_world_settings(novel_id)
    summaries = storage.get_summaries(novel_id)
    return {
        "section": cur,
        "prev": prev_s,
        "next": next_s,
        "char_names": [c.get("name", "") for c in chars],
        "setting_names": [s.get("name", "") for s in settings],
        "summaries": summaries,
    }


def coerce_plan(raw: dict, ctx: dict) -> dict:
    char_names = set(ctx["char_names"])
    setting_names = set(ctx["setting_names"])
    inv_c = [n for n in (raw.get("involved_characters") or []) if n in char_names]
    inv_s = [n for n in (raw.get("involved_settings") or []) if n in setting_names]
    beats = raw.get("beats") or []
    if isinstance(beats, str):
        beats = [b.strip() for b in beats.splitlines() if b.strip()]
    return {
        "involved_characters": inv_c,
        "involved_settings": inv_s,
        "prev_recap": str(raw.get("prev_recap", "") or ""),
        "this_goal": str(raw.get("this_goal", "") or ""),
        "next_setup": str(raw.get("next_setup", "") or ""),
        "beats": [str(b) for b in beats],
    }


def coerce_review(raw: dict) -> dict:
    issues = raw.get("issues") or []
    norm = []
    for it in issues:
        if isinstance(it, dict):
            norm.append({
                "type": str(it.get("type", "")),
                "severity": str(it.get("severity", "minor")),
                "description": str(it.get("description", "")),
                "suggestion": str(it.get("suggestion", "")),
            })
    return {"ok": bool(raw.get("ok", not norm)), "issues": norm}


def _append_log(novel_id: str, run_id: str, event: dict):
    try:
        log = storage.get_agent_log(novel_id, run_id) or {}
        log.setdefault("events", []).append(event)
        storage.save_agent_log(novel_id, run_id, log)
    except Exception:
        pass


async def _ainvoke_text(llm, system: str, user: str) -> str:
    resp = await llm.ainvoke([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])
    return resp.content if hasattr(resp, "content") else str(resp)


async def _ainvoke_json(llm, system: str, user: str) -> dict:
    return _parse_json(await _ainvoke_text(llm, system, user))


# ─────────────────────────── state ───────────────────────────

class PipelineState(TypedDict, total=False):
    novel_id: str
    section_id: str
    style_id: Optional[str]
    instruction: str
    run_id: str
    plan: dict
    draft: str
    review: dict
    final: str
    action: str


# ─────────────────────────── prompt builders ───────────────────────────

def _plan_user_prompt(ctx: dict, instruction: str) -> str:
    sec = ctx["section"]
    parts = [f"## 任务\n{instruction}",
             f"## 本节\n标题：{sec.get('title','')}\n概要：{sec.get('summary','')}"]
    if ctx.get("prev"):
        parts.append(f"## 前一节（前文）\n标题：{ctx['prev']['title']}\n概要：{ctx['prev']['summary']}")
    if ctx.get("next"):
        parts.append(f"## 后一节（后文）\n标题：{ctx['next']['title']}\n概要：{ctx['next']['summary']}")
    parts.append("## 可用角色名\n" + "、".join(ctx["char_names"] or ["（无）"]))
    parts.append("## 可用世界观设定名\n" + "、".join(ctx["setting_names"] or ["（无）"]))
    sm = ctx.get("summaries") or []
    if sm:
        recap = "\n".join(f"- {s.get('section_title','')}: {s.get('summary','')}" for s in sm[-5:])
        parts.append("## 前文摘要\n" + recap)
    return "\n\n".join(parts)


def _selected_context(novel_id: str, plan: dict) -> str:
    chars = [c for c in storage.get_characters(novel_id) if c.get("name") in set(plan.get("involved_characters", []))]
    settings = [s for s in storage.get_world_settings(novel_id) if s.get("name") in set(plan.get("involved_settings", []))]
    blocks = []
    if chars:
        blocks.append("## 出场角色\n" + _format_characters(chars))
    if settings:
        blocks.append("## 相关设定\n" + _format_settings(settings))
    return "\n\n".join(blocks)


def _write_user_prompt(novel_id: str, section_id: str, plan: dict, style_id: Optional[str]) -> str:
    parts = []
    if style_id:
        style = storage.get_style(novel_id, style_id)
        if style:
            parts.append(f"## 文风要求（自然运用，不要描述如何运用）\n{style.get('content','')}")
    parts.append(f"## 本节目标\n{plan.get('this_goal','')}")
    if plan.get("prev_recap"):
        parts.append(f"## 前文回顾\n{plan['prev_recap']}")
    if plan.get("next_setup"):
        parts.append(f"## 需为后文铺垫\n{plan['next_setup']}")
    if plan.get("beats"):
        parts.append("## 情节节拍\n" + "\n".join(f"{i+1}. {b}" for i, b in enumerate(plan["beats"])))
    sel = _selected_context(novel_id, plan)
    if sel:
        parts.append(sel)
    existing = storage.get_section_content(novel_id, section_id) or ""
    if existing:
        parts.append(f"## 已有内容（参考衔接，{len(existing)}字）\n{existing[:1000]}")
    parts.append("请基于以上信息直接创作本节正文。")
    return "\n\n".join(parts)


def _review_user_prompt(novel_id: str, draft: str, plan: dict) -> str:
    parts = [f"## 本节目标\n{plan.get('this_goal','')}"]
    sel = _selected_context(novel_id, plan)
    if sel:
        parts.append(sel)
    parts.append(f"## 待审正文\n{draft}")
    return "\n\n".join(parts)


def _revise_user_prompt(draft: str, review: dict) -> str:
    issues = review.get("issues", [])
    lines = []
    for it in issues:
        lines.append(f"- [{it.get('severity','')}] {it.get('type','')}：{it.get('description','')}（建议：{it.get('suggestion','')}）")
    issue_text = "\n".join(lines) if lines else "（无具体问题，按整体质量优化措辞与节奏）"
    return (f"## 审查清单（需逐条修正）\n{issue_text}\n\n"
            f"## 原正文\n{draft}\n\n"
            "请根据审查清单逐条修订上面的正文：只改动有问题处，保留其余内容，输出修订后的完整正文。")


# ─────────────────────────── graph ───────────────────────────

def build_graph(llm, checkpointer):
    async def plan_node(state: PipelineState):
        ctx = gather_plan_context(state["novel_id"], state["section_id"])
        sys = load_skill("plan") or "你是小说创作策划，输出 JSON 写作计划。"
        user = _plan_user_prompt(ctx, state.get("instruction", ""))
        raw = await _ainvoke_json(llm, sys, user)
        plan = coerce_plan(raw, ctx)
        _append_log(state["novel_id"], state["run_id"],
                    {"step": "plan", "status": "done", "message": "计划生成完成",
                     "input": _truncate(user), "output": _truncate(json.dumps(plan, ensure_ascii=False))})
        return {"plan": plan}

    async def write_node(state: PipelineState):
        sys = load_skill("write") or "你是专业小说创作者，输出正文。"
        user = _write_user_prompt(state["novel_id"], state["section_id"], state.get("plan", {}), state.get("style_id"))
        draft = _clean_content(await _ainvoke_text(llm, sys, user))
        _append_log(state["novel_id"], state["run_id"],
                    {"step": "write", "status": "done", "message": f"草稿完成（{len(draft)}字）",
                     "input": _truncate(user), "output": _truncate(draft)})
        return {"draft": draft}

    async def review_node(state: PipelineState):
        sys = load_skill("review") or "你是小说审稿人，输出 JSON 问题清单。"
        user = _review_user_prompt(state["novel_id"], state.get("draft", ""), state.get("plan", {}))
        raw = await _ainvoke_json(llm, sys, user)
        review = coerce_review(raw)
        _append_log(state["novel_id"], state["run_id"],
                    {"step": "review", "status": "done", "message": f"审查完成（{len(review['issues'])}个问题）",
                     "input": _truncate(user), "output": _truncate(json.dumps(review, ensure_ascii=False))})
        return {"review": review}

    async def revise_node(state: PipelineState):
        sys = load_skill("revise") or load_skill("rewrite") or "你是小说修订编辑，根据审查清单修订正文，输出完整正文。"
        user = _revise_user_prompt(state.get("draft", ""), state.get("review", {}))
        revised = _clean_content(await _ainvoke_text(llm, sys, user))
        _append_log(state["novel_id"], state["run_id"],
                    {"step": "revise", "status": "done", "message": f"修订完成（{len(revised)}字）",
                     "input": _truncate(user), "output": _truncate(revised)})
        return {"draft": revised}

    async def polish_node(state: PipelineState):
        sys = load_skill("polish") or "你是资深文字编辑，润色正文。"
        polished = _clean_content(await _ainvoke_text(llm, sys, state.get("draft", "")))
        _append_log(state["novel_id"], state["run_id"],
                    {"step": "polish", "status": "done", "message": f"润色完成（{len(polished)}字）",
                     "input": _truncate(state.get("draft", "")), "output": _truncate(polished)})
        return {"final": polished}

    async def save_node(state: PipelineState):
        final = state.get("final") or state.get("draft") or ""
        novel_id, section_id = state["novel_id"], state["section_id"]
        if final:
            storage.save_section_content(novel_id, section_id, final)
            sec = gather_plan_context(novel_id, section_id)["section"]
            embed_section(novel_id, section_id, sec.get("title", ""), final)
        _append_log(novel_id, state["run_id"],
                    {"step": "save", "status": "done", "message": f"已保存正文（{len(final)}字）"})
        return {"final": final}

    async def decide_node(state: PipelineState):
        # 在 review 断点之后运行，确保读取用户恢复时设置的 action
        return {}

    def route_after_review(state: PipelineState) -> str:
        return "revise" if state.get("action") == "revise" else "polish"

    g = StateGraph(PipelineState)
    g.add_node("plan", plan_node)
    g.add_node("write", write_node)
    g.add_node("review", review_node)
    g.add_node("decide", decide_node)
    g.add_node("revise", revise_node)
    g.add_node("polish", polish_node)
    g.add_node("save", save_node)

    g.add_edge(START, "plan")
    g.add_edge("plan", "write")
    g.add_edge("write", "review")
    g.add_edge("review", "decide")
    g.add_conditional_edges("decide", route_after_review,
                            {"revise": "revise", "polish": "polish"})
    g.add_edge("revise", "review")
    g.add_edge("polish", "save")
    g.add_edge("save", END)

    # 静态断点：plan 后暂停（供编辑计划），review 后暂停（供选择修订/润色）
    return g.compile(checkpointer=checkpointer, interrupt_after=["plan", "review"])
