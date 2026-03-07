"""GET /api/brain/status — Database statistics for the brain status panel."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api/brain", tags=["brain"])

PERSONAL_SOURCES = ['foi', 'personal']


@router.get("/status")
async def brain_status(db: AsyncSession = Depends(get_db)):
    """Return counts and status for the brain dashboard."""
    sql = text("""
        SELECT
            (SELECT COUNT(*) FROM decisions)                                          AS total_decisions,
            (SELECT COUNT(*) FROM chunks)                                             AS total_chunks,
            (SELECT COUNT(*) FROM chunks c
               JOIN decisions d ON d.id = c.decision_id
               WHERE d.source = ANY(:sources))                                        AS personal_chunks,
            (SELECT COUNT(*) FROM contradictions)                                     AS contradiction_count,
            (SELECT MAX(created_at) FROM decisions
               WHERE source = ANY(:sources))                                          AS last_personal_loaded
    """)
    row = (await db.execute(sql, {"sources": PERSONAL_SOURCES})).one()

    return {
        "total_decisions": row.total_decisions,
        "total_chunks": row.total_chunks,
        "personal_chunks": row.personal_chunks,
        "contradiction_count": row.contradiction_count,
        "last_personal_loaded": row.last_personal_loaded.isoformat() if row.last_personal_loaded else None,
    }
