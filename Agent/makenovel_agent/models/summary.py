from __future__ import annotations

from pydantic import BaseModel, Field


class SectionSummary(BaseModel):
    """已完成章节的摘要"""

    section_id: str = Field(description="对应 section 的 ID")
    section_title: str = Field(default="", description="本节标题")
    summary: str = Field(default="", description="本节情节摘要")
    key_events: list[str] = Field(
        default_factory=list, description="关键事件列表"
    )
    character_state_changes: dict[str, str] = Field(
        default_factory=dict,
        description="角色状态变化，key=角色ID, value=状态变化描述",
    )
    world_setting_changes: dict[str, str] = Field(
        default_factory=dict,
        description="世界观设定变化，key=设定ID, value=变化描述",
    )

    def format_context(self) -> str:
        """格式化为上下文文本（用于注入LLM上下文）"""
        lines = [f"## {self.section_title}"]
        if self.summary:
            lines.append(f"概要：{self.summary}")
        if self.key_events:
            lines.append("关键事件：")
            for event in self.key_events:
                lines.append(f"  - {event}")
        if self.character_state_changes:
            lines.append("角色状态变化：")
            for cid, change in self.character_state_changes.items():
                lines.append(f"  - [{cid}] {change}")
        if self.world_setting_changes:
            lines.append("世界观变化：")
            for wid, change in self.world_setting_changes.items():
                lines.append(f"  - [{wid}] {change}")
        return "\n".join(lines)
