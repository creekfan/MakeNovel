from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Novel, Chapter, Character, CharacterRelationship, Setting, OutlineNode
from app.core.config import settings


async def build_context(
    db: AsyncSession,
    novel_id: int,
    chapter_id: int | None = None,
    active_character_ids: list[int] | None = None,
    active_setting_ids: list[int] | None = None,
) -> str:
    parts = []

    novel = await db.get(Novel, novel_id)
    if not novel:
        return ""

    parts.append(f"小说标题：《{novel.title}》")
    parts.append(f"类型：{novel.genre or '未设定'}")

    all_characters = (await db.execute(
        select(Character).where(Character.novel_id == novel_id)
    )).scalars().all()
    char_map = {c.id: c for c in all_characters}

    if active_character_ids:
        active_chars = [char_map[cid] for cid in active_character_ids if cid in char_map]
    else:
        if chapter_id:
            chapter = await db.get(Chapter, chapter_id)
            if chapter and chapter.character_snapshot:
                active_chars = [char_map[cid] for cid in chapter.character_snapshot.get("character_ids", []) if cid in char_map]
            else:
                active_chars = []
        else:
            active_chars = []

    if active_character_ids is not None and not active_character_ids:
        active_chars = []
    elif not active_chars:
        active_chars = all_characters[:5]

    if active_chars:
        parts.append("\n## 角色档案")
        for char in active_chars:
            char_text = f"\n### {char.name}（{char.role}）"
            profile = char.profile or {}
            if profile.get("appearance"):
                char_text += f"\n外貌：{profile['appearance']}"
            if profile.get("age"):
                char_text += f"\n年龄：{profile['age']}"
            if profile.get("personality"):
                char_text += f"\n性格：{profile['personality']}"
            if profile.get("background"):
                char_text += f"\n背景：{profile['background']}"
            if profile.get("speech_style"):
                char_text += f"\n说话风格：{profile['speech_style']}"
            if char.arc:
                char_text += f"\n角色弧光：{char.arc}"

            relationships = (await db.execute(
                select(CharacterRelationship).where(
                    (CharacterRelationship.source_id == char.id) |
                    (CharacterRelationship.target_id == char.id)
                )
            )).scalars().all()
            if relationships:
                char_text += "\n关系："
                for rel in relationships:
                    other = char_map.get(rel.target_id) if rel.source_id == char.id else char_map.get(rel.source_id)
                    if other:
                        char_text += f"\n  - {other.name} ({rel.relation_type})"
                        if rel.description:
                            char_text += f": {rel.description}"

            parts.append(char_text)

    if chapter_id:
        chapter = await db.get(Chapter, chapter_id)
        if chapter and chapter.chapter_prompt:
            parts.append(f"\n## 本章创作重点（作者设定）\n{chapter.chapter_prompt}")

        recent_chapters = (await db.execute(
            select(Chapter)
            .where(Chapter.novel_id == novel_id, Chapter.id < chapter_id)
            .order_by(desc(Chapter.chapter_number))
            .limit(3)
        )).scalars().all()

        if recent_chapters:
            parts.append("\n## 前文摘要（最近3章）")
            for ch in reversed(recent_chapters):
                if ch.summary:
                    parts.append(f"\n第{ch.chapter_number}章《{ch.title}》：{ch.summary}")

    current_settings = (await db.execute(
        select(Setting).where(Setting.novel_id == novel_id)
    )).scalars().all()
    if active_setting_ids is not None:
        current_settings = [s for s in current_settings if s.id in active_setting_ids]

    if current_settings:
        parts.append("\n## 世界观设定")
        cat_labels = {
            "location": "环境场景", "faction": "势力组织", "rule": "规则体系",
            "race": "种族物种", "item": "重要物品", "profession": "职业", "history": "历史事件",
        }
        for s in current_settings[:10]:
            cat = cat_labels.get(s.category, s.category)
            label = f"{cat}"
            if s.location_type:
                label += f" / {s.location_type}"
            parts.append(f"\n### {s.name}（{label}）\n{s.description}")
            if s.notable_features:
                parts.append("  关键特征：" + "、".join(s.notable_features[:5]))

    # Inject outline structure
    outline_nodes = (await db.execute(
        select(OutlineNode).where(OutlineNode.novel_id == novel_id)
    )).scalars().all()

    if outline_nodes:
        node_map: dict[int, list[OutlineNode]] = {}
        for n in outline_nodes:
            pid = n.parent_id or 0
            if pid not in node_map:
                node_map[pid] = []
            node_map[pid].append(n)

        def collect_scenes(vol_id: int, depth: int = 0) -> list[OutlineNode]:
            result: list[OutlineNode] = []
            for child in node_map.get(vol_id, []):
                if child.node_type == 'scene':
                    result.append(child)
                result.extend(collect_scenes(child.id, depth + 1))
            return result

        volumes = [n for n in outline_nodes if n.node_type == 'volume']
        if volumes:
            parts.append("\n## 大纲结构")
            for vol in volumes[:10]:
                parts.append(f"\n### {vol.title}")
                if vol.summary:
                    parts.append(f"  主题：{vol.summary}")
                scenes = collect_scenes(vol.id)
                if scenes:
                    for scene in scenes[:20]:
                        line = f"  - {scene.title}"
                        if scene.summary:
                            line += f"：{scene.summary[:50]}"
                        if scene.content:
                            line += f"（已写{len(scene.content)}字）"
                        parts.append(line)
                else:
                    parts.append("  （尚无节）")

    return "\n".join(parts)
