from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

from .. import storage


class _NoArgs(BaseModel):
    pass


class GetOutlineTool(BaseTool):
    name: str = "get_outline"
    description: str = "获取当前小说的完整大纲结构（卷→章→节）。无需任何参数，直接调用。"
    args_schema: Type[BaseModel] = _NoArgs
    novel_id: str = ""

    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        data = storage.get_outline(self.novel_id)
        if not data:
            return "暂无大纲"
        lines = [f"小说：{data.get('novel_title', '')}"]
        for vol in data.get("volumes", []):
            lines.append(f"\n## {vol.get('title', '未命名卷')} [{vol.get('status', 'planned')}]")
            if vol.get("summary"):
                lines.append(f"概要：{vol['summary']}")
            for ch in vol.get("children", []):
                lines.append(f"\n### {ch.get('title', '未命名章')} [{ch.get('status', 'planned')}]")
                if ch.get("summary"):
                    lines.append(f"概要：{ch['summary']}")
                if ch.get("chapter_prompt"):
                    lines.append(f"重点：{ch['chapter_prompt']}")
                for sec in ch.get("children", []):
                    lines.append(f"- {sec.get('title', '未命名单节')} [{sec.get('status', 'planned')}]")
                    if sec.get("summary"):
                        lines.append(f"  情节概要：{sec['summary']}")
        return "\n".join(lines)


class GetCharactersTool(BaseTool):
    name: str = "get_characters"
    description: str = "获取当前小说的角色档案列表。无需任何参数，直接调用。"
    args_schema: Type[BaseModel] = _NoArgs
    novel_id: str = ""

    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        chars = storage.get_characters(self.novel_id)
        if not chars:
            return "暂无角色"
        lines = ["角色列表："]
        for c in chars:
            lines.append(f"\n### {c.get('name', '未命名')}（{c.get('role', 'unknown')}）")
            if c.get("appearance"):
                lines.append(f"外貌：{c['appearance']}")
            if c.get("personality"):
                lines.append(f"性格：{c['personality']}")
            if c.get("background"):
                lines.append(f"背景：{c['background']}")
            if c.get("current_state"):
                lines.append(f"当前状态：{c['current_state']}")
            if c.get("arc"):
                lines.append(f"角色弧：{c['arc']}")
            if c.get("abilities"):
                lines.append(f"能力：{c['abilities']}")
            if c.get("speech_style"):
                lines.append(f"说话风格：{c['speech_style']}")
            if c.get("relationships"):
                lines.append("关系：")
                for r in c["relationships"]:
                    lines.append(f"  - {r.get('relation_type', '')}: {r.get('target_id', '')} — {r.get('description', '')}")
        return "\n".join(lines)


class GetWorldSettingsTool(BaseTool):
    name: str = "get_world_settings"
    description: str = "获取当前小说的世界观设定列表。无需任何参数，直接调用。"
    args_schema: Type[BaseModel] = _NoArgs
    novel_id: str = ""

    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        settings = storage.get_world_settings(self.novel_id)
        if not settings:
            return "暂无世界观设定"
        lines = ["世界观设定列表："]
        for s in settings:
            lines.append(f"\n### {s.get('name', '未命名')}（{s.get('category', 'unknown')}）")
            if s.get("description"):
                lines.append(f"描述：{s['description']}")
            if s.get("notable_features"):
                lines.append("特征：" + "、".join(s["notable_features"]))
        return "\n".join(lines)


class GetSummariesTool(BaseTool):
    name: str = "get_summaries"
    description: str = "获取当前小说各节的摘要汇总。无需任何参数，直接调用。"
    args_schema: Type[BaseModel] = _NoArgs
    novel_id: str = ""

    def _run(self, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        summaries = storage.get_summaries(self.novel_id)
        if not summaries:
            return "暂无摘要"
        lines = ["前文摘要："]
        for s in summaries[-5:]:
            lines.append(f"\n### {s.get('section_title', '未知节')}")
            lines.append(f"概要：{s.get('summary', '')}")
            if s.get("key_events"):
                lines.append("关键事件：" + "；".join(s["key_events"]))
        return "\n".join(lines)


class SearchMemoryInput(BaseModel):
    query: str = Field(description="搜索查询文本")


class SearchMemoryTool(BaseTool):
    name: str = "search_memory"
    description: str = "在当前小说已写内容中检索与 query 语义相关的内容（RAG 记忆检索）。只需传入 query。"
    args_schema: Type[BaseModel] = SearchMemoryInput
    novel_id: str = ""

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        from .memory import search_sections
        results = search_sections(self.novel_id, query, top_k=3)
        if not results:
            return "未找到相关内容"
        lines = ["相关前文检索结果："]
        for r in results:
            lines.append(f"\n### {r.get('title', '未知节')}（相似度：{r.get('score', 0):.3f}）")
            content = r.get("content", "")
            if content:
                lines.append(content[:500] + ("..." if len(content) > 500 else ""))
        return "\n".join(lines)


class FinishInput(BaseModel):
    result: str = Field(description="创作完成的正文内容")


class FinishTool(BaseTool):
    name: str = "finish"
    description: str = "完成任务，返回最终结果。调用此工具时传入你创作的正文内容作为 result 参数。"
    args_schema: Type[BaseModel] = FinishInput

    def _run(self, result: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        return result


def get_all_tools(novel_id: str) -> list[BaseTool]:
    return [
        GetOutlineTool(novel_id=novel_id),
        GetCharactersTool(novel_id=novel_id),
        GetWorldSettingsTool(novel_id=novel_id),
        GetSummariesTool(novel_id=novel_id),
        SearchMemoryTool(novel_id=novel_id),
        FinishTool(),
    ]
