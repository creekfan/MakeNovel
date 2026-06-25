from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/snapshots", tags=["snapshots"])


class SnapshotIn(BaseModel):
    id: str
    source_type: str = "free"
    source_id: Optional[str] = None
    name: str = ""
    label: str = ""
    category: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    create_master: bool = False


def _build_character_master(snap: SnapshotIn) -> dict:
    f = snap.fields
    return {
        "id": snap.source_id,
        "name": snap.name,
        "role": f.get("role", "supporting"),
        "appearance": f.get("appearance", ""),
        "personality": f.get("personality", ""),
        "background": f.get("background", ""),
        "abilities": f.get("abilities"),
        "speech_style": f.get("speech_style"),
        "arc": f.get("arc"),
        "current_state": f.get("current_state"),
        "relationships": f.get("relationships", []),
    }


def _build_setting_master(snap: SnapshotIn) -> dict:
    f = snap.fields
    return {
        "id": snap.source_id,
        "name": snap.name,
        "category": f.get("category", "rule"),
        "description": f.get("description", ""),
        "notable_features": f.get("notable_features", []),
    }


def _sync_master(novel_id: str, snap: SnapshotIn):
    """Create a new master card on first creation only (仅新建时同步)."""
    if snap.source_type == "character":
        if not snap.source_id:
            snap.source_id = "char-" + snap.id
        chars = storage.get_characters(novel_id)
        if not any(c.get("id") == snap.source_id for c in chars):
            chars.append(_build_character_master(snap))
            storage.save_characters(novel_id, chars)
    elif snap.source_type == "setting":
        if not snap.source_id:
            snap.source_id = "ws-" + snap.id
        settings = storage.get_world_settings(novel_id)
        if not any(s.get("id") == snap.source_id for s in settings):
            settings.append(_build_setting_master(snap))
            storage.save_world_settings(novel_id, settings)


@router.get("")
def list_snapshots(novel_id: str):
    return storage.get_snapshots(novel_id)


@router.get("/{snapshot_id}/placements")
def get_placements(novel_id: str, snapshot_id: str):
    result = []
    for canvas in storage.iter_canvases(novel_id):
        node_id = canvas.get("node_id", "")
        for placement in canvas.get("nodes", []):
            if placement.get("entity_type") == "snapshot" and placement.get("entity_id") == snapshot_id:
                result.append({
                    "node_id": node_id,
                    "node_title": storage.find_node_title(novel_id, node_id),
                    "placement_id": placement.get("placement_id", ""),
                    "x": placement.get("x", 0),
                    "y": placement.get("y", 0),
                })
    return result


@router.get("/{snapshot_id}")
def get_snapshot(novel_id: str, snapshot_id: str):
    for s in storage.get_snapshots(novel_id):
        if s.get("id") == snapshot_id:
            return s
    raise HTTPException(404, "Snapshot not found")


@router.post("")
def add_snapshot(novel_id: str, body: SnapshotIn):
    if not body.created_at:
        body.created_at = datetime.now().isoformat()
    if body.create_master:
        _sync_master(novel_id, body)
    snapshots = storage.get_snapshots(novel_id)
    snapshots.append(body.model_dump(exclude={"create_master"}))
    storage.save_snapshots(novel_id, snapshots)
    return {"ok": True, "id": body.id, "source_id": body.source_id}


@router.put("/{snapshot_id}")
def update_snapshot(novel_id: str, snapshot_id: str, body: SnapshotIn):
    snapshots = storage.get_snapshots(novel_id)
    found = False
    for i, s in enumerate(snapshots):
        if s.get("id") == snapshot_id:
            data = body.model_dump(exclude={"create_master"})
            data["id"] = snapshot_id
            data["created_at"] = s.get("created_at") or body.created_at
            snapshots[i] = data
            found = True
            break
    if not found:
        raise HTTPException(404, "Snapshot not found")
    storage.save_snapshots(novel_id, snapshots)
    return {"ok": True}


@router.delete("/{snapshot_id}")
def delete_snapshot(novel_id: str, snapshot_id: str):
    snapshots = [s for s in storage.get_snapshots(novel_id) if s.get("id") != snapshot_id]
    storage.save_snapshots(novel_id, snapshots)
    return {"ok": True}
