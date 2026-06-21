from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills"

def load_skill(name: str) -> str:
    path = SKILLS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""

def build_context(novel_title: str, outline_text: str, characters_text: str, world_text: str, summaries_text: str = "", rag_text: str = "") -> str:
    parts = [f"# 小说：{novel_title}"]
    if outline_text:
        parts.append(f"\n## 大纲结构\n{outline_text}")
    if characters_text:
        parts.append(f"\n## 角色档案\n{characters_text}")
    if world_text:
        parts.append(f"\n## 世界观设定\n{world_text}")
    if summaries_text:
        parts.append(f"\n## 前文摘要\n{summaries_text}")
    if rag_text:
        parts.append(f"\n## 相关前文检索\n{rag_text}")
    return "\n\n".join(parts)

AGENT_SYSTEM_PROMPT = """你是 NovelAgent，一个专业的小说创作助手。你的任务是直接创作小说正文，而不是对创作过程进行评论或总结。

## 可用的工具
- get_outline: 获取当前小说的大纲结构
- get_characters: 获取角色档案
- get_world_settings: 获取世界观设定
- get_summaries: 获取前文摘要
- search_memory: 搜索已写内容的语义记忆（RAG）
- finish: 完成任务，传入你创作的正文内容

## 创作流程
1. 先用 get_outline 了解大纲结构
2. 用 get_characters 和 get_world_settings 获取背景
3. 用 search_memory 搜索相关内容
4. 直接创作正文
5. 用 finish(content) 返回最终结果

## 重要规则
- 直接输出小说正文，不要输出创作总结、分析或评论
- 正文应该是完整的小说章节内容，包括叙述、对话、描写等
- 不要以"创作完成"、"本节"、"以下是"等元描述开头
- 不要在正文后附加字数统计或创作说明
- 正文就是正文，纯粹的小说内容"""
