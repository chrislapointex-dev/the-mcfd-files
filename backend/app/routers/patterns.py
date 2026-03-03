"""Pattern analysis endpoints — entity frequency, co-occurrence, and timeline.

GET /api/patterns/entities
GET /api/patterns/entities/{entity_value}
GET /api/patterns/co-occurrence
GET /api/patterns/timeline
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


# ── Response models ───────────────────────────────────────────────────────────


class EntityCount(BaseModel):
    entity_value: str
    entity_type: str
    count: int
    decision_ids: list[int]


class EntityAppearance(BaseModel):
    decision_id: int
    title: str
    date: Optional[date]
    source: str
    citation: Optional[str]
    url: str
    co_entities: list[str]


class EntityDetail(BaseModel):
    entity_value: str
    entity_type: str
    appearances: list[EntityAppearance]


class CoOccurrencePair(BaseModel):
    entity_a: str
    entity_b: str
    co_occurrence_count: int
    decision_ids: list[int]


class TimelineEntry(BaseModel):
    date: Optional[date]
    decision_id: int
    title: str
    source: str
    citation: Optional[str]
    url: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/entities", response_model=list[EntityCount])
async def list_entities(
    entity_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Entity values grouped by (type, value), sorted by occurrence count desc."""
    type_clause = "AND entity_type = :entity_type" if entity_type else ""
    params: dict = {"limit": limit, "offset": offset}
    if entity_type:
        params["entity_type"] = entity_type

    sql = text(f"""
        SELECT
            entity_type,
            entity_value,
            COUNT(DISTINCT decision_id)                              AS count,
            array_agg(DISTINCT decision_id ORDER BY decision_id)     AS decision_ids
        FROM entities
        WHERE entity_type <> 'none'
          {type_clause}
        GROUP BY entity_type, entity_value
        ORDER BY count DESC, entity_value
        LIMIT :limit OFFSET :offset
    """)

    try:
        rows = (await db.execute(sql, params)).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return [
        EntityCount(
            entity_type=r.entity_type,
            entity_value=r.entity_value,
            count=r.count,
            decision_ids=list(r.decision_ids or []),
        )
        for r in rows
    ]


@router.get("/entities/{entity_value}", response_model=EntityDetail)
async def entity_detail(
    entity_value: str,
    db: AsyncSession = Depends(get_db),
):
    """All decisions containing this entity value, with co-occurring entities."""
    sql = text("""
        WITH target AS (
            SELECT DISTINCT
                d.id,
                d.title,
                d.date,
                d.source,
                d.citation,
                d.url,
                e.entity_type
            FROM entities e
            JOIN decisions d ON d.id = e.decision_id
            WHERE lower(e.entity_value) = lower(:entity_value)
              AND e.entity_type <> 'none'
        ),
        co AS (
            SELECT
                e.decision_id,
                array_agg(DISTINCT e.entity_value ORDER BY e.entity_value) AS co_entities
            FROM entities e
            JOIN target t ON t.id = e.decision_id
            WHERE e.entity_type <> 'none'
              AND lower(e.entity_value) <> lower(:entity_value)
            GROUP BY e.decision_id
        )
        SELECT
            t.id            AS decision_id,
            t.title,
            t.date,
            t.source,
            t.citation,
            t.url,
            t.entity_type,
            COALESCE(co.co_entities, ARRAY[]::text[]) AS co_entities
        FROM target t
        LEFT JOIN co ON co.decision_id = t.id
        ORDER BY t.date DESC NULLS LAST
    """)

    try:
        rows = (await db.execute(sql, {"entity_value": entity_value})).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not rows:
        raise HTTPException(status_code=404, detail=f"No entities found for '{entity_value}'")

    appearances = [
        EntityAppearance(
            decision_id=r.decision_id,
            title=r.title,
            date=r.date,
            source=r.source,
            citation=r.citation,
            url=r.url,
            co_entities=list(r.co_entities or [])[:20],
        )
        for r in rows
    ]

    return EntityDetail(
        entity_value=entity_value,
        entity_type=rows[0].entity_type,
        appearances=appearances,
    )


@router.get("/co-occurrence", response_model=list[CoOccurrencePair])
async def co_occurrence(
    entity_type_a: str = Query(..., description="First entity type (e.g. 'judge')"),
    entity_type_b: str = Query(..., description="Second entity type (e.g. 'outcome')"),
    min_count: int = Query(2, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Entity pairs (one of each type) that appear together in the same decisions."""
    sql = text("""
        SELECT
            ea.entity_value                                            AS entity_a,
            eb.entity_value                                            AS entity_b,
            COUNT(DISTINCT ea.decision_id)                             AS co_occurrence_count,
            array_agg(DISTINCT ea.decision_id ORDER BY ea.decision_id) AS decision_ids
        FROM entities ea
        JOIN entities eb ON ea.decision_id = eb.decision_id
        WHERE ea.entity_type = :type_a
          AND eb.entity_type = :type_b
          AND ea.entity_value <> '-'
          AND eb.entity_value <> '-'
          AND (ea.entity_type <> eb.entity_type OR ea.entity_value <> eb.entity_value)
        GROUP BY ea.entity_value, eb.entity_value
        HAVING COUNT(DISTINCT ea.decision_id) >= :min_count
        ORDER BY co_occurrence_count DESC, ea.entity_value, eb.entity_value
        LIMIT 100
    """)

    try:
        rows = (await db.execute(sql, {
            "type_a": entity_type_a,
            "type_b": entity_type_b,
            "min_count": min_count,
        })).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return [
        CoOccurrencePair(
            entity_a=r.entity_a,
            entity_b=r.entity_b,
            co_occurrence_count=r.co_occurrence_count,
            decision_ids=list(r.decision_ids or []),
        )
        for r in rows
    ]


@router.get("/timeline", response_model=list[TimelineEntry])
async def timeline(
    entity_value: str = Query(..., min_length=1),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """Decisions containing this entity value, ordered by date ascending."""
    clauses = [
        "lower(e.entity_value) = lower(:entity_value)",
        "e.entity_type <> 'none'",
    ]
    params: dict = {"entity_value": entity_value}

    if start_date:
        clauses.append("d.date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        clauses.append("d.date <= :end_date")
        params["end_date"] = end_date

    where = " AND ".join(clauses)

    sql = text(f"""
        SELECT
            d.date,
            d.id        AS decision_id,
            d.title,
            d.source,
            d.citation,
            d.url
        FROM entities e
        JOIN decisions d ON d.id = e.decision_id
        WHERE {where}
        GROUP BY d.id, d.date, d.title, d.source, d.citation, d.url
        ORDER BY d.date ASC NULLS LAST, d.id
    """)

    try:
        rows = (await db.execute(sql, params)).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return [
        TimelineEntry(
            date=r.date,
            decision_id=r.decision_id,
            title=r.title,
            source=r.source,
            citation=r.citation,
            url=r.url,
        )
        for r in rows
    ]
