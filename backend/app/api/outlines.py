from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import OutlineNode, Novel
from app.schemas.outline import OutlineNodeCreate, OutlineNodeUpdate, OutlineNodeOut

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
        assigned_chapter_id=node.assigned_chapter_id,
        content=node.content or "",
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
