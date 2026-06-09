import datetime
from pydantic import BaseModel, Field
from typing import Optional


class CharacterCreate(BaseModel):
    novel_id: int
    name: str = Field(..., min_length=1, max_length=200)
    aliases: list[str] = []
    role: str = "supporting"
    profile: dict = {}
    arc: str = ""
    avatar_color: str = "#6366f1"


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[list[str]] = None
    role: Optional[str] = None
    profile: Optional[dict] = None
    arc: Optional[str] = None
    avatar_color: Optional[str] = None


class RelationshipCreate(BaseModel):
    source_id: int
    target_id: int
    relation_type: str = ""
    description: str = ""


class RelationshipOut(BaseModel):
    id: int
    source_id: int
    target_id: int
    target_name: str = ""
    relation_type: str
    description: str

    model_config = {"from_attributes": True}


class CharacterOut(BaseModel):
    id: int
    novel_id: int
    name: str
    aliases: list
    role: str
    profile: dict
    arc: str
    avatar_color: str
    relationships: list["RelationshipOut"] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
