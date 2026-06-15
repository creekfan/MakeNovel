"""Novel Agent Pipeline — 串联五个 Agent 的完整写作流程"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .agents.creator import CreatorAgent
from .agents.polisher import PolisherAgent
from .agents.preparer import PreparerAgent
from .agents.reviewer import ReviewerAgent
from .agents.reviser import ReviserAgent
from .llm import LLMClient
from .models.character import CharacterCard
from .models.messages import PreparationResult, ReviewResult
from .models.outline import OutlineTree
from .models.summary import SectionSummary
from .models.world import WorldSetting


@dataclass
class PipelineResult:
    """Pipeline 完整执行结果"""

    section_id: str
    preparation: PreparationResult
    draft_content: str
    review_result: ReviewResult
    revised_content: str
    final_content: str
    logs: list[str] = field(default_factory=list)


class NovelAgentPipeline:
    """小说 Agent 写作管道"""

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        llm: Optional[LLMClient] = None,
    ):
        if skills_dir is None:
            skills_dir = Path(__file__).parent / "skills"
        self.skills_dir = Path(skills_dir)
        self.llm = llm
        self.preparer = PreparerAgent(skills_dir)
        self.creator = CreatorAgent(skills_dir)
        self.reviewer = ReviewerAgent(skills_dir)
        self.reviser = ReviserAgent(skills_dir)
        self.polisher = PolisherAgent(skills_dir)

    def run(
        self,
        section_id: str,
        outline_tree: OutlineTree,
        characters: list[CharacterCard],
        world_settings: list[WorldSetting],
        summaries: list[SectionSummary],
        content_override: Optional[str] = None,
    ) -> PipelineResult:
        """执行完整写作流程"""
        logs: list[str] = []

        # ─── 阶段 1：准备 ───
        logs.append("[准备者] 开始准备材料...")
        preparation = self.preparer.prepare(
            section_id=section_id,
            outline_tree=outline_tree,
            summaries=summaries,
            characters=characters,
            world_settings=world_settings,
            llm=self.llm,
        )
        logs.append(
            f"[准备者] 完成 — 涉及 {len(preparation.involved_characters)} 个角色, "
            f"{len(preparation.involved_world_settings)} 个世界观设定"
        )

        # ─── 阶段 2：创作 ───
        logs.append("[创作者] 开始写作...")
        draft_content = self.creator.write(
            preparation, llm=self.llm, content=content_override
        )
        logs.append(f"[创作者] 完成 — 正文长度 {len(draft_content)} 字")

        # ─── 阶段 3：审查 ───
        logs.append("[审查者] 开始审查...")
        review_result = self.reviewer.review(
            content=draft_content,
            characters=preparation.involved_characters,
            world_settings=preparation.involved_world_settings,
            llm=self.llm,
        )
        issue_count = len(review_result.issues)
        logs.append(
            f"[审查者] 完成 — 发现 {issue_count} 个问题 "
            f"({'含严重问题' if review_result.has_critical_issues else '无严重问题'})"
        )

        # ─── 阶段 4：修订 ───
        if review_result.issues:
            logs.append("[修订者] 开始修订...")
            revised_content = self.reviser.revise(
                draft_content, review_result, llm=self.llm
            )
            logs.append("[修订者] 完成")

            if review_result.has_critical_issues:
                logs.append("[审查者] 二次审查...")
                review_result2 = self.reviewer.review(
                    content=revised_content,
                    characters=preparation.involved_characters,
                    world_settings=preparation.involved_world_settings,
                    llm=self.llm,
                )
                if review_result2.issues:
                    logs.append("[修订者] 二次修订...")
                    revised_content = self.reviser.revise(
                        revised_content, review_result2, llm=self.llm
                    )
                review_result = review_result2
        else:
            revised_content = draft_content

        # ─── 阶段 5：润色 ───
        logs.append("[润色者] 开始润色...")
        final_content = self.polisher.polish(revised_content, llm=self.llm)
        logs.append(f"[润色者] 完成 — 最终正文长度 {len(final_content)} 字")

        logs.append("[Pipeline] 全部完成")

        return PipelineResult(
            section_id=section_id,
            preparation=preparation,
            draft_content=draft_content,
            review_result=review_result,
            revised_content=revised_content,
            final_content=final_content,
            logs=logs,
        )

    def run_step_by_step(
        self,
        section_id: str,
        outline_tree: OutlineTree,
        characters: list[CharacterCard],
        world_settings: list[WorldSetting],
        summaries: list[SectionSummary],
    ) -> dict:
        """分步执行，返回每步的 prompt 和占位输出（调试用）"""
        result: dict = {}

        preparation = self.preparer.prepare(
            section_id=section_id,
            outline_tree=outline_tree,
            summaries=summaries,
            characters=characters,
            world_settings=world_settings,
            llm=None,
        )
        result["preparation"] = preparation.model_dump()
        result["writer_prompt"] = self.creator.build_prompt(preparation)

        placeholder_content = self.creator.write(preparation)
        result["placeholder_content"] = placeholder_content

        result["reviewer_prompt"] = self.reviewer.build_prompt(
            content=placeholder_content,
            characters=preparation.involved_characters,
            world_settings=preparation.involved_world_settings,
        )

        dummy_review = ReviewResult(
            issues=[],
            overall_assessment="无问题",
            has_critical_issues=False,
        )
        result["reviser_prompt"] = self.reviser.build_prompt(
            content=placeholder_content,
            review_result=dummy_review,
        )

        result["polisher_prompt"] = self.polisher.build_prompt(
            content=placeholder_content
        )

        return result
