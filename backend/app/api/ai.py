import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.ai import AIRequest, AIActionInfo, ChatRequest
from app.services.llm import (
    AI_ACTIONS, stream_ai_response, resolve_model, build_system_prompt, build_user_prompt
)
from app.services.context import build_context

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/actions", response_model=list[AIActionInfo])
async def list_actions():
    return [AIActionInfo(**a) for a in AI_ACTIONS]


@router.post("/generate")
async def generate(request: AIRequest, db: AsyncSession = Depends(get_db)):
    context = await build_context(
        db, request.novel_id, request.chapter_id,
        request.active_character_ids, request.active_setting_ids,
    )

    novel_sql = "SELECT style_notes FROM novels WHERE id = :nid"
    from sqlalchemy import text
    style_result = await db.execute(text(novel_sql), {"nid": request.novel_id})
    row = style_result.fetchone()
    style_notes = row[0] if row else ""

    system_prompt = build_system_prompt(request.action, context, style_notes, request.selected_text)

    text = request.selected_text

    user_prompt = build_user_prompt(request.action, text, request.instruction)

    async def event_stream():
        async for token in stream_ai_response(
            request.action, system_prompt, user_prompt,
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
        ):
            yield f"data: {json.dumps({'token': token})}\n\n"
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
            async for chunk in response:
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", "") or ""
                if content:
                    yield f"data: {json.dumps({'token': content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'token': f'[出错: {str(e)}]'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
