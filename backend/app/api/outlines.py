from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import OutlineNode, Novel
from app.schemas.outline import OutlineNodeCreate, OutlineNodeUpdate, OutlineNodeOut
from app.services.rag import embed_section


class EmbedRequest(BaseModel):
    provider: str = ""
    model: str = ""
    api_key: str = ""


class SummarizeRequest(BaseModel):
    provider: str = ""
    model: str = ""
    api_key: str = ""


router = APIRouter(prefix="/api/outlines", tags=["outlines"])


def _node_to_out(node: OutlineNode) -> OutlineNodeOut:
    return OutlineNodeOut(
        id=node.id,
        novel_id=node.novel_id,
        parent_id=node.parent_id,
        node_type=node.node_type,
        title=node.title,
        summary=node.summary or "",
        notes=node.notes or "",
        status=node.status or "planned",
        sort_order=node.sort_order or 0,
        content=node.content or "",
        chapter_prompt=node.chapter_prompt or "",
        children=[],
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _build_tree(nodes: list[OutlineNode], parent_id: int | None = None) -> list[OutlineNodeOut]:
    result = []
    children = [n for n in nodes if n.parent_id == parent_id]
    children.sort(key=lambda n: n.sort_order or 0)
    for child in children:
        node_out = _node_to_out(child)
        node_out.children = _build_tree(nodes, child.id)
        result.append(node_out)
    return result


@router.get("/novel/{novel_id}", response_model=list[OutlineNodeOut])
async def list_outline(novel_id: int, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    nodes = (await db.execute(
        select(OutlineNode).where(OutlineNode.novel_id == novel_id)
    )).scalars().all()
    return _build_tree(list(nodes))


@router.post("", response_model=OutlineNodeOut)
async def create_outline_node(data: OutlineNodeCreate, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, data.novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    node = OutlineNode(**data.model_dump(exclude={"parent_id"}), parent_id=data.parent_id)
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return _node_to_out(node)


@router.put("/{node_id}", response_model=OutlineNodeOut)
async def update_outline_node(node_id: int, data: OutlineNodeUpdate, db: AsyncSession = Depends(get_db)):
    node = await db.get(OutlineNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="大纲节点不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(node, key, val)
    await db.commit()
    await db.refresh(node)
    return _node_to_out(node)


@router.delete("/{node_id}")
async def delete_outline_node(node_id: int, db: AsyncSession = Depends(get_db)):
    node = await db.get(OutlineNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="大纲节点不存在")
    await db.delete(node)
    await db.commit()
    return {"ok": True}


@router.post("/{node_id}/embed")
async def embed_outline_node(
    node_id: int,
    data: EmbedRequest,
    db: AsyncSession = Depends(get_db),
):
    ok = await embed_section(db, node_id, data.provider, data.model, data.api_key)
    return {"ok": ok}


@router.post("/{node_id}/summarize")
async def summarize_outline_node(
    node_id: int,
    data: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
):
    node = await db.get(OutlineNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="大纲节点不存在")
    if not node.content or len(node.content) < 50:
        return {"ok": False, "detail": "内容不足，无法生成摘要"}

    from app.services.llm import stream_ai_response, resolve_model, _load_action_prompt

    system_prompt = _load_action_prompt("summary")
    if not system_prompt:
        system_prompt = "请对以下小说正文生成一段简洁的摘要（200字以内），概括核心情节要点。"

    text_plain = node.content.replace("<p>", "").replace("</p>", "\n")
    user_prompt = f"请对以下小说正文生成摘要：\n\n{text_plain[:4000]}"

    full = ""
    try:
        async for token in stream_ai_response(
            "summary", system_prompt, user_prompt,
            provider=data.provider, model=data.model, api_key=data.api_key,
        ):
            full += token
    except Exception as e:
        return {"ok": False, "detail": str(e)}

    if full:
        node.summary = full.strip()
        await db.commit()
        return {"ok": True, "summary": node.summary}
    return {"ok": False, "detail": "生成内容为空"}
