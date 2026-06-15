from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

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


@router.put("")
def update_outline(novel_id: str, body: OutlineUpdate):
    storage.save_outline(novel_id, body.model_dump())
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
