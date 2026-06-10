"""ReAct Agent loop with function calling for autonomous novel writing."""
import json
from typing import AsyncIterator, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import OutlineNode, Character, Setting, Novel
from app.services.llm import (
    _load_action_prompt, build_system_prompt, build_user_prompt,
    stream_ai_response, resolve_model,
)
from app.services.context import build_context
from app.core.config import settings

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_content",
            "description": "根据大纲创作新的小说正文段落",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "创作指令，描述本节大纲和创作要求",
                    },
                },
                "required": ["instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rewrite_content",
            "description": "根据审查意见改写正文，修正结构/情节问题。用于 review 发现问题后的修正步骤。text 参数如省略则自动使用上一轮 write/rewrite 的输出",
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {"type": "string", "description": "改写方向和要求（必须提供，通常来自 review 的 issues）"},
                    "text": {"type": "string", "description": "需要改写的文本（可选，省略时自动取最新创作的正文）"},
                },
                "required": ["instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_content",
            "description": "审查文本质量：角色一致性、情节衔接、大纲遵循。text 参数如省略则自动使用上一轮 write/rewrite 的输出",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "需要审查的文本（可选，省略时自动取最新创作的正文）"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "polish_content",
            "description": "润色全文语言：修正语病、增强文笔和画面感。在结构问题解决后使用。text 参数如省略则自动使用上一轮 write/rewrite 的输出。SOP 要求此工具在 finish 前自动执行，Agent 无需询问用户",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "需要润色的文本（可选，省略时自动取最新正文）"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "任务完成，返回最终结果给用户",
            "parameters": {
                "type": "object",
                "properties": {
                    "result": {"type": "string", "description": "创作的小说正文或最终输出"},
                    "summary": {"type": "string", "description": "完成的工作摘要"},
                },
                "required": ["result"],
            },
        },
    },
]

LIGHT_TOOLS: set[str] = set()


async def _execute_tool(
    db: AsyncSession,
    tool_name: str,
    tool_args: dict[str, Any],
    novel_id: int,
    provider: str,
    model: str,
    api_key: str,
    session: dict[str, Any] | None = None,
) -> str:
    """Execute a single tool call and return the result as a string.
    session carries mutable state across tool calls, e.g. session["last_text"]."""
    last_text = session.get("last_text", "") if session else ""

    if tool_name == "write_content":
        ctx = await build_context(db, novel_id)
        action = "write"
        instruction = tool_args.get("instruction", "")
        system_prompt = _load_action_prompt(action)
        if not system_prompt:
            system_prompt = _load_action_prompt("polish")
        system_prompt = system_prompt.replace("{selected_text}", "")
        if ctx:
            system_prompt += f"\n\n相关上下文和设定：\n{ctx}"
        user_prompt = f"## 本节大纲\n{instruction}\n\n请根据以上大纲和上下文，开始创作本节内容。"

        full = ""
        try:
            async for token in stream_ai_response(
                action, system_prompt, user_prompt, provider, model, api_key,
            ):
                if isinstance(token, str):
                    full += token
        except Exception as e:
            full = f"[生成失败: {e}]"
        result = full or "[生成内容为空]"
        if session is not None:
            session["last_text"] = result
        return result

    elif tool_name == "rewrite_content":
        ctx = await build_context(db, novel_id)
        text = tool_args.get("text", "") or last_text
        instruction = tool_args.get("instruction", "")
        action = "rewrite"
        system_prompt = _load_action_prompt(action) or _load_action_prompt("polish")
        system_prompt = system_prompt.replace("{selected_text}", text)
        if ctx:
            system_prompt += f"\n\n相关上下文和设定：\n{ctx}"
        user_prompt = f"修改方向：{instruction}"

        if not text:
            return "[改写失败: 没有可改写的文本，请先调用 write_content 创作正文]"

        full = ""
        try:
            async for token in stream_ai_response(
                action, system_prompt, user_prompt, provider, model, api_key,
            ):
                if isinstance(token, str):
                    full += token
        except Exception as e:
            full = f"[改写失败: {e}]"
        result = full or "[改写结果为空]"
        if result and not result.startswith("[") and session is not None:
            session["last_text"] = result
        return result

    elif tool_name == "review_content":
        ctx = await build_context(db, novel_id)
        text = tool_args.get("text", "") or last_text
        action = "review"
        system_prompt = _load_action_prompt(action) or _load_action_prompt("polish")
        system_prompt = system_prompt.replace("{selected_text}", "")
        if ctx:
            system_prompt += f"\n\n相关上下文和设定：\n{ctx}"

        if not text:
            return json.dumps({"ok": False, "issues": [{"type": "quality", "title": "无文本可审查", "detail": "请先调用 write_content 创作正文后再审查", "suggestion": "先写后审"}]}, ensure_ascii=False)

        user_prompt = f"请审查以下正文：\n\n{text}"

        full = ""
        try:
            async for token in stream_ai_response(
                action, system_prompt, user_prompt, provider, model, api_key,
            ):
                if isinstance(token, str):
                    full += token
        except Exception as e:
            full = f"[审查失败: {e}]"
        return full or "[审查结果为空]"

    elif tool_name == "polish_content":
        ctx = await build_context(db, novel_id)
        text = tool_args.get("text", "") or last_text
        action = "polish"
        system_prompt = _load_action_prompt(action) or _load_action_prompt("polish")
        system_prompt = system_prompt.replace("{selected_text}", text)
        if ctx:
            system_prompt += f"\n\n相关上下文和设定：\n{ctx}"
        user_prompt = "请润色以上全文，修正语病、增强文笔，不改变情节。"

        if not text:
            return "[润色失败: 没有可润色的文本，请先调用 write_content 创作正文]"

        full = ""
        try:
            async for token in stream_ai_response(
                action, system_prompt, user_prompt, provider, model, api_key,
            ):
                if isinstance(token, str):
                    full += token
        except Exception as e:
            full = f"[润色失败: {e}]"
        result = full or "[润色结果为空]"
        if result and not result.startswith("[") and session is not None:
            session["last_text"] = result
        return result

    elif tool_name == "finish":
        return json.dumps(tool_args, ensure_ascii=False)

    return f"[未知工具: {tool_name}]"


async def agent_completion(
    db: AsyncSession,
    user_message: str,
    novel_id: int,
    provider: str,
    model: str,
    api_key: str,
    max_turns: int = 6,
) -> AsyncIterator[str]:
    """Run the ReAct agent loop, yielding SSE events for each step."""
    from litellm import acompletion
    from sqlalchemy import select

    system_prompt = _load_action_prompt("agent")
    if not system_prompt:
        system_prompt = "你是一个创作助手Agent。"

    outline_nodes = (await db.execute(
        select(OutlineNode).where(OutlineNode.novel_id == novel_id)
    )).scalars().all()
    if outline_nodes:
        node_map: dict[int | None, list[OutlineNode]] = {}
        for n in outline_nodes:
            pid = n.parent_id
            node_map.setdefault(pid, []).append(n)

        def format_outline(pid: int | None, depth: int = 0) -> list[str]:
            lines = []
            children = node_map.get(pid, [])
            children.sort(key=lambda x: x.sort_order or 0)
            for child in children:
                indent = "  " * depth
                label = {"volume": "卷", "chapter": "章", "scene": "节"}.get(child.node_type, child.node_type)
                line = f"{indent}[{label}] {child.title}"
                if child.summary:
                    line += f"：{child.summary[:60]}"
                lines.append(line)
                lines.extend(format_outline(child.id, depth + 1))
            return lines

        outline_text = "\n".join(format_outline(None))
        system_prompt += f"\n\n## 当前小说大纲\n{outline_text}"

    model_name, credential, is_base_url = resolve_model(provider, model, api_key)
    if not credential:
        yield json.dumps({"type": "error", "content": "请先配置 API Key"}) + "\n"
        return

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    turn = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    session: dict[str, Any] = {"last_text": ""}

    while turn < max_turns:
        yield json.dumps({"type": "thinking", "content": f"思考中...（第{turn+1}/{max_turns}步）"}) + "\n"

        kwargs = {
            "model": model_name,
            "messages": messages,
            "max_tokens": settings.max_output_tokens,
            "tools": TOOLS,
        }
        if is_base_url:
            kwargs["api_base"] = credential
        else:
            kwargs["api_key"] = credential

        try:
            response = await acompletion(**kwargs)
        except Exception as e:
            yield json.dumps({"type": "error", "content": f"Agent调用失败: {e}"}) + "\n"
            return

        usage = getattr(response, "usage", None)
        if usage:
            total_prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            total_completion_tokens += getattr(usage, "completion_tokens", 0) or 0

        choice = response.choices[0]
        msg = choice.message

        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                yield json.dumps({"type": "tool_call", "tool": tool_name, "args": tool_args}) + "\n"

                if tool_name == "finish":
                    result = tool_args.get("result", "")
                    yield json.dumps({"type": "final", "content": result}) + "\n"
                    if tool_args.get("summary"):
                        yield json.dumps({"type": "summary", "content": tool_args["summary"]}) + "\n"
                    yield json.dumps({
                        "type": "usage",
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_prompt_tokens + total_completion_tokens,
                        "model": model_name,
                    }) + "\n"
                    return

                result = await _execute_tool(
                    db, tool_name, tool_args, novel_id, provider, model, api_key, session,
                )
                yield json.dumps({"type": "tool_result", "tool": tool_name, "content": result[:500]}) + "\n"

                messages.append({"role": "assistant", "content": None, "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tool_name, "arguments": json.dumps(tool_args, ensure_ascii=False)}}
                ]})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

                if tool_name not in LIGHT_TOOLS:
                    turn += 1
        else:
            content = msg.content or ""
            if content:
                yield json.dumps({"type": "output", "content": content}) + "\n"
            yield json.dumps({"type": "final", "content": content}) + "\n"
            yield json.dumps({
                "type": "usage",
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "model": model_name,
            }) + "\n"
            return

    yield json.dumps({"type": "error", "content": f"Agent达到最大步数上限（{max_turns}），请简化指令重试"}) + "\n"
