from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.api import (
    novels_router, chapters_router, characters_router,
    settings_router, outlines_router, ai_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="MakeNovel API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(novels_router)
app.include_router(chapters_router)
app.include_router(characters_router)
app.include_router(settings_router)
app.include_router(outlines_router)
app.include_router(ai_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
