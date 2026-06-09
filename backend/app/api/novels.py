from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Novel, Chapter
from app.schemas.novel import NovelCreate, NovelUpdate, NovelOut, NovelListItem

router = APIRouter(prefix="/api/novels", tags=["novels"])


@router.get("", response_model=list[NovelListItem])
async def list_novels(db: AsyncSession = Depends(get_db)):
    novels = (await db.execute(select(Novel).order_by(Novel.updated_at.desc()))).scalars().all()
    result = []
    for n in novels:
        count = (await db.execute(
            select(func.count(Chapter.id)).where(Chapter.novel_id == n.id)
        )).scalar()
        words = (await db.execute(
            select(func.sum(Chapter.word_count)).where(Chapter.novel_id == n.id)
        )).scalar() or 0
        result.append(NovelListItem(
            id=n.id, title=n.title, description=n.description, genre=n.genre,
            chapter_count=count, total_word_count=words,
            created_at=n.created_at, updated_at=n.updated_at,
        ))
    return result


@router.post("", response_model=NovelOut)
async def create_novel(data: NovelCreate, db: AsyncSession = Depends(get_db)):
    novel = Novel(**data.model_dump())
    db.add(novel)
    await db.commit()
    await db.refresh(novel)
    return NovelOut(id=novel.id, title=novel.title, description=novel.description,
                    genre=novel.genre, style_notes=novel.style_notes, word_count_goal=novel.word_count_goal,
                    chapter_count=0, total_word_count=0,
                    created_at=novel.created_at, updated_at=novel.updated_at)


@router.get("/{novel_id}", response_model=NovelOut)
async def get_novel(novel_id: int, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    count = (await db.execute(
        select(func.count(Chapter.id)).where(Chapter.novel_id == novel_id)
    )).scalar()
    words = (await db.execute(
        select(func.sum(Chapter.word_count)).where(Chapter.novel_id == novel_id)
    )).scalar() or 0
    return NovelOut(id=novel.id, title=novel.title, description=novel.description,
                    genre=novel.genre, style_notes=novel.style_notes, word_count_goal=novel.word_count_goal,
                    chapter_count=count, total_word_count=words,
                    created_at=novel.created_at, updated_at=novel.updated_at)


@router.put("/{novel_id}", response_model=NovelOut)
async def update_novel(novel_id: int, data: NovelUpdate, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(novel, key, val)
    await db.commit()
    await db.refresh(novel)
    count = (await db.execute(
        select(func.count(Chapter.id)).where(Chapter.novel_id == novel_id)
    )).scalar()
    words = (await db.execute(
        select(func.sum(Chapter.word_count)).where(Chapter.novel_id == novel_id)
    )).scalar() or 0
    return NovelOut(id=novel.id, title=novel.title, description=novel.description,
                    genre=novel.genre, style_notes=novel.style_notes, word_count_goal=novel.word_count_goal,
                    chapter_count=count, total_word_count=words,
                    created_at=novel.created_at, updated_at=novel.updated_at)


@router.delete("/{novel_id}")
async def delete_novel(novel_id: int, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    await db.delete(novel)
    await db.commit()
    return {"ok": True}
