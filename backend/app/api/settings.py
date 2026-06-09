import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Setting, Novel
from app.schemas.setting import SettingCreate, SettingUpdate, SettingOut

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/novel/{novel_id}", response_model=list[SettingOut])
async def list_settings(novel_id: int, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    settings = (await db.execute(
        select(Setting).where(Setting.novel_id == novel_id)
    )).scalars().all()
    return [SettingOut.model_validate(s) for s in settings]


@router.post("", response_model=SettingOut)
async def create_setting(data: SettingCreate, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, data.novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    setting = Setting(**data.model_dump())
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return SettingOut.model_validate(setting)


@router.put("/{setting_id}", response_model=SettingOut)
async def update_setting(setting_id: int, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    s = await db.get(Setting, setting_id)
    if not s:
        raise HTTPException(status_code=404, detail="场景不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(s, key, val)
    await db.commit()
    await db.refresh(s)
    return SettingOut.model_validate(s)


@router.get("/search")
async def search_settings(novel_id: int = Query(...), q: str = Query(""), db: AsyncSession = Depends(get_db)):
    query = select(Setting).where(Setting.novel_id == novel_id)
    if q:
        query = query.where(Setting.name.icontains(q))
    query = query.limit(20)
    results = (await db.execute(query)).scalars().all()
    return [{"id": s.id, "name": s.name} for s in results]


@router.delete("/{setting_id}")
async def delete_setting(setting_id: int, db: AsyncSession = Depends(get_db)):
    s = await db.get(Setting, setting_id)
    if not s:
        raise HTTPException(status_code=404, detail="场景不存在")
    await db.delete(s)
    await db.commit()
    return {"ok": True}
