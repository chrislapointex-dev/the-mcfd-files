"""Agent control endpoints.

GET  /api/agents/status           → list all agent statuses
POST /api/agents/scrape/canlii    → trigger CanLII scraper
POST /api/agents/scrape/rcy       → trigger RCY scraper
POST /api/agents/scrape/hansard   → trigger Hansard scraper
GET  /api/agents/scraped/stats    → row counts for scraped tables
POST /api/agents/embed-scraped    → embed unembedded ScrapedDecision rows
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ScrapedDecision, ScrapedReport, ScrapedHansard, Decision, Chunk
from ..services.embed_service import embed_query
from ..agents import core, scraper

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _result_to_dict(r: core.AgentResult) -> dict:
    return {
        "name": r.agent_name,
        "status": r.status.value,
        "last_run": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "records_found": r.records_found,
        "records_added": r.records_added,
        "errors": r.errors,
        "log": r.log,
    }


# Ensure agents appear in registry on first status call
def _ensure_registered():
    for name in ("canlii", "rcy", "hansard"):
        core.register_agent(name)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    _ensure_registered()
    agents = core.get_all_agents()
    return {"agents": [_result_to_dict(a) for a in agents]}


@router.post("/scrape/canlii")
async def trigger_canlii(
    background_tasks: BackgroundTasks,
    pages: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    agent = core.register_agent("canlii")
    if agent.status == core.AgentStatus.RUNNING:
        return {"message": "Already running", "agent": _result_to_dict(agent)}

    async def run():
        async for _db in get_db():
            result = await scraper.scrape_canlii(pages, _db)
            core.update_status("canlii", result)

    background_tasks.add_task(asyncio.create_task, run())
    agent.status = core.AgentStatus.RUNNING
    return {"message": "CanLII scraper started", "agent": _result_to_dict(agent)}


@router.post("/scrape/rcy")
async def trigger_rcy(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    agent = core.register_agent("rcy")
    if agent.status == core.AgentStatus.RUNNING:
        return {"message": "Already running", "agent": _result_to_dict(agent)}

    async def run():
        async for _db in get_db():
            result = await scraper.scrape_rcy(_db)
            core.update_status("rcy", result)

    background_tasks.add_task(asyncio.create_task, run())
    agent.status = core.AgentStatus.RUNNING
    return {"message": "RCY scraper started", "agent": _result_to_dict(agent)}


@router.post("/scrape/hansard")
async def trigger_hansard(
    background_tasks: BackgroundTasks,
    pages: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    agent = core.register_agent("hansard")
    if agent.status == core.AgentStatus.RUNNING:
        return {"message": "Already running", "agent": _result_to_dict(agent)}

    async def run():
        async for _db in get_db():
            result = await scraper.scrape_hansard(pages, _db)
            core.update_status("hansard", result)

    background_tasks.add_task(asyncio.create_task, run())
    agent.status = core.AgentStatus.RUNNING
    return {"message": "Hansard scraper started", "agent": _result_to_dict(agent)}


@router.get("/scraped/stats")
async def scraped_stats(db: AsyncSession = Depends(get_db)):
    decisions_total = (await db.execute(select(func.count()).select_from(ScrapedDecision))).scalar_one()
    decisions_unembedded = (await db.execute(
        select(func.count()).select_from(ScrapedDecision).where(ScrapedDecision.embedded == False)  # noqa: E712
    )).scalar_one()
    reports_total = (await db.execute(select(func.count()).select_from(ScrapedReport))).scalar_one()
    reports_unembedded = (await db.execute(
        select(func.count()).select_from(ScrapedReport).where(ScrapedReport.embedded == False)  # noqa: E712
    )).scalar_one()
    hansard_total = (await db.execute(select(func.count()).select_from(ScrapedHansard))).scalar_one()
    hansard_unembedded = (await db.execute(
        select(func.count()).select_from(ScrapedHansard).where(ScrapedHansard.embedded == False)  # noqa: E712
    )).scalar_one()

    return {
        "scraped_decisions": {"total": decisions_total, "unembedded": decisions_unembedded},
        "scraped_reports": {"total": reports_total, "unembedded": reports_unembedded},
        "scraped_hansard": {"total": hansard_total, "unembedded": hansard_unembedded},
        "total_unembedded": decisions_unembedded + reports_unembedded + hansard_unembedded,
    }


@router.post("/embed-scraped")
async def embed_scraped(
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Embed unembedded ScrapedDecision rows into Decision + Chunk tables."""
    rows = (await db.execute(
        select(ScrapedDecision)
        .where(ScrapedDecision.embedded == False)  # noqa: E712
        .limit(limit)
    )).scalars().all()

    embedded_count = 0
    for row in rows:
        try:
            # Insert Decision row
            decision = Decision(
                source="canlii-scraped",
                title=row.case_name or row.citation or "",
                citation=row.citation,
                date=row.date,
                court=row.court,
                url=row.url,
                snippet=row.excerpt[:300] if row.excerpt else None,
            )
            db.add(decision)
            await db.flush()  # get decision.id

            # Embed excerpt
            if row.excerpt:
                vec = await embed_query(row.excerpt[:512])
                chunk = Chunk(
                    decision_id=decision.id,
                    chunk_num=0,
                    text=row.excerpt,
                    citation=row.citation,
                    embedding=vec,
                )
                db.add(chunk)

            row.embedded = True
            embedded_count += 1
        except Exception as e:
            await db.rollback()
            continue

    await db.commit()
    return {"embedded": embedded_count}
