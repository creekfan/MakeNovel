import json
from pathlib import Path
from typing import AsyncIterator, Any

import litellm
from litellm import completion, acompletion

from app.core.config import settings


AI_ACTIONS = [
    {"action": "write",      "label": "创作",       "description": "根据大纲和上下文创作新内容",              "requires_text": False},
    {"action": "polish",     "label": "润色",       "description": "进化你的初稿，默认作用于本节全文",                  "requires_text": False},
    {"action": "rewrite",    "label": "改写",       "description": "按指定方向修改选段或全文",                  "requires_text": False},
    {"action": "brainstorm", "label": "头脑风暴",   "description": "结合创作想法提供情节发展建议",        "requires_text": False},
    {"action": "summary",    "label": "摘要",       "description": "对本节内容生成摘要供下文参考",            "requires_text": False},
    {"action": "review",     "label": "审查",       "description": "检查创作质量和一致性",            "requires_text": False},
]


def resolve_model(provider: str, model: str, api_key: str) -> tuple[str, str, bool]:
    """Return (litellm_model_name, credential, is_base_url) from user-provided config."""
    p = provider or "openai"
    if p == "ollama":
        return f"ollama/{model or settings.ollama_model}", api_key or settings.ollama_base_url, True
    elif p == "deepseek":
        return f"deepseek/{model or settings.deepseek_model}", api_key, False
    elif p == "gemini":
        return f"gemini/{model or settings.gemini_model}", api_key, False
    elif p == "anthropic":
        return model or settings.anthropic_model, api_key, False
    else:
        return model or settings.openai_model, api_key, False


_SKILL_DIR = Path(__file__).parent.parent / "skills"
_prompt_cache: dict[str, str] = {}


def _load_action_prompt(action: str) -> str:
    if action not in _prompt_cache:
        path_val = _SKILL_DIR / f"{action}.md"
        _prompt_cache[action] = path_val.read_text(encoding="utf-8").strip() if path_val.exists() else ""
    return _prompt_cache[action]


def build_system_prompt(action: str, context: str, style_notes: str, selected_text: str = "") -> str:
    action_prompt = _load_action_prompt(action)
    if not action_prompt:
        action_prompt = _load_action_prompt("polish")
    action_prompt = action_prompt.replace("{selected_text}", selected_text)
    parts = [action_prompt]
    if context:
        parts.append(f"\n\n相关上下文和设定：\n{context}")
    if style_notes:
        parts.append(f"\n\n作者的写作风格要求：\n{style_notes}")
    return "\n".join(parts)


def build_user_prompt(action: str, selected_text: str, instruction: str) -> str:
    if action == "recommend":
        return instruction
    if action == "write":
        base = f"## 本节大纲\n{instruction}"
        if selected_text:
            base += f"\n\n## 前文\n{selected_text[-2000:]}"
        base += "\n\n请根据以上大纲和前文，开始创作本节内容。"
    elif action == "summary":
        base = f"请对以下小说正文进行摘要：\n\n{selected_text}"
        if instruction:
            base += f"\n\n特别要求：{instruction}"
    elif action == "rewrite":
        base = f"修改方向：{instruction}"
    elif action == "review":
        base = f"请审查以下正文：\n\n{selected_text}"
        if instruction:
            base += f"\n\n审查重点：{instruction}"
    elif action == "brainstorm":
        base = "请基于以下大纲信息生成具体事件建议。"
        if selected_text:
            base += f"\n\n大纲上下文：\n{selected_text[-3000:]}"
        if instruction:
            base += f"\n\n作者的补充想法：{instruction}"
    else:
        base = ""
        if instruction:
            base += f"特别要求：{instruction}"
    return base


TOKEN_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4": (0.03, 0.06),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "claude-3-5-sonnet-20240620": (0.003, 0.015),
    "claude-3-opus": (0.015, 0.075),
    "claude-3-haiku": (0.00025, 0.00125),
    "deepseek-chat": (0.00014, 0.00028),
    "deepseek-reasoner": (0.00055, 0.00219),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    clean = model.replace("openai/", "").replace("anthropic/", "").replace("deepseek/", "").replace("ollama/", "")
    costs = TOKEN_COSTS.get(clean)
    if not costs:
        for k, v in TOKEN_COSTS.items():
            if k in clean:
                costs = v
                break
    if not costs:
        return 0.0
    return (prompt_tokens / 1000) * costs[0] + (completion_tokens / 1000) * costs[1]


async def stream_ai_response(
    action: str,
    system_prompt: str,
    user_prompt: str,
    provider: str = "",
    model: str = "",
    api_key: str = "",
) -> AsyncIterator[str | dict]:
    model_name, credential, is_base_url = resolve_model(provider, model, api_key)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    kwargs: dict = {
        "model": model_name,
        "messages": messages,
        "max_tokens": settings.max_output_tokens,
        "stream": True,
    }

    if is_base_url:
        kwargs["api_base"] = credential
    else:
        kwargs["api_key"] = credential

    if not credential:
        yield "\n\n[请先在设置页面配置 API Key]"
        return

    try:
        response = await acompletion(**kwargs)
        usage_info = None
        async for chunk in response:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", "") or ""
            reasoning = getattr(delta, "reasoning_content", "") or ""
            usage = getattr(chunk, "usage", None)
            if usage:
                prompt_tokens = getattr(usage, "prompt_tokens", 0)
                completion_tokens = getattr(usage, "completion_tokens", 0)
                total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens)
                cost = estimate_cost(model_name, prompt_tokens, completion_tokens)
                usage_info = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost": round(cost, 6),
                    "model": model_name,
                }
            if reasoning:
                yield {"type": "reasoning", "content": reasoning}
            if content:
                yield content
        if usage_info:
            yield {"type": "usage", "data": usage_info}
    except Exception as e:
        yield f"\n\n[AI 调用出错: {str(e)}]"
