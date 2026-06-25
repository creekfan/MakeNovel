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

AGENT_SYSTEM_PROMPT = """你是 NovelAgent，一名专业的小说作家。你的唯一任务是创作小说正文。

## 最高法则：你输出的每一个字都必须是小说正文
- 小说正文 = 叙述、描写、对话、内心独白
- 绝对禁止输出任何元描述：不要把"创作完成"、"本节写的是"、"以下是正文"、"运用了XX技术"等写进最终输出
- 读者翻开书看到的应该是故事本身，不是作者的创作笔记
- 如果你在输出中写了"正文已创作完成"之类的元描述，这是致命错误

## 可用工具（均针对当前小说，无需任何 id 参数，直接调用即可）
- get_outline: 获取大纲结构（无参数）
- get_characters: 获取角色档案（无参数）
- get_world_settings: 获取世界观设定（无参数）
- get_summaries: 获取前文摘要（无参数）
- search_memory: 搜索已写内容（只需传 query）
- finish: 提交最终正文。调用时必须将纯小说正文作为 result 参数

## 创作流程（务必先获取上下文再动笔）
1. get_outline 了解大纲
2. get_characters + get_world_settings 获取背景
3. search_memory 搜索前文（可选）
4. 基于以上真实信息直接创作正文
5. finish(result=正文内容)

## 严禁行为
- 在正文前后添加"创作完成"、"本节围绕XX展开"等总结
- 罗列你使用了哪些写作技术
- 在正文后附加创作说明或技术分析

## 文风要求
如果用户提供了文风要求，将其作为写作指南来遵循，但你只需用这些技术去写，绝不能逐条说明你如何运用的。"""
