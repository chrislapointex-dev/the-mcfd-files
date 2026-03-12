"""Public /api/share endpoints — view counter for the /share page."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Contradiction, ShareView, TimelineEvent
from ..ratelimit import rate_limit_public, rate_limit_view
from ..redact import redact_name

router = APIRouter(prefix="/api/share", tags=["share"])


class ViewRequest(BaseModel):
    referrer: Optional[str] = None


@router.post("/view")
async def record_view(body: ViewRequest, db: AsyncSession = Depends(get_db), _: None = Depends(rate_limit_view)):
    """Record a /share page view. Returns total view count."""
    view = ShareView(referrer=body.referrer)
    db.add(view)
    await db.commit()

    total = (await db.execute(select(func.count()).select_from(ShareView))).scalar_one()
    return JSONResponse({"total_views": total})


@router.get("/strength")
async def get_strength(db: AsyncSession = Depends(get_db), _: None = Depends(rate_limit_public)):
    """Return a case strength score based on documented evidence."""
    total_count = (await db.execute(
        select(func.count()).select_from(Contradiction)
    )).scalar_one()

    direct_count = (await db.execute(
        select(func.count()).select_from(Contradiction).where(
            Contradiction.severity == 'DIRECT'
        )
    )).scalar_one()

    # Fixed evidence scores
    foi_gap_score = 15
    cost_score = 15
    video_score = 20
    judicial_default_score = 10

    # Dynamic: 8 pts per DIRECT contradiction, max 40
    contradiction_score = min(int(direct_count) * 8, 40)

    total_score = foi_gap_score + cost_score + video_score + judicial_default_score + contradiction_score
    max_score = 100
    percentage = round(total_score / max_score * 100, 1)

    if total_score > 75:
        rating = "STRONG"
    elif total_score > 50:
        rating = "SOLID"
    else:
        rating = "DEVELOPING"

    breakdown = [
        {"category": "FOI Disclosure Gap", "points": foi_gap_score, "max": 15,
         "note": "906 vs 1,792 pages — OIPC complaint active"},
        {"category": "Taxpayer Cost Documentation", "points": cost_score, "max": 15,
         "note": f"${175041.32:,.2f} — BC published rates"},
        {"category": "Video Evidence", "points": video_score, "max": 20,
         "note": "Lawfully recorded interactions preserved"},
        {"category": "Judicial Default Record", "points": judicial_default_score, "max": 10,
         "note": "Prior orders and non-compliance documented"},
        {"category": f"Direct Contradictions ({direct_count} of {total_count})", "points": contradiction_score, "max": 40,
         "note": "8 pts per DIRECT severity contradiction, max 40"},
    ]

    return JSONResponse({
        "total_score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "rating": rating,
        "breakdown": breakdown,
        "disclaimer": "This score is a structured summary of documented evidence, not a legal opinion. It is intended to help journalists and researchers assess the evidentiary record at a glance.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })


@router.get("/views")
async def get_views(db: AsyncSession = Depends(get_db), _: None = Depends(rate_limit_public)):
    """Return view stats for the /share page."""
    row = (await db.execute(text("""
        SELECT
            COUNT(*) AS total_views,
            MIN(viewed_at) AS first_view,
            MAX(viewed_at) AS latest_view,
            COUNT(*) FILTER (WHERE viewed_at::date = CURRENT_DATE) AS views_today
        FROM share_views
    """))).one()

    return JSONResponse({
        "total_views": int(row.total_views),
        "first_view": row.first_view.isoformat() if row.first_view else None,
        "latest_view": row.latest_view.isoformat() if row.latest_view else None,
        "views_today": int(row.views_today),
    })


@router.get("/contradictions")
async def public_contradictions(db: AsyncSession = Depends(get_db), _: None = Depends(rate_limit_public)):
    """Public contradiction list for /share page (no auth required)."""
    rows = (await db.execute(
        select(Contradiction).order_by(Contradiction.created_at.desc())
    )).scalars().all()
    return [
        {
            "id": r.id,
            "claim": redact_name(r.claim),
            "evidence": redact_name(r.evidence) if r.evidence else r.evidence,
            "source_doc": redact_name(r.source_doc) if r.source_doc else r.source_doc,
            "severity": r.severity,
        }
        for r in rows
    ]


@router.get("/timeline")
async def public_timeline(db: AsyncSession = Depends(get_db), _: None = Depends(rate_limit_public)):
    """Public timeline events for /share page (no auth required)."""
    rows = (await db.execute(
        select(TimelineEvent).order_by(TimelineEvent.event_date)
    )).scalars().all()
    return [
        {
            "id": r.id,
            "title": redact_name(r.title),
            "event_date": str(r.event_date) if r.event_date else None,
            "severity": r.severity,
            "description": redact_name(r.description) if r.description else r.description,
        }
        for r in rows
    ]
