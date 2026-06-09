import datetime
from pydantic import BaseModel, Field
from typing import Optional


class NovelCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    genre: str = ""
    style_notes: str = ""
    word_count_goal: int = 0


class NovelUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    style_notes: Optional[str] = None
    word_count_goal: Optional[int] = None


class NovelOut(BaseModel):
    id: int
    title: str
    description: str
    genre: str
    style_notes: str
    word_count_goal: int
    chapter_count: int = 0
    total_word_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class NovelListItem(BaseModel):
    id: int
    title: str
    description: str
    genre: str
    chapter_count: int = 0
    total_word_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
