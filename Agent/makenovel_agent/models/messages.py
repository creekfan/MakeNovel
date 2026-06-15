"""Agent 间的消息类型 —— 所有结构化输入/输出"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .character import CharacterCard
from .summary import SectionSummary
from .world import WorldSetting


# ═══════════════════════════════════════════════════════════
# 准备者 → 创作者
# ═══════════════════════════════════════════════════════════

class PreparationResult(BaseModel):
    """准备者的输出：创作者和后续Agent的输入"""

    current_section_id: str = Field(description="当前写作的 section ID")
    current_section_title: str = Field(description="当前节的标题")
    current_section_summary: str = Field(default="", description="当前节的情节概要")
    chapter_prompt: Optional[str] = Field(
        default=None, description="本章写作提示/目标"
    )

    starting_state: str = Field(description="起始状态：本节开始时的情节状态")
    what_to_write: str = Field(description="要写什么：本节需要完成的情节推进")
    ending_state: str = Field(description="终止状态：本节结束时应达成的状态")

    involved_characters: list[CharacterCard] = Field(
        default_factory=list, description="本节涉及的角色卡片"
    )
    involved_world_settings: list[WorldSetting] = Field(
        default_factory=list, description="本节涉及的世界观卡片"
    )
    context_summaries: list[SectionSummary] = Field(
        default_factory=list, description="前文已完成章节的摘要"
    )

    def format_for_writer(self) -> str:
        """格式化为创作者 prompt 上下文"""
        parts = []
        parts.append(f"# 本节信息")
        parts.append(f"标题：{self.current_section_title}")
        parts.append(f"情节概要：{self.current_section_summary}")
        if self.chapter_prompt:
            parts.append(f"写作提示：{self.chapter_prompt}")
        parts.append("")
        parts.append(f"# 情节状态")
        parts.append(f"起始状态：{self.starting_state}")
        parts.append(f"要写什么：{self.what_to_write}")
        parts.append(f"终止状态：{self.ending_state}")
        parts.append("")

        if self.context_summaries:
            parts.append("# 前文摘要")
            for s in self.context_summaries:
                parts.append(s.format_context())
            parts.append("")

        if self.involved_characters:
            parts.append("# 涉及角色")
            for c in self.involved_characters:
                parts.append(c.format_card())
            parts.append("")

        if self.involved_world_settings:
            parts.append("# 涉及世界观设定")
            for w in self.involved_world_settings:
                parts.append(w.format_card())
            parts.append("")

        return "\n".join(parts)


# ═══════════════════════════════════════════════════════════
# 审查者 → 修订者
# ═══════════════════════════════════════════════════════════

class ReviewIssue(BaseModel):
    """单个审查问题"""

    location: str = Field(description="问题在原文中的位置引用")
    issue_type: Literal[
        "logic",
        "character_consistency",
        "world_setting",
        "plot_hole",
        "pacing",
        "dialogue",
    ] = Field(description="问题类型")
    severity: Literal["critical", "major", "minor"] = Field(
        default="major", description="严重程度"
    )
    description: str = Field(description="问题描述")
    suggestion: str = Field(default="", description="修改建议")


class ReviewResult(BaseModel):
    """审查者的输出"""

    issues: list[ReviewIssue] = Field(
        default_factory=list, description="发现的问题列表"
    )
    overall_assessment: str = Field(
        default="", description="总体评价"
    )
    has_critical_issues: bool = Field(
        default=False,
        description="是否有严重问题需要在修订后重新审查",
    )

    def format_for_reviser(self) -> str:
        """格式化为修订者 prompt 上下文"""
        if not self.issues:
            return "审查通过，未发现问题。"
        parts = []
        parts.append(f"总体评价：{self.overall_assessment}")
        parts.append("")
        for i, issue in enumerate(self.issues, 1):
            parts.append(f"问题 {i}：")
            parts.append(f"  严重程度：{issue.severity}")
            parts.append(f"  类型：{issue.issue_type}")
            parts.append(f"  位置：{issue.location}")
            parts.append(f"  描述：{issue.description}")
            if issue.suggestion:
                parts.append(f"  建议：{issue.suggestion}")
            parts.append("")
        return "\n".join(parts)
