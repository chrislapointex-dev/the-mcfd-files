import os
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import require_api_key
from .database import init_db, get_db
from . import models  # noqa: F401 — registers Decision + Memory with Base.metadata
from .models import Contradiction, CostEntry, TimelineEvent, CrossExamQuestion, ShareView
from .routers import decisions, memory, search, ask, patterns, contradictions, timeline, brain, trialprep, witnesses, export, checklist, complaints, vault, crossexam, costs, share, graph
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
app.include_router(graph.router,          dependencies=_auth)
app.include_router(checklist.router,      dependencies=_auth)
app.include_router(complaints.router,     dependencies=_auth)
app.include_router(vault.router,          dependencies=_auth)
app.include_router(crossexam.router,      dependencies=_auth)
# Public — no auth:
app.include_router(export.router)   # mixed — per-endpoint auth on trial-report routes
app.include_router(costs.router)    # fully public
app.include_router(share.router)    # fully public — view counter


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "mcfd-backend"}


@app.get("/")
async def root():
    return {"message": "The MCFD Files API"}


@app.get("/api/deploy-check")
async def deploy_check(db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timezone

    errors = []
    warnings = []

    # DB counts
    contra_count = (await db.execute(select(func.count()).select_from(Contradiction))).scalar_one()
    cost_count = (await db.execute(select(func.count()).select_from(CostEntry))).scalar_one()
    timeline_count = (await db.execute(select(func.count()).select_from(TimelineEvent))).scalar_one()
    crossexam_count = (await db.execute(select(func.count()).select_from(CrossExamQuestion))).scalar_one()
    views_count = (await db.execute(select(func.count()).select_from(ShareView))).scalar_one()
    db_ok = contra_count > 0 and cost_count > 0
    if not db_ok:
        errors.append("Database appears empty — no contradictions or cost entries found")

    # Auth check
    api_key_set = bool(os.getenv("MCFD_API_KEY", ""))
    if not api_key_set:
        warnings.append("MCFD_API_KEY not set — all protected routes are open (dev mode)")
    auth_mode = "production (key set)" if api_key_set else "dev (no key set)"

    # Vault check
    vault_path = Path(__file__).parent.parent / "data" / "vault" / "court-final.pdf"
    vault_ok = vault_path.exists()
    if not vault_ok:
        warnings.append(f"Vault file not found: {vault_path} — must be present on deployment host")

    # Cloudflare files check
    project_root = Path(__file__).parent.parent.parent
    cf_tunnel = project_root / "cloudflare" / "tunnel-config.yml"
    redirects = project_root / "frontend" / "public" / "_redirects"
    cf_files = {
        "cloudflare/tunnel-config.yml": cf_tunnel.exists(),
        "frontend/public/_redirects": redirects.exists(),
    }
    cf_ok = redirects.exists()

    ready = db_ok and len(errors) == 0

    return {
        "ready": ready,
        "checks": {
            "database": {
                "ok": db_ok,
                "contradictions": int(contra_count),
                "cost_entries": int(cost_count),
                "timeline_events": int(timeline_count),
                "witness_profiles": 6,
                "cross_exam_sets": int(crossexam_count),
                "share_views": int(views_count),
            },
            "auth": {
                "ok": True,
                "mode": auth_mode,
                "note": "Set MCFD_API_KEY env var before deploying" if not api_key_set else None,
            },
            "public_endpoints": {
                "ok": True,
                "endpoints": [
                    "/api/costs",
                    "/api/costs/scale",
                    "/api/export/media-package",
                    "/api/export/caryma-brief.pdf",
                    "/api/share/views",
                    "/api/share/strength",
                ],
            },
            "vault": {
                "ok": vault_ok,
                "file": "court-final.pdf",
                "path": str(vault_path),
                "note": "Vault file must be present on deployment host" if not vault_ok else None,
            },
            "cloudflare": {
                "ok": cf_ok,
                "files": cf_files,
                "note": "Domain set to themcfdfiles.ca — fill <TUNNEL_ID> in tunnel-config.yml after tunnel creation",
            },
        },
        "warnings": warnings,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
