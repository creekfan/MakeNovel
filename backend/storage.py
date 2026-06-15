import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _novel_dir(novel_id: str) -> Path:
    d = DATA_DIR / novel_id
    d.mkdir(exist_ok=True)
    return d


def list_novels() -> list[dict]:
    result = []
    if not DATA_DIR.exists():
        return result
    for p in DATA_DIR.iterdir():
        if p.is_dir():
            meta_file = p / "meta.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                result.append(meta)
    return result


def get_novel(novel_id: str) -> dict | None:
    meta_file = _novel_dir(novel_id) / "meta.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text(encoding="utf-8"))
    return None


def save_novel(novel_id: str, meta: dict):
    meta_file = _novel_dir(novel_id) / "meta.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_novel(novel_id: str):
    import shutil
    d = DATA_DIR / novel_id
    if d.exists():
        shutil.rmtree(d)


def get_outline(novel_id: str) -> dict | None:
    f = _novel_dir(novel_id) / "outline.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def save_outline(novel_id: str, data: dict):
    f = _novel_dir(novel_id) / "outline.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_characters(novel_id: str) -> list:
    f = _novel_dir(novel_id) / "characters.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def save_characters(novel_id: str, data: list):
    f = _novel_dir(novel_id) / "characters.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_world_settings(novel_id: str) -> list:
    f = _novel_dir(novel_id) / "world_settings.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def save_world_settings(novel_id: str, data: list):
    f = _novel_dir(novel_id) / "world_settings.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_summaries(novel_id: str) -> list:
    f = _novel_dir(novel_id) / "summaries.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def save_summaries(novel_id: str, data: list):
    f = _novel_dir(novel_id) / "summaries.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_outline_node(novel_id: str, node_id: str, updates: dict) -> bool:
    outline = get_outline(novel_id)
    if not outline:
        return False

    def _update(nodes: list) -> bool:
        for node in nodes:
            if node.get("id") == node_id:
                node.update(updates)
                return True
            if _update(node.get("children", [])):
                return True
        return False

    found = _update(outline.get("volumes", []))
    if found:
        save_outline(novel_id, outline)
    return found


def get_section_content(novel_id: str, section_id: str) -> str | None:
    f = _novel_dir(novel_id) / "sections" / f"{section_id}.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return None


def save_section_content(novel_id: str, section_id: str, content: str):
    d = _novel_dir(novel_id) / "sections"
    d.mkdir(exist_ok=True)
    f = d / f"{section_id}.txt"
    f.write_text(content, encoding="utf-8")
