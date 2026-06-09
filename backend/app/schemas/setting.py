import datetime
from pydantic import BaseModel, Field
from typing import Optional


class SettingCreate(BaseModel):
    novel_id: int
    name: str = Field(..., min_length=1, max_length=300)
    category: str = "location"
    location_type: str = ""
    description: str = ""
    notable_features: list[str] = []


class SettingUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    location_type: Optional[str] = None
    description: Optional[str] = None
    notable_features: Optional[list[str]] = None


class SettingOut(BaseModel):
    id: int
    novel_id: int
    name: str
    category: str
    location_type: str
    description: str
    notable_features: list
    chapters_featured: list
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
