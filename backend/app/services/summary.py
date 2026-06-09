from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Chapter, Character


async def generate_summary_for_chapter(db: AsyncSession, chapter: Chapter) -> str:
    """Placeholder: returns truncated first 300 chars.
    Full implementation would call LLM to generate proper summary.
    """
    text = chapter.content.strip()
    if not text:
        return ""
    if len(text) <= 400:
        return text
    return text[:400] + "..."
