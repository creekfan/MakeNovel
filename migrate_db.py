import sqlite3
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path("makenovel.db")
DATA_DIR = Path("backend/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>\s*<p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()
    return text


def parse_json_field(val) -> list | dict:
    if not val:
        return []
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


def build_outline_tree(nodes, novel_id, novel_title):
    by_id = {}
    roots = []
    for n in nodes:
        if n["novel_id"] != novel_id:
            continue
        node_type = n["node_type"]
        if node_type == "scene":
            node_type = "section"
        item = {
            "id": f"node-{n['id']}",
            "title": n["title"] or "",
            "node_type": node_type,
            "summary": n["summary"] or "",
            "status": (n["status"] or "planned").lower(),
            "content": None,
            "chapter_prompt": n["chapter_prompt"] or None,
            "children": [],
            "sort_order": float(n["sort_order"] or 0),
        }
        by_id[n["id"]] = (item, n["parent_id"])

    for db_id, (item, parent_id) in by_id.items():
        if parent_id is None or parent_id not in by_id:
            roots.append(item)
        else:
            by_id[parent_id][0]["children"].append(item)

    for _, (item, _) in by_id.items():
        item["children"].sort(key=lambda x: x["sort_order"])

    roots.sort(key=lambda x: x["sort_order"])

    return {
        "novel_id": str(novel_id),
        "novel_title": novel_title,
        "volumes": roots,
    }


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM novels")
    novels = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM outline_nodes ORDER BY novel_id, parent_id, sort_order")
    all_nodes = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM characters")
    all_chars = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM settings")
    all_settings = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM character_relationships")
    all_rels = [dict(r) for r in c.fetchall()]

    conn.close()

    for novel in novels:
        novel_id = str(novel["id"])
        novel_title = novel["title"]
        novel_dir = DATA_DIR / novel_id
        novel_dir.mkdir(exist_ok=True)

        meta = {"id": novel_id, "name": novel_title}
        (novel_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[Novel] {novel_id}: {novel_title}")

        outline = build_outline_tree(all_nodes, novel["id"], novel_title)
        (novel_dir / "outline.json").write_text(
            json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  [Outline] {len(outline['volumes'])} volumes")

        sections_dir = novel_dir / "sections"
        sections_dir.mkdir(exist_ok=True)
        section_count = 0
        for node in all_nodes:
            if node["novel_id"] != novel["id"]:
                continue
            raw_content = node.get("content") or ""
            text = strip_html(raw_content)
            if text:
                section_id = f"node-{node['id']}"
                (sections_dir / f"{section_id}.txt").write_text(text, encoding="utf-8")
                section_count += 1
        print(f"  [Sections] {section_count} files saved")

        chars = []
        rels_by_char = {}
        for rel in all_rels:
            rels_by_char.setdefault(rel["source_id"], []).append(rel)
            if rel["source_id"] != rel["target_id"]:
                rels_by_char.setdefault(rel["target_id"], []).append(rel)

        for ch in all_chars:
            if ch["novel_id"] != novel["id"]:
                continue
            profile = parse_json_field(ch.get("profile"))
            if isinstance(profile, str):
                try:
                    profile = json.loads(profile)
                except:
                    profile = {}
            if not isinstance(profile, dict):
                profile = {}

            role_map = {
                "PROTAGONIST": "protagonist",
                "ANTAGONIST": "antagonist",
                "SUPPORTING": "supporting",
                "MINOR": "minor",
            }
            role = role_map.get(ch.get("role", ""), "supporting")

            relationships = []
            for rel in rels_by_char.get(ch["id"], []):
                relationships.append({
                    "source_id": f"char-{rel['source_id']}",
                    "target_id": f"char-{rel['target_id']}",
                    "relation_type": rel.get("relation_type", ""),
                    "description": rel.get("description", ""),
                })

            char_out = {
                "id": f"char-{ch['id']}",
                "name": ch["name"],
                "role": role,
                "appearance": profile.get("appearance", ""),
                "personality": profile.get("personality", ""),
                "background": profile.get("background", ""),
                "abilities": profile.get("abilities"),
                "speech_style": profile.get("speech_style"),
                "arc": ch.get("arc") or None,
                "current_state": None,
                "relationships": relationships,
            }
            chars.append(char_out)

        (novel_dir / "characters.json").write_text(
            json.dumps(chars, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  [Characters] {len(chars)}")

        world = []
        for s in all_settings:
            if s["novel_id"] != novel["id"]:
                continue
            features = parse_json_field(s.get("notable_features"))
            if not isinstance(features, list):
                features = []

            cat = s.get("category", "rule")
            valid_cats = ["location", "faction", "rule", "race", "item", "profession", "history"]
            if cat not in valid_cats:
                cat = "rule"

            ws = {
                "id": f"ws-{s['id']}",
                "name": s["name"],
                "category": cat,
                "description": s.get("description", ""),
                "notable_features": features,
            }
            world.append(ws)

        (novel_dir / "world_settings.json").write_text(
            json.dumps(world, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  [World] {len(world)}")

        (novel_dir / "summaries.json").write_text("[]", encoding="utf-8")

    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
