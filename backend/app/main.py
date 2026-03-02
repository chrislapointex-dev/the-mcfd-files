from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import init_db
from . import models  # noqa: F401 — registers Decision + Memory with Base.metadata
from .routers import decisions, memory, search, ask
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
        await conn.execute(text("COMMIT"))


app = FastAPI(
    title="The MCFD Files",
    description="Document analysis and search API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(decisions.router)
app.include_router(memory.router)
app.include_router(search.router)
app.include_router(ask.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "mcfd-backend"}


@app.get("/")
async def root():
    return {"message": "The MCFD Files API"}
