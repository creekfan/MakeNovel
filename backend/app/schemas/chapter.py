import datetime
from pydantic import BaseModel, Field
from typing import Optional


class ChapterCreate(BaseModel):
    novel_id: int
    title: str = Field(..., min_length=1, max_length=500)
    chapter_number: int


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    character_snapshot: Optional[dict] = None
    plot_points: Optional[list] = None
    word_count: Optional[int] = None
    chapter_prompt: Optional[str] = None


class ChapterOut(BaseModel):
    id: int
    novel_id: int
    title: str
    chapter_number: int
    status: str
    content: str
    summary: str
    character_snapshot: dict
    plot_points: list
    word_count: int
    chapter_prompt: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ChapterListItem(BaseModel):
    id: int
    novel_id: int
    title: str
    chapter_number: int
    status: str
    summary: str
    word_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
