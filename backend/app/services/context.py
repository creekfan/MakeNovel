from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Novel, Character, CharacterRelationship, Setting, OutlineNode


async def build_context(
    db: AsyncSession,
    novel_id: int,
    active_character_ids: list[int] | None = None,
    active_setting_ids: list[int] | None = None,
    current_scene_id: int | None = None,
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
    elif active_character_ids is not None and not active_character_ids:
        active_chars = []
    else:
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

    outline_nodes = (await db.execute(
        select(OutlineNode).where(OutlineNode.novel_id == novel_id)
    )).scalars().all()

    if outline_nodes:
        node_map: dict[int | None, list[OutlineNode]] = {}
        node_by_id: dict[int, OutlineNode] = {}
        for n in outline_nodes:
            pid = n.parent_id
            if pid not in node_map:
                node_map[pid] = []
            node_map[pid].append(n)
            node_by_id[n.id] = n

        for pid in node_map:
            node_map[pid].sort(key=lambda n: n.sort_order or 0)

        volumes = [n for n in outline_nodes if n.node_type == 'volume']
        if volumes:
            parts.append("\n## 大纲结构")
            for vol in volumes[:10]:
                parts.append(f"\n### {vol.title}")
                if vol.summary:
                    parts.append(f"  主题：{vol.summary}")
                for ch in node_map.get(vol.id, []):
                    if ch.node_type == 'chapter':
                        parts.append(f"\n#### {ch.title}")
                        if ch.summary:
                            parts.append(f"  概要：{ch.summary}")
                        if ch.chapter_prompt:
                            parts.append(f"  创作重点：{ch.chapter_prompt}")
                        for sc in node_map.get(ch.id, []):
                            if sc.node_type == 'scene':
                                line = f"  - {sc.title}"
                                if sc.summary:
                                    line += f"：{sc.summary[:50]}"
                                if sc.content:
                                    line += f"（已写{len(sc.content)}字）"
                                parts.append(line)

        if current_scene_id and current_scene_id in node_by_id:
            cur_scene = node_by_id[current_scene_id]
            if cur_scene.chapter_prompt:
                parts.append(f"\n## 本节创作重点\n{cur_scene.chapter_prompt}")

        if current_scene_id:
            all_scenes = []
            for vol in volumes:
                for ch in node_map.get(vol.id, []):
                    if ch.node_type == 'chapter':
                        for sc in node_map.get(ch.id, []):
                            if sc.node_type == 'scene':
                                all_scenes.append(sc)

            idx = next((i for i, s in enumerate(all_scenes) if s.id == current_scene_id), -1)
            if idx > 0:
                prev_scene = all_scenes[idx - 1]
                if prev_scene.summary:
                    parts.append(f"\n## 上一节摘要\n{prev_scene.summary}")

            recent_scenes = all_scenes[max(0, idx - 3):idx]
            recent_with_content = [s for s in reversed(recent_scenes) if s.summary]
            if recent_with_content:
                parts.append("\n## 前文摘要（最近已写各节）")
                for sc in recent_with_content[:3]:
                    parts.append(f"\n{sc.title}：{sc.summary[:200]}")

    return "\n".join(parts)
