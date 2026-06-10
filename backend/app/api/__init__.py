from app.api.novels import router as novels_router
from app.api.characters import router as characters_router
from app.api.settings import router as settings_router
from app.api.outlines import router as outlines_router
from app.api.ai import router as ai_router

__all__ = [
    "novels_router", "characters_router",
    "settings_router", "outlines_router", "ai_router",
]
