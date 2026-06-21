import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/styles", tags=["styles"])


class StyleCreate(BaseModel):
    name: str
    content: str


class StyleUpdate(BaseModel):
    name: str
    content: str


@router.get("")
def list_styles_route(novel_id: str):
    return storage.list_styles(novel_id)


@router.get("/{style_id}")
def get_style_route(novel_id: str, style_id: str):
    s = storage.get_style(novel_id, style_id)
    if not s:
        raise HTTPException(404, "文风不存在")
    return s


@router.post("")
def create_style(novel_id: str, body: StyleCreate):
    if not body.name.strip():
        raise HTTPException(400, "名称不能为空")
    style_id = "sty_" + uuid.uuid4().hex[:8]
    storage.save_style(novel_id, style_id, body.name.strip(), body.content)
    return storage.get_style(novel_id, style_id)


@router.put("/{style_id}")
def update_style(novel_id: str, style_id: str, body: StyleUpdate):
    existing = storage.get_style(novel_id, style_id)
    if not existing:
        raise HTTPException(404, "文风不存在")
    if not body.name.strip():
        raise HTTPException(400, "名称不能为空")
    storage.save_style(novel_id, style_id, body.name.strip(), body.content)
    return storage.get_style(novel_id, style_id)


@router.delete("/{style_id}")
def delete_style_route(novel_id: str, style_id: str):
    existing = storage.get_style(novel_id, style_id)
    if not existing:
        raise HTTPException(404, "文风不存在")
    storage.delete_style(novel_id, style_id)
    return {"ok": True}
