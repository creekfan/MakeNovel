"""准备者 (Preparer) — 读取本节情节概要，准备写作材料"""

from pathlib import Path
from typing import Optional

from ..llm import LLMClient
from ..models.character import CharacterCard
from ..models.messages import PreparationResult
from ..models.outline import OutlineNode, OutlineTree
from ..models.summary import SectionSummary
from ..models.world import WorldSetting


class PreparerAgent:
    """准备者 Agent"""

    prompt_template: str

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            skills_dir = Path(__file__).parent.parent / "skills"
        self.skills_dir = Path(skills_dir)
        self.prompt_template = (self.skills_dir / "preparer.md").read_text(
            encoding="utf-8"
        )

    def prepare(
        self,
        section_id: str,
        outline_tree: OutlineTree,
        summaries: list[SectionSummary],
        characters: list[CharacterCard],
        world_settings: list[WorldSetting],
        llm: Optional[LLMClient] = None,
    ) -> PreparationResult:
        """准备写作材料。如果提供 LLM，则用 LLM 增强分析；否则用规则算法。"""

        current_node = outline_tree.find_node(section_id)
        if current_node is None:
            raise ValueError(f"未找到 section: {section_id}")
        if current_node.node_type != "section":
            raise ValueError(
                f"节点 {section_id} 类型为 {current_node.node_type}，必须是 section"
            )

        if llm:
            return self._prepare_with_llm(
                section_id, current_node, outline_tree,
                summaries, characters, world_settings, llm,
            )
        else:
            return self._prepare_rule_based(
                section_id, current_node, outline_tree,
                summaries, characters, world_settings,
            )

    def _prepare_with_llm(
        self,
        section_id: str,
        current_node: OutlineNode,
        outline_tree: OutlineTree,
        summaries: list[SectionSummary],
        characters: list[CharacterCard],
        world_settings: list[WorldSetting],
        llm: LLMClient,
    ) -> PreparationResult:
        """用 LLM 进行状态分析和要素选择"""

        # 构建上下文
        chain: list[OutlineNode] = []
        for vol in outline_tree.volumes:
            result = vol.get_ancestor_chain(section_id)
            if result:
                chain = result
                break

        # 构建大纲路径描述
        outline_context_parts = []
        for node in chain:
            outline_context_parts.append(f"[{node.node_type}] {node.title}: {node.summary}")
        outline_context = "\n".join(outline_context_parts)

        # 前文摘要
        previous_sections = outline_tree.get_previous_sections(section_id, count=5)
        relevant_summaries = [
            s for s in summaries
            if any(ps.id == s.section_id for ps in previous_sections)
        ]
        summaries_text = "\n\n".join(
            s.format_context() for s in relevant_summaries
        ) if relevant_summaries else "(无前文章节)"

        # 角色列表
        chars_text = "\n\n".join(
            f"[{c.id}] {c.format_card()}\n关系: " +
            "; ".join(f"{r.source_id}->{r.target_id}({r.relation_type})" for r in c.relationships)
            for c in characters
        )

        # 世界观列表
        worlds_text = "\n\n".join(
            f"[{w.id}] {w.format_card()}" for w in world_settings
        )

        user_message = f"""## 当前章节在大纲中的位置

{outline_context}

## 前文摘要

{summaries_text}

## 全部角色

{chars_text}

## 全部世界观

{worlds_text}

请根据以上信息，分析本节的情节状态并选择涉及的角色和世界观。严格按 JSON 格式输出。"""

        result = llm.chat_json(
            system_prompt=self.prompt_template,
            user_message=user_message,
            temperature=0.3,
        )

        # 解析 LLM 返回的角色和世界观 ID
        involved_char_ids = result.get("involved_character_ids", [])
        involved_setting_ids = result.get("involved_setting_ids", [])

        char_map = {c.id: c for c in characters}
        world_map = {w.id: w for w in world_settings}

        involved_characters = [
            char_map[cid] for cid in involved_char_ids if cid in char_map
        ]
        involved_world_settings = [
            world_map[wid] for wid in involved_setting_ids if wid in world_map
        ]

        return PreparationResult(
            current_section_id=section_id,
            current_section_title=current_node.title,
            current_section_summary=current_node.summary,
            chapter_prompt=current_node.chapter_prompt,
            starting_state=result.get("starting_state", ""),
            what_to_write=result.get("what_to_write", ""),
            ending_state=result.get("ending_state", ""),
            involved_characters=involved_characters,
            involved_world_settings=involved_world_settings,
            context_summaries=relevant_summaries,
        )

    def _prepare_rule_based(
        self,
        section_id: str,
        current_node: OutlineNode,
        outline_tree: OutlineTree,
        summaries: list[SectionSummary],
        characters: list[CharacterCard],
        world_settings: list[WorldSetting],
    ) -> PreparationResult:
        """规则算法版本（无需 LLM）"""
        previous_sections = outline_tree.get_previous_sections(section_id, count=5)
        relevant_summaries = [
            s for s in summaries
            if any(ps.id == s.section_id for ps in previous_sections)
        ]

        chain: list[OutlineNode] = []
        for vol in outline_tree.volumes:
            result = vol.get_ancestor_chain(section_id)
            if result:
                chain = result
                break
        chapter_node = chain[-2] if len(chain) >= 2 else None

        starting_state = self._derive_starting_state(
            current_node, relevant_summaries, previous_sections
        )
        what_to_write = self._derive_what_to_write(current_node, chapter_node)
        ending_state = self._derive_ending_state(current_node, what_to_write)
        involved_characters = self._select_characters(
            current_node, relevant_summaries, characters
        )
        involved_world_settings = self._select_world_settings(
            current_node, relevant_summaries, world_settings
        )

        return PreparationResult(
            current_section_id=section_id,
            current_section_title=current_node.title,
            current_section_summary=current_node.summary,
            chapter_prompt=current_node.chapter_prompt,
            starting_state=starting_state,
            what_to_write=what_to_write,
            ending_state=ending_state,
            involved_characters=involved_characters,
            involved_world_settings=involved_world_settings,
            context_summaries=relevant_summaries,
        )

    def build_prompt(self, preparation: PreparationResult) -> str:
        return preparation.format_for_writer()

    # ─── 规则算法内部方法 ──────────────────────────────

    def _derive_starting_state(
        self,
        current_node: OutlineNode,
        relevant_summaries: list[SectionSummary],
        previous_sections: list[OutlineNode],
    ) -> str:
        if not relevant_summaries and not previous_sections:
            return "故事开始，一切尚未发生。"
        parts: list[str] = []
        for s in relevant_summaries:
            if s.summary:
                parts.append(s.summary)
        if not parts:
            for ps in previous_sections:
                if ps.summary:
                    parts.append(ps.summary)
        if parts:
            return "基于前文：\n" + "\n".join(parts)
        return "从前文发展至本节。"

    def _derive_what_to_write(
        self,
        current_node: OutlineNode,
        chapter_node: Optional[OutlineNode],
    ) -> str:
        parts: list[str] = []
        if current_node.summary:
            parts.append(current_node.summary)
        if current_node.chapter_prompt:
            parts.append(f"写作重点：{current_node.chapter_prompt}")
        if chapter_node and chapter_node.summary:
            parts.append(f"所属章节目标：{chapter_node.summary}")
        return "\n".join(parts) if parts else "按照大纲推进情节。"

    def _derive_ending_state(
        self, current_node: OutlineNode, what_to_write: str
    ) -> str:
        if current_node.summary:
            return f"完成以下情节的推进：{current_node.summary}"
        return "完成本节情节推进。"

    def _select_characters(
        self,
        current_node: OutlineNode,
        relevant_summaries: list[SectionSummary],
        characters: list[CharacterCard],
    ) -> list[CharacterCard]:
        text = current_node.summary + " " + (current_node.chapter_prompt or "")
        for s in relevant_summaries:
            text += " " + s.summary + " " + " ".join(s.key_events)
        if not text.strip() or not characters:
            return list(characters)
        selected: list[CharacterCard] = []
        for c in characters:
            if c.name in text:
                selected.append(c)
                continue
            for s in relevant_summaries:
                if c.id in s.character_state_changes:
                    selected.append(c)
                    break
        if not selected:
            selected = [c for c in characters if c.role in ("protagonist", "antagonist")]
        return selected

    def _select_world_settings(
        self,
        current_node: OutlineNode,
        relevant_summaries: list[SectionSummary],
        world_settings: list[WorldSetting],
    ) -> list[WorldSetting]:
        text = current_node.summary + " " + (current_node.chapter_prompt or "")
        for s in relevant_summaries:
            text += " " + s.summary
        if not text.strip() or not world_settings:
            return []
        selected: list[WorldSetting] = []
        for w in world_settings:
            if w.name in text:
                selected.append(w)
                continue
            for feature in w.notable_features:
                if feature in text:
                    selected.append(w)
                    break
        return selected
