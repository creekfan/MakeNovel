from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import novels, outlines, characters, world, agent, style, snapshots, events, canvas

app = FastAPI(title="NovelAgent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(novels.router)
app.include_router(outlines.router)
app.include_router(characters.router)
app.include_router(world.router)
app.include_router(agent.router)
app.include_router(style.router)
app.include_router(snapshots.router)
app.include_router(events.router)
app.include_router(canvas.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
