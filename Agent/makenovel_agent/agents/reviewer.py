"""审查者 (Reviewer) — 检查正文逻辑、人物形象、世界观问题"""

import json
from pathlib import Path
from typing import Optional

from ..llm import LLMClient
from ..models.character import CharacterCard
from ..models.messages import ReviewIssue, ReviewResult
from ..models.world import WorldSetting


class ReviewerAgent:
    """审查者 Agent"""

    prompt_template: str

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            skills_dir = Path(__file__).parent.parent / "skills"
        self.skills_dir = Path(skills_dir)
        self.prompt_template = (self.skills_dir / "reviewer.md").read_text(
            encoding="utf-8"
        )

    def build_prompt(
        self,
        content: str,
        characters: list[CharacterCard],
        world_settings: list[WorldSetting],
    ) -> str:
        char_text = "\n\n".join(c.format_card() for c in characters)
        world_text = "\n\n".join(w.format_card() for w in world_settings)
        context = (
            f"## 正文\n\n{content}\n\n"
            f"## 角色卡片\n\n{char_text}\n\n"
            f"## 世界观设定\n\n{world_text}"
        )
        return f"{self.prompt_template}\n\n---\n\n{context}"

    def review(
        self,
        content: str,
        characters: list[CharacterCard],
        world_settings: list[WorldSetting],
        llm: Optional[LLMClient] = None,
        issues: Optional[list[ReviewIssue]] = None,
        overall_assessment: str = "",
    ) -> ReviewResult:
        """执行审查。如果提供 LLM，调用 AI 审查；否则用 issues 或默认通过。"""
        if issues is not None:
            return ReviewResult(
                issues=issues,
                overall_assessment=overall_assessment,
                has_critical_issues=any(
                    i.severity == "critical" for i in issues
                ),
            )
        if llm:
            return self._review_with_llm(content, characters, world_settings, llm)
        return ReviewResult(
            issues=[],
            overall_assessment="占位审查：未接入 LLM，默认通过。",
            has_critical_issues=False,
        )

    def _review_with_llm(
        self,
        content: str,
        characters: list[CharacterCard],
        world_settings: list[WorldSetting],
        llm: LLMClient,
    ) -> ReviewResult:
        char_text = "\n\n".join(c.format_card() for c in characters)
        world_text = "\n\n".join(w.format_card() for w in world_settings)
        user_message = (
            f"## 正文\n\n{content}\n\n"
            f"## 角色卡片\n\n{char_text}\n\n"
            f"## 世界观设定\n\n{world_text}"
        )

        result = llm.chat_json(
            system_prompt=self.prompt_template,
            user_message=user_message,
            temperature=0.3,
        )

        issues = [ReviewIssue(**i) for i in result.get("issues", [])]
        return ReviewResult(
            issues=issues,
            overall_assessment=result.get("overall_assessment", ""),
            has_critical_issues=any(
                i.severity == "critical" for i in issues
            ),
        )
