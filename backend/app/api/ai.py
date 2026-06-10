import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.ai import AIRequest, AIActionInfo, ChatRequest, AgentRequest
from app.services.llm import (
    AI_ACTIONS, stream_ai_response, resolve_model, build_system_prompt, build_user_prompt
)
from app.services.context import build_context
from app.services.rag import search_by_query
from app.services.agent import agent_completion

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/actions", response_model=list[AIActionInfo])
async def list_actions():
    return [AIActionInfo(**a) for a in AI_ACTIONS]


@router.post("/generate")
async def generate(request: AIRequest, db: AsyncSession = Depends(get_db)):
    context = await build_context(
        db, request.novel_id,
        request.active_character_ids, request.active_setting_ids,
        current_scene_id=request.scene_id,
    )

    if request.action in ("write", "polish", "rewrite", "brainstorm", "summary") and request.api_key:
        try:
            query_text = request.instruction or request.selected_text or ""
            if len(query_text) > 100:
                rag_results = await search_by_query(
                    db, request.novel_id, query_text,
                    request.provider, request.model, request.api_key,
                    top_k=3,
                )
                if rag_results:
                    rag_parts = ["\n## 相关前文（RAG检索）"]
                    for sec in rag_results[:3]:
                        text_plain = (sec.content or "").replace("<p>", "").replace("</p>", "\n")
                        text_plain = text_plain[:300]
                        rag_parts.append(f"\n### {sec.title}")
                        if sec.summary:
                            rag_parts.append(f"  概要：{sec.summary[:80]}")
                        if text_plain:
                            rag_parts.append(f"  正文节选：{text_plain}")
                    context += "\n" + "\n".join(rag_parts)
        except Exception:
            pass

    from sqlalchemy import select
    from app.models.models import Novel
    novel = await db.get(Novel, request.novel_id)
    style_notes = novel.style_notes if novel else ""

    system_prompt = build_system_prompt(request.action, context, style_notes, request.selected_text)
    text = request.selected_text
    user_prompt = build_user_prompt(request.action, text, request.instruction)

    if request.action == "recommend":
        async def event_stream():
            model_name, credential, is_base_url = resolve_model(
                request.provider, request.model, request.api_key
            )
            if not credential:
                yield f"data: {json.dumps({'token': '[请先配置 Gemini API Key]'})}\n\n"
                yield "data: [DONE]\n\n"
                return
            try:
                from litellm import acompletion
                kwargs = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 300,
                }
                if is_base_url:
                    kwargs["api_base"] = credential
                else:
                    kwargs["api_key"] = credential
                resp = await acompletion(**kwargs)
                content = resp.choices[0].message.content or ""
                yield f"data: {json.dumps({'token': content})}\n\n"
                usage = getattr(resp, "usage", None)
                if usage:
                    yield f"data: {json.dumps({'usage': {'prompt_tokens': getattr(usage,'prompt_tokens',0), 'completion_tokens': getattr(usage,'completion_tokens',0), 'total_tokens': getattr(usage,'total_tokens',0)}})}\n\n"
            except Exception as e:
                error_msg = str(e)
                if '429' in error_msg or 'quota' in error_msg.lower():
                    yield f"data: {json.dumps({'error': 'Gemini 免费额度用尽（20次/天），请稍后重试或换 Key'})}\n\n"
                else:
                    yield f"data: {json.dumps({'error': f'AI 调用出错: {error_msg[:200]}'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    async def event_stream():
        usage_info = None
        async for item in stream_ai_response(
            request.action, system_prompt, user_prompt,
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
        ):
            if isinstance(item, dict):
                if item.get("type") == "reasoning":
                    yield f"data: {json.dumps({'reasoning': item['content']})}\n\n"
                elif item.get("type") == "usage":
                    usage_info = item.get("data", item)
                # 其他 dict 类型忽略，不阻塞流
            else:
                yield f"data: {json.dumps({'token': item})}\n\n"
        if usage_info:
            yield f"data: {json.dumps({'usage': usage_info})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat")
async def chat(request: ChatRequest):
    model_name, credential, is_base_url = resolve_model(
        request.provider or "", request.model or "", request.api_key or ""
    )

    if not credential:
        async def error_stream():
            yield f"data: {json.dumps({'token': '[请先在设置页面配置 API Key]'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    system_msg = {
        "role": "system",
        "content": "你是 MakeNovel 的 AI 写作伙伴。你可以帮助用户回答写作相关问题、提供创意建议、讨论情节、分析角色等。请用中文回答，保持热情、专业。",
    }

    messages = [system_msg] + [m.model_dump() for m in request.messages]

    kwargs: dict = {
        "model": model_name,
        "messages": messages,
        "max_tokens": 2000,
        "stream": True,
    }

    if is_base_url:
        kwargs["api_base"] = credential
    else:
        kwargs["api_key"] = credential

    async def event_stream():
        from litellm import acompletion
        try:
            response = await acompletion(**kwargs)
            usage_info = None
            async for chunk in response:
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", "") or ""
                reasoning = getattr(delta, "reasoning_content", "") or ""
                usage = getattr(chunk, "usage", None)
                if usage:
                    usage_info = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
                if reasoning:
                    yield f"data: {json.dumps({'reasoning': reasoning})}\n\n"
                if content:
                    yield f"data: {json.dumps({'token': content})}\n\n"
            if usage_info:
                yield f"data: {json.dumps({'usage': usage_info})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'token': f'[出错: {str(e)}]'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/agent")
async def agent(request: AgentRequest, db: AsyncSession = Depends(get_db)):
    async def event_stream():
        async for event in agent_completion(
            db=db,
            user_message=request.message,
            novel_id=request.novel_id,
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
        ):
            yield f"data: {event}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
