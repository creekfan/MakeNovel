from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/canvas", tags=["canvas"])


class CanvasPlacement(BaseModel):
    placement_id: str
    entity_type: str
    entity_id: str
    x: float = 0.0
    y: float = 0.0


class CanvasEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str = "note_to_event"
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None


class CanvasData(BaseModel):
    node_id: str
    nodes: list[CanvasPlacement] = []
    edges: list[CanvasEdge] = []
    viewport: Optional[dict[str, Any]] = None


@router.get("/{node_id}")
def get_canvas(novel_id: str, node_id: str):
    return storage.get_canvas(novel_id, node_id)


@router.put("/{node_id}")
def save_canvas(novel_id: str, node_id: str, body: CanvasData):
    data = body.model_dump()
    data["node_id"] = node_id
    storage.save_canvas(novel_id, node_id, data)
    return {"ok": True}
