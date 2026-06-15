"""修订者 (Reviser) — 根据审查反馈修改正文"""

from pathlib import Path
from typing import Optional

from ..llm import LLMClient
from ..models.messages import ReviewResult


class ReviserAgent:
    """修订者 Agent"""

    prompt_template: str

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            skills_dir = Path(__file__).parent.parent / "skills"
        self.skills_dir = Path(skills_dir)
        self.prompt_template = (self.skills_dir / "reviser.md").read_text(
            encoding="utf-8"
        )

    def build_prompt(
        self,
        content: str,
        review_result: ReviewResult,
    ) -> str:
        issues_text = review_result.format_for_reviser()
        context = f"## 正文\n\n{content}\n\n## 审查问题\n\n{issues_text}"
        return f"{self.prompt_template}\n\n---\n\n{context}"

    def revise(
        self,
        content: str,
        review_result: ReviewResult,
        llm: Optional[LLMClient] = None,
        revised_content: Optional[str] = None,
    ) -> str:
        """执行修订。如果提供 LLM，调用 AI 修订；否则用 revised_content 或原文。"""
        if revised_content is not None:
            return revised_content
        if not review_result.issues:
            return content
        if llm:
            return self._revise_with_llm(content, review_result, llm)
        issue_count = len(review_result.issues)
        return (
            f"{content}\n\n"
            f"[修订占位：发现 {issue_count} 个问题，待 LLM 接入后修订]"
        )

    def _revise_with_llm(
        self,
        content: str,
        review_result: ReviewResult,
        llm: LLMClient,
    ) -> str:
        issues_text = review_result.format_for_reviser()
        user_message = f"## 正文\n\n{content}\n\n## 审查问题\n\n{issues_text}"

        return llm.chat(
            system_prompt=self.prompt_template,
            user_message=user_message,
            temperature=0.6,
        )
