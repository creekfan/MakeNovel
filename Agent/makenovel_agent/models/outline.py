from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class OutlineNode(BaseModel):
    """卷-章-节树节点"""

    id: str = Field(description="节点唯一标识")
    title: str = Field(description="名称")
    node_type: Literal["volume", "chapter", "section"] = Field(
        description="节点类型：卷/章/节"
    )
    summary: str = Field(default="", description="情节概要")
    status: Literal["planned", "draft", "revising", "done"] = Field(
        default="planned", description="写作状态"
    )
    content: Optional[str] = Field(
        default=None, description="正文内容（仅 section 类型）"
    )
    chapter_prompt: Optional[str] = Field(
        default=None, description="本节写作提示/目标"
    )
    children: list[OutlineNode] = Field(
        default_factory=list, description="子节点（递归树结构）"
    )
    sort_order: float = Field(default=0.0, description="排序权重")

    @property
    def is_leaf(self) -> bool:
        return self.node_type == "section" or len(self.children) == 0

    def find_node(self, node_id: str) -> Optional[OutlineNode]:
        """在树中递归查找指定ID的节点"""
        if self.id == node_id:
            return self
        for child in self.children:
            result = child.find_node(node_id)
            if result:
                return result
        return None

    def get_ancestor_chain(self, node_id: str) -> list[OutlineNode]:
        """获取从根到指定节点的路径（用于定位所在卷章）"""
        if self.id == node_id:
            return [self]
        for child in self.children:
            result = child.get_ancestor_chain(node_id)
            if result:
                return [self] + result
        return []

    def get_section_path(self, node_id: str) -> str:
        """获取 section 的完整路径字符串，如 '第一卷 > 第一章 > 第一节'"""
        chain = self.get_ancestor_chain(node_id)
        return " > ".join(node.title for node in chain)


class OutlineTree(BaseModel):
    """完整大纲树（根为所有卷的虚拟容器）"""

    novel_id: str = Field(description="所属小说ID")
    novel_title: str = Field(default="", description="小说标题")
    volumes: list[OutlineNode] = Field(
        default_factory=list, description="卷列表（根为volume节点）"
    )

    def find_node(self, node_id: str) -> Optional[OutlineNode]:
        for volume in self.volumes:
            result = volume.find_node(node_id)
            if result:
                return result
        return None

    def get_ordered_sections(self) -> list[OutlineNode]:
        """获取所有 section 节点，按卷章节顺序排列"""
        sections: list[OutlineNode] = []
        for volume in sorted(self.volumes, key=lambda v: v.sort_order):
            for chapter in sorted(volume.children, key=lambda c: c.sort_order):
                for section in sorted(chapter.children, key=lambda s: s.sort_order):
                    sections.append(section)
        return sections

    def get_previous_sections(self, section_id: str, count: int = 3) -> list[OutlineNode]:
        """获取指定section之前已完成的sections"""
        sections = self.get_ordered_sections()
        result = []
        found = False
        for s in reversed(sections):
            if s.id == section_id:
                found = True
                continue
            if found and s.status == "done":
                result.append(s)
                if len(result) >= count:
                    break
        return list(reversed(result))
