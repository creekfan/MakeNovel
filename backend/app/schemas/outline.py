import datetime
from pydantic import BaseModel, Field
from typing import Optional, Union


class OutlineNodeCreate(BaseModel):
    novel_id: int
    parent_id: Optional[int] = None
    node_type: str = "scene"
    title: str = Field(..., min_length=1, max_length=500)
    summary: str = ""
    notes: str = ""
    sort_order: Union[int, float] = 0


class OutlineNodeUpdate(BaseModel):
    parent_id: Optional[int] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    notes: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[Union[int, float]] = None
    assigned_chapter_id: Optional[int] = None


class OutlineNodeOut(BaseModel):
    id: int
    novel_id: int
    parent_id: Optional[int] = None
    node_type: str
    title: str
    summary: str
    notes: str
    status: str
    sort_order: float
    assigned_chapter_id: Optional[int] = None
    content: str = ""
    children: list["OutlineNodeOut"] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
