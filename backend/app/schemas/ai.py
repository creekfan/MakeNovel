from typing import Optional

from pydantic import BaseModel


class AIRequest(BaseModel):
    novel_id: int
    chapter_id: Optional[int] = None
    action: str
    selected_text: str = ""
    instruction: str = ""
    provider: str = ""
    model: str = ""
    api_key: str = ""
    active_character_ids: Optional[list[int]] = None
    active_setting_ids: Optional[list[int]] = None


class AIActionInfo(BaseModel):
    action: str
    label: str
    description: str
    requires_text: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    provider: str = ""
    model: str = ""
    api_key: str = ""
