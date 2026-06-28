import json
import os
from pathlib import Path
from typing import Any, List, Optional

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _novel_dir(novel_id: str) -> Path:
    return DATA_DIR / novel_id


def _ensure_novel_dir(novel_id: str) -> Path:
    d = DATA_DIR / novel_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_novels() -> List[dict]:
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


def get_novel(novel_id: str) -> Optional[dict]:
    meta_file = _novel_dir(novel_id) / "meta.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text(encoding="utf-8"))
    return None


def save_novel(novel_id: str, meta: dict):
    meta_file = _ensure_novel_dir(novel_id) / "meta.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_novel(novel_id: str):
    import shutil
    d = DATA_DIR / novel_id
    if d.exists():
        shutil.rmtree(d)


def get_outline(novel_id: str) -> Optional[dict]:
    f = _novel_dir(novel_id) / "outline.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def save_outline(novel_id: str, data: dict):
    f = _ensure_novel_dir(novel_id) / "outline.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_characters(novel_id: str) -> list:
    f = _novel_dir(novel_id) / "characters.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def save_characters(novel_id: str, data: list):
    f = _ensure_novel_dir(novel_id) / "characters.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_world_settings(novel_id: str) -> list:
    f = _novel_dir(novel_id) / "world_settings.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def save_world_settings(novel_id: str, data: list):
    f = _ensure_novel_dir(novel_id) / "world_settings.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_summaries(novel_id: str) -> list:
    f = _novel_dir(novel_id) / "summaries.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def save_summaries(novel_id: str, data: list):
    f = _ensure_novel_dir(novel_id) / "summaries.json"
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


def get_section_content(novel_id: str, section_id: str) -> Optional[str]:
    f = _novel_dir(novel_id) / "sections" / f"{section_id}.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return None


def save_section_content(novel_id: str, section_id: str, content: str):
    d = _ensure_novel_dir(novel_id) / "sections"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{section_id}.txt"
    f.write_text(content, encoding="utf-8")


def _styles_dir(novel_id: str) -> Path:
    d = _ensure_novel_dir(novel_id) / "styles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_styles(novel_id: str) -> list:
    f = _styles_dir(novel_id) / "list.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def get_style(novel_id: str, style_id: str) -> Optional[dict]:
    styles = list_styles(novel_id)
    for s in styles:
        if s.get("id") == style_id:
            content_f = _styles_dir(novel_id) / f"{style_id}.md"
            s["content"] = content_f.read_text(encoding="utf-8") if content_f.exists() else ""
            return s
    return None


def save_style(novel_id: str, style_id: str, name: str, content: str):
    content_f = _styles_dir(novel_id) / f"{style_id}.md"
    content_f.write_text(content, encoding="utf-8")
    styles = list_styles(novel_id)
    updated = False
    for s in styles:
        if s.get("id") == style_id:
            s["name"] = name
            updated = True
            break
    if not updated:
        from datetime import datetime
        styles.append({"id": style_id, "name": name, "created_at": datetime.now().isoformat()})
    list_f = _styles_dir(novel_id) / "list.json"
    list_f.write_text(json.dumps(styles, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_style(novel_id: str, style_id: str):
    content_f = _styles_dir(novel_id) / f"{style_id}.md"
    if content_f.exists():
        content_f.unlink()
    styles = [s for s in list_styles(novel_id) if s.get("id") != style_id]
    list_f = _styles_dir(novel_id) / "list.json"
    list_f.write_text(json.dumps(styles, ensure_ascii=False, indent=2), encoding="utf-8")


def get_snapshots(novel_id: str) -> list:
    f = _novel_dir(novel_id) / "snapshots.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def save_snapshots(novel_id: str, data: list):
    f = _ensure_novel_dir(novel_id) / "snapshots.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_events(novel_id: str) -> list:
    f = _novel_dir(novel_id) / "events.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return []


def save_events(novel_id: str, data: list):
    f = _ensure_novel_dir(novel_id) / "events.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _canvas_dir(novel_id: str) -> Path:
    d = _ensure_novel_dir(novel_id) / "canvas"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_canvas(novel_id: str, node_id: str) -> dict:
    f = _canvas_dir(novel_id) / f"{node_id}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"node_id": node_id, "nodes": [], "edges": [], "viewport": None}


def save_canvas(novel_id: str, node_id: str, data: dict):
    f = _canvas_dir(novel_id) / f"{node_id}.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def iter_canvases(novel_id: str) -> list:
    d = _novel_dir(novel_id) / "canvas"
    result = []
    if not d.exists():
        return result
    for p in d.iterdir():
        if p.is_file() and p.suffix == ".json":
            try:
                result.append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    return result


def find_node_title(novel_id: str, node_id: str) -> str:
    outline = get_outline(novel_id)
    if not outline:
        return ""

    def _search(nodes: list) -> Optional[str]:
        for n in nodes:
            if n.get("id") == node_id:
                return n.get("title", "")
            r = _search(n.get("children", []))
            if r is not None:
                return r
        return None

    return _search(outline.get("volumes", [])) or ""


def _logs_dir(novel_id: str) -> Path:
    d = _ensure_novel_dir(novel_id) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_agent_log(novel_id: str, run_id: str, data: dict):
    f = _logs_dir(novel_id) / f"{run_id}.json"
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_agent_log(novel_id: str, run_id: str) -> Optional[dict]:
    f = _logs_dir(novel_id) / f"{run_id}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def list_agent_logs(novel_id: str) -> List[dict]:
    d = _novel_dir(novel_id) / "logs"
    result: List[dict] = []
    if not d.exists():
        return result
    for p in d.iterdir():
        if p.is_file() and p.suffix == ".json":
            try:
                log = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            result.append({
                "run_id": log.get("run_id", p.stem),
                "section_id": log.get("section_id", ""),
                "section_title": log.get("section_title", ""),
                "instruction": log.get("instruction", ""),
                "model": log.get("model", ""),
                "status": log.get("status", ""),
                "started_at": log.get("started_at", ""),
                "finished_at": log.get("finished_at", ""),
                "event_count": len(log.get("events", [])),
                "final_len": len(log.get("final_content", "") or ""),
            })
    result.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return result


def delete_agent_log(novel_id: str, run_id: str):
    f = _novel_dir(novel_id) / "logs" / f"{run_id}.json"
    if f.exists():
        f.unlink()


def delete_section_summaries(novel_id: str, section_ids: set):
    summaries = get_summaries(novel_id)
    if not summaries:
        return
    filtered = [s for s in summaries if s.get("section_id") not in section_ids]
    if len(filtered) != len(summaries):
        save_summaries(novel_id, filtered)


def delete_section_files(novel_id: str, section_ids: set):
    for sid in section_ids:
        f = _novel_dir(novel_id) / "sections" / f"{sid}.txt"
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass


def delete_canvas_nodes(novel_id: str, node_ids: set):
    d = _novel_dir(novel_id) / "canvas"
    if not d.exists():
        return
    for nid in node_ids:
        f = d / f"{nid}.json"
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass
