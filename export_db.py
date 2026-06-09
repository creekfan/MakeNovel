"""Export MakeNovel SQLite DB to readable TXT file."""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import text
from app.core.database import engine

CATEGORY_LABELS = {
    "location": "环境场景", "faction": "势力组织", "rule": "规则体系",
    "race": "种族物种", "item": "重要物品", "profession": "职业", "history": "历史事件",
}

ROLE_LABELS = {
    "protagonist": "主角", "PROTAGONIST": "主角",
    "antagonist": "反派", "ANTAGONIST": "反派",
    "supporting": "配角", "SUPPORTING": "配角",
    "minor": "次要", "MINOR": "次要",
}

STATUS_LABELS = {
    "draft": "草稿", "DRAFT": "草稿",
    "revising": "修改中", "REVISING": "修改中",
    "done": "已完成", "DONE": "已完成",
}

async def export(output_path: str = "makenovel_export.txt"):
    lines = []
    lines.append("=" * 60)
    lines.append("  MakeNovel 小说项目导出")
    lines.append("=" * 60)

    async with engine.begin() as conn:
        # Novels
        novels = await conn.run_sync(
            lambda c: c.execute(text("SELECT * FROM novels ORDER BY id")).fetchall()
        )
        for novel in novels:
            nid = novel.id
            lines.append(f"\n{'='*60}")
            lines.append(f"  小说：{novel.title}")
            lines.append(f"{'='*60}")
            lines.append(f"  类型：{novel.genre or '未设定'}")
            if novel.description:
                lines.append(f"  简介：{novel.description}")
            if novel.style_notes:
                lines.append(f"  写作风格：{novel.style_notes}")
            lines.append(f"  目标字数：{novel.word_count_goal:,}")

            # Characters
            chars = await conn.run_sync(
                lambda c: c.execute(
                    text("SELECT * FROM characters WHERE novel_id = :nid ORDER BY id"), {"nid": nid}
                ).fetchall()
            )
            if chars:
                lines.append(f"\n【角色】({len(chars)}个)")
                for c in chars:
                    role = ROLE_LABELS.get(c.role, str(c.role))
                    lines.append(f"  >> {c.name}（{role}）")
                    profile = safe_json(c.profile)
                    if profile:
                        for k in ["age", "appearance", "personality", "background", "speech_style"]:
                            v = profile.get(k, "")
                            if v:
                                lines.append(f"     {LABELS_PROFILE.get(k, k)}：{v}")
                    if c.arc:
                        lines.append(f"     角色弧光：{c.arc}")
                    # Relationships
                    rels = await conn.run_sync(
                        lambda c2: c2.execute(
                            text("SELECT r.*, t.name as target_name FROM character_relationships r LEFT JOIN characters t ON r.target_id = t.id WHERE r.source_id = :cid"), {"cid": c.id}
                        ).fetchall()
                    )
                    if rels:
                        for r in rels:
                            lines.append(f"     关系：→ {r.target_name}（{r.relation_type}）{r.description or ''}")

            # Settings (world-building)
            settings = await conn.run_sync(
                lambda c: c.execute(
                    text("SELECT * FROM settings WHERE novel_id = :nid ORDER BY category, id"), {"nid": nid}
                ).fetchall()
            )
            if settings:
                lines.append(f"\n【世界观设定】({len(settings)}项)")
                for s in settings:
                    cat = CATEGORY_LABELS.get(s.category, s.category)
                    label = f"{cat}"
                    if s.location_type:
                        label += f" / {s.location_type}"
                    lines.append(f"  >> {s.name}（{label}）")
                    if s.description:
                        lines.append(f"     {s.description}")
                    features = safe_json_list(s.notable_features)
                    if features:
                        lines.append(f"     关键特征：{'、'.join(features[:10])}")

            # Outline
            outlines = await conn.run_sync(
                lambda c: c.execute(
                    text("SELECT * FROM outline_nodes WHERE novel_id = :nid ORDER BY sort_order, id"), {"nid": nid}
                ).fetchall()
            )
            if outlines:
                lines.append(f"\n【大纲】({len(outlines)}个节点)")
                node_type_label = {"volume": "卷", "chapter": "章", "scene": "节"}
                for o in outlines:
                    prefix = node_type_label.get(o.node_type, o.node_type)
                    parts = [f"  [{prefix}] {o.title}"]
                    if o.summary:
                        parts.append(f"\n        {o.summary}")
                    if o.character_id:
                        char_row = await conn.run_sync(
                            lambda c2: c2.execute(
                                text("SELECT name FROM characters WHERE id = :cid"), {"cid": o.character_id}
                            ).fetchone()
                        )
                        if char_row:
                            parts.append(f"  角色: {char_row[0]}")
                    if o.setting_id:
                        set_row = await conn.run_sync(
                            lambda c2: c2.execute(
                                text("SELECT name FROM settings WHERE id = :sid"), {"sid": o.setting_id}
                            ).fetchone()
                        )
                        if set_row:
                            parts.append(f"  场景: {set_row[0]}")
                    lines.append("".join(parts))

            # Chapters
            chapters = await conn.run_sync(
                lambda c: c.execute(
                    text("SELECT * FROM chapters WHERE novel_id = :nid ORDER BY chapter_number"), {"nid": nid}
                ).fetchall()
            )
            if chapters:
                lines.append(f"\n【章节】({len(chapters)}章)")
                total_words = 0
                for ch in chapters:
                    status = STATUS_LABELS.get(str(ch.status), str(ch.status))
                    total_words += ch.word_count or 0
                    lines.append(f"\n  --- 第{ch.chapter_number}章：{ch.title}（{status}）---")
                    if ch.chapter_prompt:
                        lines.append(f"  创作重点：\n{ch.chapter_prompt}")
                    if ch.summary:
                        lines.append(f"  摘要：{ch.summary}")
                    lines.append(f"  字数：{ch.word_count or 0:,}")
                    content = (ch.content or "").replace("<p>", "").replace("</p>", "\n").replace("<br>", "\n")
                    if content:
                        import re
                        content = re.sub(r"<[^>]+>", "", content)
                        lines.append(f"\n{content.strip()}\n")
                lines.append(f"\n  全书总字数：{total_words:,}")

    result = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"导出完成 → {output_path}")
    print(f"共 {len(result):,} 字符")


LABELS_PROFILE = {
    "age": "年龄", "appearance": "外貌", "personality": "性格",
    "background": "背景", "speech_style": "说话风格",
}


def safe_json(v):
    """JSON columns come back as strings with raw SQL on SQLite."""
    if v is None:
        return {}
    if isinstance(v, str):
        try:
            import json
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return v
    return v


def safe_json_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        try:
            import json
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return []
    return v if isinstance(v, list) else []

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "makenovel_export.txt"
    asyncio.run(export(out))
