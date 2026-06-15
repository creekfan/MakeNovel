from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CharacterRelationship(BaseModel):
    """角色关系"""

    source_id: str = Field(description="源角色ID")
    target_id: str = Field(description="目标角色ID")
    relation_type: str = Field(description="关系类型，如：朋友、师徒、敌人")
    description: str = Field(default="", description="关系描述")


class CharacterCard(BaseModel):
    """角色卡片"""

    id: str = Field(description="角色唯一标识")
    name: str = Field(description="角色名称")
    role: Literal["protagonist", "antagonist", "supporting", "minor"] = Field(
        description="角色定位：主角/反派/配角/次要角色"
    )
    appearance: str = Field(default="", description="外貌描述")
    personality: str = Field(default="", description="性格特征")
    background: str = Field(default="", description="角色背景")
    abilities: Optional[str] = Field(default=None, description="能力/特长/技能")
    speech_style: Optional[str] = Field(default=None, description="说话风格/口癖")
    arc: Optional[str] = Field(default=None, description="角色弧光/成长轨迹")
    current_state: Optional[str] = Field(default=None, description="当前剧情状态")
    relationships: list[CharacterRelationship] = Field(
        default_factory=list, description="与他人的关系列表"
    )

    def get_related_character_ids(self) -> set[str]:
        """获取所有关联角色ID"""
        ids: set[str] = set()
        for rel in self.relationships:
            ids.add(rel.source_id)
            ids.add(rel.target_id)
        ids.discard(self.id)
        return ids

    def get_relationship_with(self, other_id: str) -> Optional[CharacterRelationship]:
        """获取与另一角色的关系"""
        for rel in self.relationships:
            if (rel.source_id == self.id and rel.target_id == other_id) or \
               (rel.source_id == other_id and rel.target_id == self.id):
                return rel
        return None

    def format_card(self) -> str:
        """格式化为可读文本（用于注入LLM上下文）"""
        lines = [
            f"【{self.name}】（{self.role}）",
            f"  外貌：{self.appearance}" if self.appearance else "",
            f"  性格：{self.personality}" if self.personality else "",
            f"  背景：{self.background}" if self.background else "",
            f"  能力：{self.abilities}" if self.abilities else "",
            f"  说话风格：{self.speech_style}" if self.speech_style else "",
            f"  当前状态：{self.current_state}" if self.current_state else "",
        ]
        return "\n".join(filter(None, lines))
