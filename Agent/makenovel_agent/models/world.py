from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, Field


class WorldSetting(BaseModel):
    """世界观/设定卡片"""

    id: str = Field(description="设定唯一标识")
    name: str = Field(description="设定名称")
    category: Literal["location", "faction", "rule", "race", "item", "profession", "history"] = Field(
        description="设定类别：地点/势力/规则/种族/物品/职业/历史"
    )
    description: str = Field(default="", description="详细描述")
    notable_features: list[str] = Field(
        default_factory=list, description="显著特征列表"
    )

    CATEGORY_LABELS: ClassVar[dict[str, str]] = {
        "location": "环境场景",
        "faction": "势力组织",
        "rule": "世界观规则",
        "race": "种族物种",
        "item": "重要物品",
        "profession": "职业",
        "history": "历史事件",
    }

    def format_card(self) -> str:
        """格式化为可读文本（用于注入LLM上下文）"""
        category_label = self.CATEGORY_LABELS.get(self.category, self.category)
        lines = [
            f"【{self.name}】（{category_label}）",
            f"  描述：{self.description}" if self.description else "",
        ]
        if self.notable_features:
            lines.append(f"  特征：{' / '.join(self.notable_features)}")
        return "\n".join(filter(None, lines))
