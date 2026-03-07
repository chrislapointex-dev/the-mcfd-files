"""GET /api/export/trial-package — Download ZIP with trial prep materials.

Contents:
  contradictions.csv  — all contradiction records
  timeline.csv        — dated events from FOI/personal chunks
  witnesses.txt       — per-witness chunk excerpts
  brain_status.json   — current database stats
  README.txt          — explains each file
"""

import csv
import io
import json
import re
import zipfile
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api/export", tags=["export"])

PERSONAL_SOURCES = ['foi', 'personal']
TRIAL_DATE = "2026-05-19"
CASE_NUMBERS = "PC 19700 · PC 19709 · SC 64242 · SC 064851"

# Date extraction — same logic as timeline.py
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

WITNESS_LIST = [
    {"name": "Nicki Wolfenden",   "role": "Social Worker",            "file": "PC 19700"},
    {"name": "Tammy Newton",      "role": "Team Leader",              "file": "PC 19700"},
    {"name": "Jordon Muileboom", "role": "Acting Team Leader",        "file": "PC 19700"},
    {"name": "Robyn Burnstein",   "role": "Centralized Screening TL", "file": "PC 19700"},
    {"name": "Cheryl Martin",     "role": "Director Counsel",         "file": "SC 64242"},
    {"name": "Plessa Walden",     "role": "Opposing Counsel",         "file": "SC 064851"},
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


async def _build_contradictions_csv(db: AsyncSession) -> str:
    sql = text("""
        SELECT id, claim, evidence, source_doc, page_ref, severity, created_at
        FROM contradictions
        ORDER BY created_at DESC
    """)
    rows = (await db.execute(sql)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "claim", "evidence", "source_doc", "page_ref", "severity", "created_at"])
    for r in rows:
        w.writerow([r.id, r.claim, r.evidence, r.source_doc, r.page_ref, r.severity,
                    r.created_at.isoformat() if r.created_at else ""])
    return buf.getvalue()


async def _build_timeline_csv(db: AsyncSession) -> str:
    sql = text("""
        SELECT c.id AS chunk_id, c.text, c.citation, d.source, d.title
        FROM chunks c
        JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = ANY(:sources) AND c.text IS NOT NULL
        ORDER BY c.id
    """)
    rows = (await db.execute(sql, {"sources": PERSONAL_SOURCES})).all()

    events_by_date: dict[str, list[dict]] = {}
    for r in rows:
        for ds in set(_extract_dates(r.text)):
            entry = {
                "text": r.text[:300],
                "source": r.source,
                "citation": r.citation or r.title or "",
                "chunk_id": r.chunk_id,
            }
            events_by_date.setdefault(ds, []).append(entry)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "text", "source", "citation", "chunk_id"])
    for ds in sorted(events_by_date.keys()):
        for ev in events_by_date[ds]:
            w.writerow([ds, ev["text"], ev["source"], ev["citation"], ev["chunk_id"]])
    return buf.getvalue()


async def _build_witnesses_txt(db: AsyncSession) -> str:
    parts = []
    for witness in WITNESS_LIST:
        name = witness["name"]
        sql = text("""
            SELECT c.text, c.citation, d.source, d.title
            FROM chunks c
            JOIN decisions d ON d.id = c.decision_id
            WHERE lower(c.text) LIKE '%' || lower(:name) || '%'
              AND d.source = ANY(:sources)
            ORDER BY c.id
            LIMIT 20
        """)
        rows = (await db.execute(sql, {"name": name, "sources": PERSONAL_SOURCES})).all()

        parts.append(f"{'='*60}")
        parts.append(f"WITNESS: {name}")
        parts.append(f"Role: {witness['role']} | File: {witness['file']}")
        parts.append(f"Chunks found: {len(rows)}")
        parts.append("")
        for i, r in enumerate(rows, 1):
            citation = r.citation or r.title or "unknown"
            parts.append(f"  [{i}] Source: {r.source} | Citation: {citation}")
            parts.append(f"  {r.text[:500].strip()}")
            parts.append("")
    return "\n".join(parts)


async def _build_brain_status_json(db: AsyncSession) -> str:
    sql = text("""
        SELECT
            (SELECT COUNT(*) FROM decisions)                                 AS total_decisions,
            (SELECT COUNT(*) FROM chunks)                                    AS total_chunks,
            (SELECT COUNT(*) FROM chunks c
               JOIN decisions d ON d.id = c.decision_id
               WHERE d.source = ANY(:sources))                               AS personal_chunks,
            (SELECT COUNT(*) FROM contradictions)                            AS contradiction_count
    """)
    row = (await db.execute(sql, {"sources": PERSONAL_SOURCES})).one()
    data = {
        "total_decisions": int(row.total_decisions),
        "total_chunks": int(row.total_chunks),
        "personal_chunks": int(row.personal_chunks),
        "contradiction_count": int(row.contradiction_count),
        "exported_at": datetime.utcnow().isoformat() + "Z",
    }
    return json.dumps(data, indent=2)


def _build_readme() -> str:
    return f"""THE MCFD FILES — TRIAL PACKAGE
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Trial Date: {TRIAL_DATE} (May 19–21, 2026)
Case Numbers: {CASE_NUMBERS}

FILES IN THIS PACKAGE
---------------------

contradictions.csv
  All contradiction records generated by the AI contradiction engine.
  Columns: id, claim, evidence, source_doc, page_ref, severity, created_at
  Severity values: DIRECT | PARTIAL | NONE

timeline.csv
  Date-stamped events extracted from FOI and personal document chunks.
  Columns: date, text (excerpt), source, citation, chunk_id
  Sorted chronologically. Use to identify gaps in MCFD's record.

witnesses.txt
  Per-witness excerpt summaries from FOI and personal documents.
  Each section shows up to 20 matching chunks for that witness.
  Witnesses: Nicki Wolfenden, Tammy Newton, Jordon Muileboom,
             Robyn Burnstein, Cheryl Martin, Plessa Walden

brain_status.json
  Snapshot of database statistics at time of export.

USAGE NOTES
-----------
- Import CSVs into Excel/Numbers for filtering and sorting
- Sort contradictions by severity=DIRECT for strongest evidence
- Timeline gaps between 2025-08-07 and 2025-09-08 are key
- All source documents are from FOI disclosure or personal case files
"""


@router.get("/trial-package")
async def export_trial_package(db: AsyncSession = Depends(get_db)):
    """Stream a ZIP file containing all trial prep materials."""
    today = datetime.utcnow().strftime("%Y%m%d")
    filename = f"trial_package_{today}.zip"

    # Build all content concurrently (sequential is fine — all fast DB queries)
    contradictions_csv = await _build_contradictions_csv(db)
    timeline_csv = await _build_timeline_csv(db)
    witnesses_txt = await _build_witnesses_txt(db)
    brain_status_json = await _build_brain_status_json(db)
    readme_txt = _build_readme()

    # Pack into ZIP in memory
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("contradictions.csv", contradictions_csv)
        zf.writestr("timeline.csv", timeline_csv)
        zf.writestr("witnesses.txt", witnesses_txt)
        zf.writestr("brain_status.json", brain_status_json)
        zf.writestr("README.txt", readme_txt)
    zip_buf.seek(0)

    return StreamingResponse(
        zip_buf,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
