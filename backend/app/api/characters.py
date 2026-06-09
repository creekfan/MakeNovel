from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Character, CharacterRelationship, Novel
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterOut, RelationshipCreate, RelationshipOut

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.get("/novel/{novel_id}", response_model=list[CharacterOut])
async def list_characters(novel_id: int, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    characters = (await db.execute(
        select(Character)
        .where(Character.novel_id == novel_id)
        .options(selectinload(Character.relationships_as_source),
                 selectinload(Character.relationships_as_target))
    )).unique().scalars().all()

    result = []
    for c in characters:
        rels = []
        for r in c.relationships_as_source:
            target = (await db.execute(
                select(Character.name).where(Character.id == r.target_id)
            )).scalar()
            rels.append(RelationshipOut(
                id=r.id, source_id=r.source_id, target_id=r.target_id,
                target_name=target or "", relation_type=r.relation_type,
                description=r.description,
            ))
        for r in c.relationships_as_target:
            source = (await db.execute(
                select(Character.name).where(Character.id == r.source_id)
            )).scalar()
            rels.append(RelationshipOut(
                id=r.id, source_id=r.source_id, target_id=r.target_id,
                target_name=source or "", relation_type=r.relation_type,
                description=r.description,
            ))
        result.append(CharacterOut(
            id=c.id, novel_id=c.novel_id, name=c.name, aliases=c.aliases or [],
            role=c.role.value if c.role else "supporting", profile=c.profile or {},
            arc=c.arc or "", avatar_color=c.avatar_color, relationships=rels,
            created_at=c.created_at, updated_at=c.updated_at,
        ))
    return result


@router.post("", response_model=CharacterOut)
async def create_character(data: CharacterCreate, db: AsyncSession = Depends(get_db)):
    novel = await db.get(Novel, data.novel_id)
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")
    character = Character(**data.model_dump())
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return CharacterOut(
        id=character.id, novel_id=character.novel_id, name=character.name,
        aliases=character.aliases or [], role=character.role.value if character.role else "supporting",
        profile=character.profile or {}, arc=character.arc or "",
        avatar_color=character.avatar_color, relationships=[],
        created_at=character.created_at, updated_at=character.updated_at,
    )


@router.get("/{character_id}", response_model=CharacterOut)
async def get_character(character_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Character, character_id)
    if not c:
        raise HTTPException(status_code=404, detail="角色不存在")
    return CharacterOut(
        id=c.id, novel_id=c.novel_id, name=c.name, aliases=c.aliases or [],
        role=c.role.value if c.role else "supporting", profile=c.profile or {},
        arc=c.arc or "", avatar_color=c.avatar_color, relationships=[],
        created_at=c.created_at, updated_at=c.updated_at,
    )


@router.put("/{character_id}", response_model=CharacterOut)
async def update_character(character_id: int, data: CharacterUpdate, db: AsyncSession = Depends(get_db)):
    c = await db.get(Character, character_id)
    if not c:
        raise HTTPException(status_code=404, detail="角色不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(c, key, val)
    await db.commit()
    await db.refresh(c)
    return CharacterOut(
        id=c.id, novel_id=c.novel_id, name=c.name, aliases=c.aliases or [],
        role=c.role.value if c.role else "supporting", profile=c.profile or {},
        arc=c.arc or "", avatar_color=c.avatar_color, relationships=[],
        created_at=c.created_at, updated_at=c.updated_at,
    )


@router.delete("/{character_id}")
async def delete_character(character_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Character, character_id)
    if not c:
        raise HTTPException(status_code=404, detail="角色不存在")
    await db.delete(c)
    await db.commit()
    return {"ok": True}


@router.post("/relationships", response_model=RelationshipOut)
async def create_relationship(data: RelationshipCreate, db: AsyncSession = Depends(get_db)):
    rel = CharacterRelationship(**data.model_dump())
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return RelationshipOut(
        id=rel.id, source_id=rel.source_id, target_id=rel.target_id,
        target_name="", relation_type=rel.relation_type, description=rel.description,
    )


@router.get("/search/{novel_id}")
async def search_characters(novel_id: int, q: str = "", db: AsyncSession = Depends(get_db)):
    query = select(Character).where(Character.novel_id == novel_id)
    if q:
        query = query.where(Character.name.icontains(q))
    query = query.limit(20)
    results = (await db.execute(query)).scalars().all()
    return [{"id": c.id, "name": c.name} for c in results]


@router.delete("/relationships/{rel_id}")
async def delete_relationship(rel_id: int, db: AsyncSession = Depends(get_db)):
    rel = await db.get(CharacterRelationship, rel_id)
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    await db.delete(rel)
    await db.commit()
    return {"ok": True}
