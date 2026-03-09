import os

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .auth import require_api_key
from .database import init_db
from . import models  # noqa: F401 — registers Decision + Memory with Base.metadata
from .routers import decisions, memory, search, ask, patterns, contradictions, timeline, brain, trialprep, witnesses, export, checklist, complaints, vault, crossexam, costs
from .services import embed_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _create_vector_index()
    embed_service.load_model()
    yield


async def _create_vector_index() -> None:
    """Create HNSW index on chunks.embedding if it doesn't exist yet."""
    from .database import engine
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
            "ON chunks USING hnsw (embedding vector_cosine_ops)"
        ))


app = FastAPI(
    title="The MCFD Files",
    description="Document analysis and search API",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_auth = [Depends(require_api_key)]

app.include_router(decisions.router,      dependencies=_auth)
app.include_router(memory.router,         dependencies=_auth)
app.include_router(search.router,         dependencies=_auth)
app.include_router(ask.router,            dependencies=_auth)
app.include_router(patterns.router,       dependencies=_auth)
app.include_router(contradictions.router, dependencies=_auth)
app.include_router(timeline.router,       dependencies=_auth)
app.include_router(brain.router,          dependencies=_auth)
app.include_router(trialprep.router,      dependencies=_auth)
app.include_router(witnesses.router,      dependencies=_auth)
app.include_router(checklist.router,      dependencies=_auth)
app.include_router(complaints.router,     dependencies=_auth)
app.include_router(vault.router,          dependencies=_auth)
app.include_router(crossexam.router,      dependencies=_auth)
# Public — no auth:
app.include_router(export.router)   # mixed — per-endpoint auth on trial-report routes
app.include_router(costs.router)    # fully public


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "mcfd-backend"}


@app.get("/")
async def root():
    return {"message": "The MCFD Files API"}
