"""润色者 (Polisher) — 对正文进行润色，不改本意"""

from pathlib import Path
from typing import Optional

from ..llm import LLMClient


class PolisherAgent:
    """润色者 Agent"""

    prompt_template: str

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            skills_dir = Path(__file__).parent.parent / "skills"
        self.skills_dir = Path(skills_dir)
        self.prompt_template = (self.skills_dir / "polisher.md").read_text(
            encoding="utf-8"
        )

    def build_prompt(self, content: str) -> str:
        return f"{self.prompt_template}\n\n---\n\n## 正文\n\n{content}"

    def polish(
        self,
        content: str,
        llm: Optional[LLMClient] = None,
        polished_content: Optional[str] = None,
    ) -> str:
        """执行润色。如果提供 LLM，调用 AI 润色；否则用 polished_content 或原文。"""
        if polished_content is not None:
            return polished_content
        if llm:
            return self._polish_with_llm(content, llm)
        return content

    def _polish_with_llm(
        self,
        content: str,
        llm: LLMClient,
    ) -> str:
        return llm.chat(
            system_prompt=self.prompt_template,
            user_message=f"## 正文\n\n{content}",
            temperature=0.5,
        )
