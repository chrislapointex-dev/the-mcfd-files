from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Decision
from ..schemas import DecisionDetail, DecisionSummary, FiltersResponse, PaginatedDecisions
from r2d2 import R2Memory

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


def _apply_filters(stmt, court, date_from, date_to, source=None):
    if source:
        stmt = stmt.where(Decision.source == source)
    if court:
        stmt = stmt.where(Decision.court == court)
    if date_from:
        stmt = stmt.where(Decision.date >= date_from)
    if date_to:
        stmt = stmt.where(Decision.date <= date_to)
    return stmt


@router.get("", response_model=PaginatedDecisions)
async def list_decisions(
    court: Optional[str] = None,
    source: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    base = select(Decision)
    base = _apply_filters(base, court, date_from, date_to, source)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Decision.date.desc().nulls_last())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    items = [DecisionSummary.model_validate(r) for r in rows]
    return PaginatedDecisions(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),
    )


@router.get("/search", response_model=PaginatedDecisions)
async def search_decisions(
    q: str = Query(..., min_length=1),
    court: Optional[str] = None,
    source: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    tsquery = func.websearch_to_tsquery("english", q)
    tsvector = func.to_tsvector(
        "english",
        func.coalesce(Decision.title, "")
        + " "
        + func.coalesce(Decision.citation, "")
        + " "
        + func.coalesce(Decision.full_text, ""),
    )
    rank = func.ts_rank_cd(tsvector, tsquery).label("rank")
    headline = func.ts_headline(
        "english",
        func.coalesce(Decision.full_text, ""),
        tsquery,
        "MaxFragments=1,MaxWords=35,MinWords=15,StartSel=<mark>,StopSel=</mark>",
    ).label("headline")

    base = (
        select(Decision, rank, headline)
        .where(tsvector.op("@@")(tsquery))
    )
    base = _apply_filters(base, court, date_from, date_to, source)

    count_base = select(Decision).where(tsvector.op("@@")(tsquery))
    count_base = _apply_filters(count_base, court, date_from, date_to, source)
    count_stmt = select(func.count()).select_from(count_base.subquery())

    total = (await db.execute(count_stmt)).scalar_one()

    results = (
        await db.execute(
            base.order_by(rank.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()

    items = []
    for row in results:
        decision, _rank, hl = row
        summary = DecisionSummary.model_validate(decision)
        # Replace snippet with highlighted excerpt from full text
        if hl:
            summary.snippet = hl
        items.append(summary)

    # Log search to R2 memory (fire-and-forget — never fails the request)
    try:
        mem = R2Memory(db=db)
        await mem.log_search(
            query=q,
            result_count=total,
            filters={"court": court, "source": source,
                     "date_from": str(date_from) if date_from else None,
                     "date_to": str(date_to) if date_to else None},
        )
    except Exception:
        pass

    return PaginatedDecisions(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),
    )


@router.get("/filters", response_model=FiltersResponse)
async def get_filters(db: AsyncSession = Depends(get_db)):
    sources_result = await db.execute(
        select(Decision.source).distinct().order_by(Decision.source)
    )
    sources = [r[0] for r in sources_result.all()]

    courts_result = await db.execute(
        select(Decision.court)
        .where(Decision.court.isnot(None))
        .distinct()
        .order_by(Decision.court)
    )
    courts = [r[0] for r in courts_result.all()]

    year_result = await db.execute(
        select(
            func.min(func.extract("year", Decision.date)),
            func.max(func.extract("year", Decision.date)),
        ).where(Decision.date.isnot(None))
    )
    year_min, year_max = year_result.one()

    return FiltersResponse(
        sources=sources,
        courts=courts,
        year_min=int(year_min) if year_min else None,
        year_max=int(year_max) if year_max else None,
    )


@router.get("/{decision_id}", response_model=DecisionDetail)
async def get_decision(decision_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Decision).where(Decision.id == decision_id))
    decision = result.scalar_one_or_none()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Log view to R2 memory
    try:
        mem = R2Memory(db=db)
        await mem.log_view(
            decision_id=decision.id,
            title=decision.title,
            citation=decision.citation,
        )
    except Exception:
        pass

    return DecisionDetail.model_validate(decision)
