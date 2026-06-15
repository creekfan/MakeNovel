import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import storage

router = APIRouter(prefix="/api/novels", tags=["novels"])


class NovelCreate(BaseModel):
    name: str


class NovelOut(BaseModel):
    id: str
    name: str


@router.get("", response_model=list[NovelOut])
def list_novels():
    return storage.list_novels()


@router.post("", response_model=NovelOut, status_code=201)
def create_novel(body: NovelCreate):
    novel_id = str(uuid.uuid4())[:8]
    meta = {"id": novel_id, "name": body.name}
    storage.save_novel(novel_id, meta)
    outline = {
        "novel_id": novel_id,
        "novel_title": body.name,
        "volumes": [],
    }
    storage.save_outline(novel_id, outline)
    storage.save_characters(novel_id, [])
    storage.save_world_settings(novel_id, [])
    storage.save_summaries(novel_id, [])
    return meta


@router.get("/{novel_id}", response_model=NovelOut)
def get_novel(novel_id: str):
    meta = storage.get_novel(novel_id)
    if not meta:
        raise HTTPException(404, "Novel not found")
    return meta


@router.delete("/{novel_id}", status_code=204)
def delete_novel(novel_id: str):
    storage.delete_novel(novel_id)
