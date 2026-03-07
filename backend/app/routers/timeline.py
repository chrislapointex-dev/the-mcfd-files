"""GET /api/timeline — Case timeline built from date patterns in document chunks.

Flow:
  1. Query all chunks from 'foi' and 'personal' sources
  2. Run regex on each chunk to find date patterns
  3. Group events by date, collect text snippet + source + citation
  4. Sort ascending by date
  5. Return list of { date, events: [...] }
"""

import re
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api", tags=["timeline"])

PERSONAL_SOURCES = ['foi', 'personal']
MAX_EVENTS = 500

_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

_ISO_RE = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
_LONG_RE = re.compile(
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+(\d{1,2}),?\s+(\d{4})\b',
    re.IGNORECASE,
)


def _extract_dates(text: str) -> list[str]:
    """Return all YYYY-MM-DD date strings found in text."""
    found: list[str] = []

    for m in _ISO_RE.finditer(text):
        found.append(m.group(1))

    for m in _LONG_RE.finditer(text):
        month_name = m.group(1).lower()
        day = int(m.group(2))
        year = int(m.group(3))
        month = _MONTH_MAP.get(month_name)
        if month:
            try:
                d = date_type(year, month, day)
                found.append(d.isoformat())
            except ValueError:
                pass

    return found


@router.get("/timeline")
async def get_timeline(db: AsyncSession = Depends(get_db)):
    """Build a date-sorted timeline from personal/FOI document chunks."""
    sql = text("""
        SELECT
            c.id        AS chunk_id,
            c.text,
            c.citation,
            d.source,
            d.title
        FROM chunks c
        JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = ANY(:sources)
          AND c.text IS NOT NULL
        ORDER BY c.id
    """)
    rows = (await db.execute(sql, {"sources": PERSONAL_SOURCES})).all()

    # Group events by date
    events_by_date: dict[str, list[dict]] = {}
    total = 0

    for r in rows:
        if total >= MAX_EVENTS:
            break
        dates = _extract_dates(r.text)
        for d in set(dates):  # deduplicate within same chunk
            if total >= MAX_EVENTS:
                break
            entry = {
                "text": r.text[:200],
                "source": r.source,
                "citation": r.citation or r.title or "",
                "chunk_id": r.chunk_id,
            }
            if d not in events_by_date:
                events_by_date[d] = []
            events_by_date[d].append(entry)
            total += 1

    # Sort by date ascending
    sorted_dates = sorted(events_by_date.keys())
    timeline = [
        {"date": d, "events": events_by_date[d]}
        for d in sorted_dates
    ]

    return {"timeline": timeline, "total_events": total}
