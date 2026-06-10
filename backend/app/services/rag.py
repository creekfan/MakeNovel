"""RAG: embed section content and retrieve relevant context via vector similarity."""
import json
import math
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import OutlineNode


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


async def embed_text(text: str, provider: str, model: str, api_key: str) -> list[float]:
    """Call embedding API via litellm. Returns a float vector."""
    import litellm
    model_name = f"{provider}/{model}" if provider not in ("openai", "anthropic") else model
    try:
        resp = await litellm.aembedding(
            model=model_name,
            input=[text],
            api_key=api_key,
        )
        return resp.data[0]["embedding"]
    except Exception:
        # Fallback: try direct openai format
        resp = await litellm.aembedding(
            model="openai/" + model if provider != "openai" else model,
            input=[text],
            api_key=api_key,
        )
        return resp.data[0]["embedding"]


async def embed_section(db: AsyncSession, section_id: int, provider: str = "", model: str = "", api_key: str = "") -> bool:
    """Embed a section's content and store it."""
    section = await db.get(OutlineNode, section_id)
    if not section or not section.content:
        return False

    text_to_embed = f"{section.title}\n{section.summary or ''}\n{section.content}"
    if len(text_to_embed) < 10:
        return False

    try:
        vec = await embed_text(text_to_embed, provider, model, api_key)
        section.embedding = vec
        await db.commit()
        return True
    except Exception:
        return False


async def search_similar(
    db: AsyncSession,
    novel_id: int,
    exclude_section_id: int | None = None,
    top_k: int = 5,
) -> list[OutlineNode]:
    """Return top-k sections with known embeddings for the given novel.
    Sorted by a simple heuristic: returns sections with embeddings that exist.
    For actual similarity search against a query, use search_by_query().
    """
    query = select(OutlineNode).where(
        OutlineNode.novel_id == novel_id,
        OutlineNode.node_type == 'scene',
        OutlineNode.embedding.isnot(None),
    )
    if exclude_section_id is not None:
        query = query.where(OutlineNode.id != exclude_section_id)
    query = query.limit(top_k * 3)
    result = (await db.execute(query)).scalars().all()
    return list(result)


async def search_by_query(
    db: AsyncSession,
    novel_id: int,
    query_text: str,
    provider: str,
    model: str,
    api_key: str,
    exclude_section_id: int | None = None,
    top_k: int = 5,
) -> list[OutlineNode]:
    """Embed query_text and find top-k most similar sections."""
    candidates = await search_similar(db, novel_id, exclude_section_id, top_k=10)
    if not candidates:
        return []

    try:
        query_vec = await embed_text(query_text, provider, model, api_key)
    except Exception:
        return candidates[:top_k]

    scored = []
    for sec in candidates:
        if sec.embedding:
            sim = cosine_similarity(query_vec, sec.embedding)
            scored.append((sim, sec))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:top_k]]
