from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/characters", tags=["characters"])


class CharacterRelationshipIn(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    description: str = ""


class CharacterIn(BaseModel):
    id: str
    name: str
    role: str = "supporting"
    appearance: str = ""
    personality: str = ""
    background: str = ""
    abilities: Optional[str] = None
    speech_style: Optional[str] = None
    arc: Optional[str] = None
    current_state: Optional[str] = None
    relationships: list[CharacterRelationshipIn] = []


@router.get("")
def get_characters(novel_id: str):
    return storage.get_characters(novel_id)


@router.put("")
def save_characters(novel_id: str, body: list[CharacterIn]):
    storage.save_characters(novel_id, [c.model_dump() for c in body])
    return {"ok": True}


@router.post("")
def add_character(novel_id: str, body: CharacterIn):
    chars = storage.get_characters(novel_id)
    chars.append(body.model_dump())
    storage.save_characters(novel_id, chars)
    return {"ok": True}


@router.delete("/{character_id}")
def delete_character(novel_id: str, character_id: str):
    chars = storage.get_characters(novel_id)
    chars = [c for c in chars if c.get("id") != character_id]
    storage.save_characters(novel_id, chars)
    return {"ok": True}
