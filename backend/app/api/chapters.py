from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Novel, Chapter
from app.schemas.chapter import ChapterCreate, ChapterUpdate, ChapterOut, ChapterListItem
from app.services.summary import generate_summary_for_chapter

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


@router.get("/novel/{novel_id}", response_model=list[ChapterListItem])
async def list_chapters(novel_id: int, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    chapters = (await db.execute(
        select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.chapter_number)
    )).scalars().all()
    return [ChapterListItem.model_validate(c) for c in chapters]


@router.post("", response_model=ChapterOut)
async def create_chapter(data: ChapterCreate, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, data.novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    chapter = Chapter(**data.model_dump())
    db.add(chapter)
    await db.commit()
    await db.refresh(chapter)
    return ChapterOut.model_validate(chapter)


@router.get("/{chapter_id}", response_model=ChapterOut)
async def get_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return ChapterOut.model_validate(chapter)


@router.put("/{chapter_id}", response_model=ChapterOut)
async def update_chapter(chapter_id: int, data: ChapterUpdate, db: AsyncSession = Depends(get_db)):
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(chapter, key, val)
    if data.content is not None:
        chapter.word_count = len(data.content)
        chapter.summary = await generate_summary_for_chapter(db, chapter)
    await db.commit()
    await db.refresh(chapter)
    return ChapterOut.model_validate(chapter)


@router.delete("/{chapter_id}")
async def delete_chapter(chapter_id: int, db: AsyncSession = Depends(get_db)):
    chapter = await db.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    await db.delete(chapter)
    await db.commit()
    return {"ok": True}
