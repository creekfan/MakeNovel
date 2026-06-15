from fastapi import APIRouter
from pydantic import BaseModel

from .. import storage

router = APIRouter(prefix="/api/novels/{novel_id}/world", tags=["world"])


class WorldSettingIn(BaseModel):
    id: str
    name: str
    category: str = "rule"
    description: str = ""
    notable_features: list[str] = []


@router.get("")
def get_world_settings(novel_id: str):
    return storage.get_world_settings(novel_id)


@router.put("")
def save_world_settings(novel_id: str, body: list[WorldSettingIn]):
    storage.save_world_settings(novel_id, [w.model_dump() for w in body])
    return {"ok": True}


@router.post("")
def add_world_setting(novel_id: str, body: WorldSettingIn):
    settings = storage.get_world_settings(novel_id)
    settings.append(body.model_dump())
    storage.save_world_settings(novel_id, settings)
    return {"ok": True}


@router.delete("/{setting_id}")
def delete_world_setting(novel_id: str, setting_id: str):
    settings = storage.get_world_settings(novel_id)
    settings = [s for s in settings if s.get("id") != setting_id]
    storage.save_world_settings(novel_id, settings)
    return {"ok": True}
