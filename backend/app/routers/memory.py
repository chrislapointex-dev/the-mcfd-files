from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from r2d2 import R2Memory
from r2d2.context import ContextBuilder

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("")
async def get_memory(
    region: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return raw memory rows, optionally filtered by region or category."""
    mem = R2Memory(db=db)
    rows = await mem.recall(region=region, category=category, limit=limit)
    return {"count": len(rows), "rows": rows}


@router.get("/context")
async def get_context(
    limit_per_region: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Return memory grouped by region plus a formatted briefing string."""
    mem = R2Memory(db=db)
    builder = ContextBuilder(mem)
    regions = await mem.get_context(limit_per_region=limit_per_region)
    briefing = await builder.build(limit_per_region=limit_per_region)
    return {"regions": regions, "briefing": briefing}


@router.get("/searches")
async def get_recent_searches(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return recent search queries in chronological order."""
    mem = R2Memory(db=db)
    builder = ContextBuilder(mem)
    queries = await builder.recent_searches(n=limit)
    return {"count": len(queries), "queries": queries}
