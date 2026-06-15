"""创作者 (Creator) — 根据准备材料编排故事"""

from pathlib import Path
from typing import Optional

from ..llm import LLMClient
from ..models.messages import PreparationResult


class CreatorAgent:
    """创作者 Agent"""

    prompt_template: str

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            skills_dir = Path(__file__).parent.parent / "skills"
        self.skills_dir = Path(skills_dir)
        self.prompt_template = (self.skills_dir / "writer.md").read_text(
            encoding="utf-8"
        )

    def build_prompt(self, preparation: PreparationResult) -> str:
        context = preparation.format_for_writer()
        return f"{self.prompt_template}\n\n---\n\n{context}"

    def write(
        self,
        preparation: PreparationResult,
        llm: Optional[LLMClient] = None,
        content: Optional[str] = None,
    ) -> str:
        """执行创作。如果提供 LLM，调用 AI 生成；否则用 content 或占位输出。"""
        if content is not None:
            return content
        if llm:
            return self._write_with_llm(preparation, llm)
        return self._generate_placeholder(preparation)

    def _write_with_llm(
        self,
        preparation: PreparationResult,
        llm: LLMClient,
    ) -> str:
        prompt = self.build_prompt(preparation)
        return llm.chat(
            system_prompt=self.prompt_template,
            user_message=preparation.format_for_writer(),
            temperature=0.8,
        )

    def _generate_placeholder(self, preparation: PreparationResult) -> str:
        chars = ", ".join(c.name for c in preparation.involved_characters)
        worlds = ", ".join(w.name for w in preparation.involved_world_settings)
        return (
            f"[待创作]\n"
            f"本节：{preparation.current_section_title}\n"
            f"概要：{preparation.current_section_summary}\n"
            f"起始：{preparation.starting_state}\n"
            f"内容：{preparation.what_to_write}\n"
            f"终止：{preparation.ending_state}\n"
            f"角色：{chars}\n"
            f"场景：{worlds}\n"
        )
