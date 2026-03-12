"""GET /api/trialprep/summary — Trial prep dashboard data.

Returns:
  - days remaining to trial (May 19, 2026)
  - contradiction count
  - personal chunk count
  - top 5 contradictions
  - timeline gaps in critical period Aug 7 – Sep 8, 2025
"""

import re
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..redact import redact_name

router = APIRouter(prefix="/api/trialprep", tags=["trialprep"])

PERSONAL_SOURCES = ['foi', 'personal']
TRIAL_DATE = date_type(2026, 5, 19)

# Date regex — same as timeline.py
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

GAP_START = date_type(2025, 8, 7)
GAP_END = date_type(2025, 9, 8)
GAP_THRESHOLD_DAYS = 3

KEY_WITNESSES = [
    "Nicki Wolfenden",
    "Tammy Newton",
    "Jordon Muileboom",
    "Robyn Burnstein",
]


def _extract_dates(txt: str) -> list[str]:
    found: list[str] = []
    for m in _ISO_RE.finditer(txt):
        found.append(m.group(1))
    for m in _LONG_RE.finditer(txt):
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


def _find_gaps(dates_in_range: list[str]) -> list[dict]:
    """Find gaps > GAP_THRESHOLD_DAYS between consecutive dates."""
    if not dates_in_range:
        return []
    sorted_dates = sorted(set(dates_in_range))
    gaps = []
    for i in range(len(sorted_dates) - 1):
        a = date_type.fromisoformat(sorted_dates[i])
        b = date_type.fromisoformat(sorted_dates[i + 1])
        delta = (b - a).days
        if delta > GAP_THRESHOLD_DAYS:
            gaps.append({
                "start": a.isoformat(),
                "end": b.isoformat(),
                "days": delta,
            })
    return gaps


@router.get("/summary")
async def trial_summary(db: AsyncSession = Depends(get_db)):
    """Return trial prep summary dashboard data."""
    today = date_type.today()
    days_remaining = (TRIAL_DATE - today).days

    # Contradiction count + top 5
    contra_sql = text("""
        SELECT COUNT(*) AS cnt FROM contradictions
    """)
    contra_count = (await db.execute(contra_sql)).scalar() or 0

    top_sql = text("""
        SELECT id, claim, evidence, source_doc, page_ref, severity, created_at
        FROM contradictions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    top_rows = (await db.execute(top_sql)).all()
    top_contradictions = [
        {
            "id": r.id,
            "claim": redact_name(r.claim),
            "evidence": redact_name(r.evidence) if r.evidence else r.evidence,
            "source_doc": redact_name(r.source_doc) if r.source_doc else r.source_doc,
            "page_ref": r.page_ref,
            "severity": r.severity,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in top_rows
    ]

    # Personal chunk count
    personal_sql = text("""
        SELECT COUNT(*) AS cnt
        FROM chunks c
        JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = ANY(:sources)
    """)
    personal_chunks = (await db.execute(personal_sql, {"sources": PERSONAL_SOURCES})).scalar() or 0

    # Timeline gap analysis — pull chunks from critical window sources
    chunk_sql = text("""
        SELECT c.text
        FROM chunks c
        JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = ANY(:sources)
          AND c.text IS NOT NULL
    """)
    chunk_rows = (await db.execute(chunk_sql, {"sources": PERSONAL_SOURCES})).all()

    # Collect all dates in the critical range
    dates_in_range: list[str] = []
    for row in chunk_rows:
        for ds in _extract_dates(row.text):
            try:
                d = date_type.fromisoformat(ds)
                if GAP_START <= d <= GAP_END:
                    dates_in_range.append(ds)
            except ValueError:
                pass

    timeline_gaps = _find_gaps(dates_in_range)

    return {
        "trial_date": TRIAL_DATE.isoformat(),
        "days_remaining": days_remaining,
        "contradiction_count": int(contra_count),
        "personal_chunks": int(personal_chunks),
        "key_witnesses": [redact_name(w) for w in KEY_WITNESSES],
        "top_contradictions": top_contradictions,
        "timeline_gaps": timeline_gaps,
    }
