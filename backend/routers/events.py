from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/events", tags=["events"])


class EventIn(BaseModel):
    id: str
    title: str
    description: str = ""
    time_label: Optional[str] = None
    created_at: Optional[str] = None


@router.get("")
def list_events(novel_id: str):
    return storage.get_events(novel_id)


@router.get("/{event_id}")
def get_event(novel_id: str, event_id: str):
    for e in storage.get_events(novel_id):
        if e.get("id") == event_id:
            return e
    raise HTTPException(404, "Event not found")


@router.post("")
def add_event(novel_id: str, body: EventIn):
    if not body.created_at:
        body.created_at = datetime.now().isoformat()
    events = storage.get_events(novel_id)
    events.append(body.model_dump())
    storage.save_events(novel_id, events)
    return {"ok": True, "id": body.id}


@router.put("/{event_id}")
def update_event(novel_id: str, event_id: str, body: EventIn):
    events = storage.get_events(novel_id)
    found = False
    for i, e in enumerate(events):
        if e.get("id") == event_id:
            data = body.model_dump()
            data["id"] = event_id
            data["created_at"] = e.get("created_at") or body.created_at
            events[i] = data
            found = True
            break
    if not found:
        raise HTTPException(404, "Event not found")
    storage.save_events(novel_id, events)
    return {"ok": True}


@router.delete("/{event_id}")
def delete_event(novel_id: str, event_id: str):
    events = [e for e in storage.get_events(novel_id) if e.get("id") != event_id]
    storage.save_events(novel_id, events)
    return {"ok": True}
