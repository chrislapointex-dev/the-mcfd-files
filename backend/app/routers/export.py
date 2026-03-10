"""GET /api/export/trial-package — Download ZIP with trial prep materials.

Contents:
  contradictions.csv  — all contradiction records
  timeline.csv        — dated events from FOI/personal chunks
  witnesses.txt       — per-witness chunk excerpts
  brain_status.json   — current database stats
  README.txt          — explains each file
"""

import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import date, date as date_type, datetime, timezone

import fitz  # PyMuPDF

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_api_key
from ..database import get_db
from ..models import CostEntry
from ..ratelimit import rate_limit_public

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


@router.get("/trial-package", dependencies=[Depends(require_api_key)])
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


@router.get("/trial-summary", dependencies=[Depends(require_api_key)])
async def export_trial_summary(db: AsyncSession = Depends(get_db)):
    """Return structured JSON with trial-ready evidence for frontend download."""
    TRIAL_DATE_OBJ = date(2026, 5, 19)
    days_to_trial = (TRIAL_DATE_OBJ - date.today()).days

    foi_sql = text("""
        SELECT c.id, c.text, c.citation, c.page_estimate, d.title
        FROM chunks c JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = 'foi'
        ORDER BY c.page_estimate NULLS LAST, c.id
    """)
    contradictions_sql = text("""
        SELECT id, claim, evidence, source_doc, severity
        FROM contradictions ORDER BY id
    """)
    personal_sql = text("""
        SELECT c.id, c.text, c.citation, d.title
        FROM chunks c JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = 'personal'
        ORDER BY c.id
    """)
    counts_sql = text("""
        SELECT
            (SELECT COUNT(*) FROM decisions) as total_decisions,
            (SELECT COUNT(*) FROM chunks c JOIN decisions d ON d.id=c.decision_id WHERE d.source='foi') as foi_count,
            (SELECT COUNT(*) FROM contradictions) as contradiction_count,
            (SELECT COUNT(*) FROM chunks c JOIN decisions d ON d.id=c.decision_id WHERE d.source='personal') as personal_count
    """)

    foi_rows = (await db.execute(foi_sql)).all()
    contradiction_rows = (await db.execute(contradictions_sql)).all()
    personal_rows = (await db.execute(personal_sql)).all()
    counts_row = (await db.execute(counts_sql)).one()

    return JSONResponse({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days_to_trial": days_to_trial,
        "trial_date": TRIAL_DATE_OBJ.isoformat(),
        "case_files": ["PC 19700", "PC 19709", "SC 64242", "SC 064851"],
        "foi_chunks": [
            {"chunk_id": r.id, "text": r.text, "citation": r.citation, "title": r.title, "page_estimate": r.page_estimate}
            for r in foi_rows
        ],
        "contradictions": [
            {"id": r.id, "claim": r.claim, "evidence": r.evidence, "source_doc": r.source_doc, "severity": r.severity}
            for r in contradiction_rows
        ],
        "personal_chunks": [
            {"chunk_id": r.id, "text": r.text, "citation": r.citation, "title": r.title}
            for r in personal_rows
        ],
        "summary": {
            "foi_chunk_count": int(counts_row.foi_count),
            "contradiction_count": int(counts_row.contradiction_count),
            "personal_chunk_count": int(counts_row.personal_count),
            "total_decisions": int(counts_row.total_decisions),
        },
    })


@router.get("/trial-report.md", dependencies=[Depends(require_api_key)])
async def export_trial_report(db: AsyncSession = Depends(get_db)):
    """Return Markdown trial evidence report for human reading / lawyer handoff."""
    TRIAL_DATE_OBJ = date(2026, 5, 19)
    days_to_trial = (TRIAL_DATE_OBJ - date.today()).days
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    today_filename = datetime.now(timezone.utc).strftime("%Y%m%d")

    foi_rows = (await db.execute(text("""
        SELECT c.id, c.text, c.citation, c.page_estimate, d.title
        FROM chunks c JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = 'foi'
        ORDER BY c.page_estimate NULLS LAST, c.id
    """))).all()

    contradiction_rows = (await db.execute(text("""
        SELECT id, claim, evidence, source_doc, severity, page_ref
        FROM contradictions ORDER BY id
    """))).all()

    personal_rows = (await db.execute(text("""
        SELECT c.id, c.text, c.citation, d.title
        FROM chunks c JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = 'personal'
        ORDER BY c.id
    """))).all()

    counts_row = (await db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM decisions) as total_decisions,
            (SELECT COUNT(*) FROM chunks c JOIN decisions d ON d.id=c.decision_id WHERE d.source='foi') as foi_count,
            (SELECT COUNT(*) FROM contradictions) as contradiction_count,
            (SELECT COUNT(*) FROM chunks c JOIN decisions d ON d.id=c.decision_id WHERE d.source='personal') as personal_count
    """))).one()

    lines = []

    # Header
    lines += [
        "# MCFD EVIDENCE REPORT",
        f"**Generated:** {today_str}",
        f"**Days to Trial:** {days_to_trial} (May 19, 2026)",
        "**Case Files:** PC 19700 | PC 19709 | SC 64242 | SC 064851",
        "",
        "---",
        "",
    ]

    # Summary table
    lines += [
        "## SUMMARY",
        "| Category | Count |",
        "|----------|-------|",
        f"| FOI Document Chunks | {int(counts_row.foi_count)} |",
        f"| Contradictions | {int(counts_row.contradiction_count)} |",
        f"| Personal Evidence Chunks | {int(counts_row.personal_count)} |",
        f"| Medical/Genetic Flags | 0 |",
        f"| BC Case Law Decisions | 0 |",
        "",
        "---",
        "",
    ]

    # Contradictions
    lines += [f"## CONTRADICTIONS ({len(contradiction_rows)})", ""]
    for i, r in enumerate(contradiction_rows, 1):
        sev = f" [{r.severity}]" if r.severity else ""
        lines.append(f"### Contradiction {i}{sev}")
        lines.append(f"**Statement A:** {r.claim or ''}")
        lines.append(f"**Statement B:** {r.evidence or ''}")
        src = r.source_doc or ""
        if r.page_ref:
            src += f" · p.{r.page_ref}"
        if src:
            lines.append(f"**Source:** {src}")
        lines.append("")
    lines += ["---", ""]

    # Medical/genetic — no data yet
    lines += [
        "## MEDICAL & GENETIC EVIDENCE (0 flags)",
        "",
        "*No medical or genetic evidence chunks indexed yet.*",
        "",
        "---",
        "",
    ]

    # FOI chunks
    lines += [f"## FOI DOCUMENT EVIDENCE ({len(foi_rows)} chunks)", ""]
    for i, r in enumerate(foi_rows, 1):
        lines.append(f"### FOI Entry {i}")
        if r.citation:
            lines.append(f"**Citation:** {r.citation}")
        if r.title:
            lines.append(f"**Document:** {r.title}")
        lines.append("")
        lines.append((r.text or "").strip())
        lines.append("")
    lines += ["---", ""]

    # Personal chunks
    lines += [f"## PERSONAL EVIDENCE CHUNKS ({len(personal_rows)})", ""]
    for i, r in enumerate(personal_rows, 1):
        lines.append(f"### Entry {i}")
        src = r.citation or r.title or "unknown"
        lines.append(f"**Source:** {src}")
        lines.append("")
        lines.append((r.text or "")[:300].strip())
        lines.append("")
    lines += ["---", ""]

    # Footer
    lines += [
        "*Report generated by The MCFD Files platform*",
        "*Pro Patria*",
    ]

    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="mcfd_trial_report_{today_filename}.md"'},
    )


def _build_pdf_bytes(foi_rows, contradiction_rows, personal_rows, counts_row, days_to_trial, today_str, evidence_by_contradiction: dict = None, crossexam_by_contradiction: dict = None, cost_rows=None, cost_total: float = 0.0) -> bytes:
    W, H = 595, 842        # A4 portrait
    ML, MT, MR, MB = 60, 60, 60, 50
    TW = W - ML - MR       # usable text width = 475pt

    doc = fitz.open()
    state = {"page": None, "y": 0, "n": 0}

    def _new_page():
        state["n"] += 1
        p = doc.new_page(width=W, height=H)
        state["page"] = p
        state["y"] = MT
        p.insert_text(
            (ML, H - 22),
            f"The MCFD Files  |  Pro Patria  —  Page {state['n']}",
            fontname="helv", fontsize=8, color=(0.5, 0.5, 0.5),
        )

    def _wrap(text: str, fs: int) -> list:
        max_c = max(1, int(TW / (fs * 0.55)))
        words = (text or "").split()
        lines, cur = [], []
        for word in words:
            if sum(len(w) for w in cur) + len(cur) + len(word) > max_c:
                lines.append(" ".join(cur))
                cur = [word]
            else:
                cur.append(word)
        if cur:
            lines.append(" ".join(cur))
        return lines or [""]

    def write(text: str, fs: int = 10, bold: bool = False, gap: int = 6, color=(0, 0, 0)):
        fn = "hebo" if bold else "helv"
        lh = fs + 3
        for line in _wrap(text, fs):
            if state["y"] + lh > H - MB - 30:
                _new_page()
            state["page"].insert_text((ML, state["y"]), line, fontname=fn, fontsize=fs, color=color)
            state["y"] += lh
        state["y"] += gap

    def rule():
        state["page"].draw_line((ML, state["y"]), (ML + TW, state["y"]), color=(0.7, 0.7, 0.7), width=0.5)
        state["y"] += 10

    _new_page()

    # ── Cover page ──────────────────────────────────────────────
    state["y"] = 180
    write("MCFD EVIDENCE REPORT", fs=24, bold=True, gap=12)
    write(f"Generated: {today_str}", fs=10, gap=6)
    write(f"Days to Trial: {days_to_trial}  (May 19, 2026)", fs=10, gap=6)
    write("Case Files: PC 19700  |  PC 19709  |  SC 64242  |  SC 064851", fs=10, gap=20)
    rule()
    write("SUMMARY", fs=13, bold=True, gap=8)
    for label, val in [
        ("FOI Document Chunks",      int(counts_row.foi_count)),
        ("Contradictions",           int(counts_row.contradiction_count)),
        ("Personal Evidence Chunks", int(counts_row.personal_count)),
        ("Medical/Genetic Flags",    0),
        ("BC Case Law Decisions",    0),
    ]:
        write(f"  {label}: {val}", fs=10, gap=4)
    state["y"] += 20

    # ── Contradictions ───────────────────────────────────────────
    _new_page()
    write(f"CONTRADICTIONS  ({len(contradiction_rows)})", fs=14, bold=True, gap=10)
    rule()
    for i, r in enumerate(contradiction_rows, 1):
        sev = f"  [{r.severity}]" if r.severity else ""
        write(f"Contradiction {i}{sev}", fs=11, bold=True, gap=4)
        write(f"Statement A:  {r.claim or ''}", fs=9, gap=3)
        write(f"Statement B:  {r.evidence or ''}", fs=9, gap=3)
        src = r.source_doc or ""
        if r.page_ref:
            src += f"  ·  p.{r.page_ref}"
        if src:
            write(f"Source:  {src}", fs=9, gap=3, color=(0.4, 0.4, 0.4))
        ev_list = (evidence_by_contradiction or {}).get(r.id, [])
        if ev_list:
            write("Supporting Evidence:", fs=8, bold=True, gap=2, color=(0.2, 0.2, 0.5))
            for ev in ev_list:
                score = f"{ev.similarity_score:.2f}" if ev.similarity_score else "?"
                src_label = ev.source.upper()
                page_str = f" p.{ev.page_estimate}" if ev.page_estimate else ""
                excerpt = (ev.text or "")[:200].strip().replace("\n", " ")
                write(f"  [{score}] {src_label}{page_str}: \"{excerpt}\"", fs=8, gap=3, color=(0.3, 0.3, 0.3))
        cq_text = (crossexam_by_contradiction or {}).get(r.id)
        if cq_text:
            write("Cross-Examination Questions:", fs=8, bold=True, gap=2, color=(0.1, 0.4, 0.1))
            write(cq_text[:800], fs=8, gap=4, color=(0.2, 0.2, 0.2))
        state["y"] += 8

    # ── Medical/Genetic (stub) ────────────────────────────────────
    _new_page()
    write("MEDICAL & GENETIC EVIDENCE  (0 flags)", fs=14, bold=True, gap=10)
    rule()
    write("No medical or genetic evidence chunks indexed yet.", fs=10, gap=6)

    # ── FOI Document Evidence ─────────────────────────────────────
    _new_page()
    write(f"FOI DOCUMENT EVIDENCE  ({len(foi_rows)} chunks)", fs=14, bold=True, gap=10)
    rule()
    for i, r in enumerate(foi_rows, 1):
        write(f"FOI Entry {i}", fs=10, bold=True, gap=3)
        if r.citation:
            write(f"Citation: {r.citation}", fs=8, gap=2, color=(0.3, 0.3, 0.3))
        if r.title:
            write(f"Document: {r.title}", fs=8, gap=2, color=(0.3, 0.3, 0.3))
        write((r.text or "")[:400].strip(), fs=9, gap=8)

    # ── Personal Evidence ─────────────────────────────────────────
    _new_page()
    write(f"PERSONAL EVIDENCE CHUNKS  ({len(personal_rows)})", fs=14, bold=True, gap=10)
    rule()
    for i, r in enumerate(personal_rows, 1):
        write(f"Entry {i}", fs=10, bold=True, gap=3)
        src = r.citation or r.title or "unknown"
        write(f"Source: {src}", fs=8, gap=2, color=(0.3, 0.3, 0.3))
        write((r.text or "")[:300].strip(), fs=9, gap=8)

    # ── Taxpayer Cost Summary ─────────────────────────────────────
    if cost_rows:
        _new_page()
        write("TAXPAYER COST SUMMARY", fs=14, bold=True, gap=10)
        rule()
        write(f"Grand Total (Documented): ${cost_total:,.2f}", fs=12, bold=True, gap=6, color=(0.8, 0.1, 0.1))
        write("Case: PC 19700 — LaPointe, Christopher  |  214 days in care", fs=9, gap=8, color=(0.4, 0.4, 0.4))

        # Category subtotals
        from collections import defaultdict
        by_cat: dict = defaultdict(float)
        for r in cost_rows:
            by_cat[r.category] += (r.total or 0.0)
        write("CATEGORY SUBTOTALS", fs=10, bold=True, gap=4)
        for cat, subtotal in sorted(by_cat.items()):
            write(f"  {cat.upper()}: ${subtotal:,.2f}", fs=9, gap=3)
        state["y"] += 6

        # Line items
        rule()
        write("LINE ITEMS", fs=10, bold=True, gap=4)
        prev_cat = None
        for r in cost_rows:
            if r.category != prev_cat:
                write(f"[ {(r.category or '').upper()} ]", fs=8, bold=True, gap=2, color=(0.3, 0.3, 0.5))
                prev_cat = r.category
            total_str = "ON RECORD" if r.total == 0 else f"${r.total:,.2f}"
            write(f"  {r.line_item}", fs=8, gap=1)
            write(f"    {total_str}  |  {r.source or ''}", fs=7, gap=4, color=(0.4, 0.4, 0.4))

        # Scale projection
        rule()
        write("BC-WIDE SCALE PROJECTION", fs=10, bold=True, gap=4)
        write(f"  Estimated true cost (this case): $285,000 – $420,000", fs=9, gap=3)
        write(f"  BC provincial projection (5,000 children): $1.4B – $2.1B / year", fs=9, gap=3)
        write(f"  Kamloops / Thompson Nicola region: $85M – $210M / year", fs=9, gap=3)
        write(
            "Source: BC MCFD Annual Service Plan 2024-25. "
            "Projections based on documented per-family cost estimates. "
            "All figures based on publicly available BC government rates and published estimates. "
            "Actual costs may be significantly higher.",
            fs=7, gap=6, color=(0.5, 0.5, 0.5),
        )

    return doc.tobytes()


@router.get("/media-package")
async def export_media_package(db: AsyncSession = Depends(get_db), _: None = Depends(rate_limit_public)):
    """Return structured JSON media package for journalists and advocates."""
    contradiction_rows = (await db.execute(text("""
        SELECT id, claim, evidence, source_doc, severity, created_at
        FROM contradictions
        ORDER BY
            CASE severity WHEN 'DIRECT' THEN 0 WHEN 'PARTIAL' THEN 1 ELSE 2 END,
            created_at DESC
        LIMIT 5
    """))).all()

    cost_rows = (await db.execute(
        select(CostEntry).order_by(CostEntry.category, CostEntry.id)
    )).scalars().all()

    cost_total_row = (await db.execute(text("SELECT SUM(total) FROM cost_entries"))).one()
    cost_total = float(cost_total_row[0] or 0.0)

    timeline_rows = (await db.execute(text("""
        SELECT id, title, event_date, severity, description
        FROM timeline_events
        ORDER BY
            CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            event_date DESC
        LIMIT 8
    """))).all()

    by_category: dict = {}
    for r in cost_rows:
        by_category.setdefault(r.category, 0.0)
        by_category[r.category] += float(r.total or 0.0)

    return JSONResponse({
        "title": "THE MCFD FILES — Public Accountability Media Package",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_ref": "PC 19700 · PC 19709 · SC 64242 · SC 064851",
        "trial_date": TRIAL_DATE,
        "oipc_complaint": "Filed — FOI disclosure gap: 906 pages received vs. 1,792 pages disclosed to OIPC",
        "summary": {
            "documented_cost": cost_total,
            "documented_cost_formatted": f"${cost_total:,.2f}",
            "days_in_care": 214,
            "contradiction_count": len(contradiction_rows),
            "foi_page_gap": {"received": 906, "disclosed_to_oipc": 1792},
        },
        "key_personnel": [
            {"name": "Nicki Wolfenden", "role": "Social Worker", "file": "PC 19700"},
            {"name": "Tammy Newton", "role": "Team Leader", "file": "PC 19700"},
            {"name": "Jordon Muileboom", "role": "Acting Team Leader", "file": "PC 19700"},
            {"name": "Robyn Burnstein", "role": "Centralized Screening TL", "file": "PC 19700"},
        ],
        "top_contradictions": [
            {
                "id": r.id,
                "claim": r.claim,
                "evidence": r.evidence,
                "source_doc": r.source_doc,
                "severity": r.severity,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in contradiction_rows
        ],
        "cost_by_category": by_category,
        "scale_projection": {
            "bc_children": 5000,
            "bc_low": 1_425_000_000,
            "bc_high": 2_100_000_000,
            "bc_low_formatted": "$1.4B",
            "bc_high_formatted": "$2.1B",
            "kamloops_low": 85_000_000,
            "kamloops_high": 210_000_000,
            "source": "BC MCFD Annual Service Plan 2024-25",
        },
        "timeline_highlights": [
            {
                "id": r.id,
                "title": r.title,
                "event_date": str(r.event_date) if r.event_date else None,
                "severity": r.severity,
                "description": r.description,
            }
            for r in timeline_rows
        ],
        "foi_disclosure_gap": {
            "pages_received": 906,
            "pages_disclosed_to_oipc": 1792,
            "shortfall": 886,
            "oipc_complaint_filed": True,
        },
        "legal_basis": [
            "Freedom of Information and Protection of Privacy Act (FOIPPA) RSBC 1996 c.165",
            "Canadian Charter of Rights and Freedoms s.7 (life, liberty, security)",
            "Canadian Charter of Rights and Freedoms s.8 (unreasonable search and seizure)",
            "Canadian Charter of Rights and Freedoms s.15 (equality rights)",
            "Child, Family and Community Service Act (CFCSA) RSBC 1996 c.46",
        ],
        "disclaimer": (
            "All figures are based on publicly available BC government rates and published estimates. "
            "FOI documents are official government records. Contradictions identified by AI-assisted review "
            "of sworn statements and disclosed records. All claims verifiable against source documents."
        ),
    })


@router.get("/trial-report.pdf", dependencies=[Depends(require_api_key)])
async def export_trial_report_pdf(db: AsyncSession = Depends(get_db)):
    """Return court-submittable PDF trial evidence report."""
    TRIAL_DATE_OBJ = date(2026, 5, 19)
    days_to_trial = (TRIAL_DATE_OBJ - date.today()).days
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    today_filename = datetime.now(timezone.utc).strftime("%Y%m%d")

    foi_rows = (await db.execute(text("""
        SELECT c.id, c.text, c.citation, c.page_estimate, d.title
        FROM chunks c JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = 'foi' ORDER BY c.page_estimate NULLS LAST, c.id
    """))).all()

    contradiction_rows = (await db.execute(text("""
        SELECT id, claim, evidence, source_doc, severity, page_ref
        FROM contradictions ORDER BY id
    """))).all()

    personal_rows = (await db.execute(text("""
        SELECT c.id, c.text, c.citation, d.title
        FROM chunks c JOIN decisions d ON d.id = c.decision_id
        WHERE d.source = 'personal' ORDER BY c.id
    """))).all()

    counts_row = (await db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM decisions) as total_decisions,
            (SELECT COUNT(*) FROM chunks c JOIN decisions d ON d.id=c.decision_id WHERE d.source='foi') as foi_count,
            (SELECT COUNT(*) FROM contradictions) as contradiction_count,
            (SELECT COUNT(*) FROM chunks c JOIN decisions d ON d.id=c.decision_id WHERE d.source='personal') as personal_count
    """))).one()

    evidence_rows = (await db.execute(text("""
        SELECT ce.contradiction_id, ce.similarity_score,
               c.text, c.citation, c.page_estimate, d.source
        FROM contradiction_evidence ce
        JOIN chunks c ON c.id = ce.chunk_id
        JOIN decisions d ON d.id = c.decision_id
        ORDER BY ce.contradiction_id, ce.similarity_score DESC
    """))).all()

    evidence_by_contradiction: dict = {}
    for r in evidence_rows:
        ev_list = evidence_by_contradiction.setdefault(r.contradiction_id, [])
        if len(ev_list) < 3:
            ev_list.append(r)

    crossexam_rows = (await db.execute(text("""
        SELECT contradiction_id, questions_text
        FROM crossexam_questions
    """))).all()

    crossexam_by_contradiction: dict = {r.contradiction_id: r.questions_text for r in crossexam_rows}

    cost_rows = (await db.execute(
        select(CostEntry).order_by(CostEntry.category, CostEntry.id)
    )).scalars().all()
    cost_total = sum(r.total or 0.0 for r in cost_rows)

    pdf_bytes = _build_pdf_bytes(foi_rows, contradiction_rows, personal_rows, counts_row, days_to_trial, today_str, evidence_by_contradiction, crossexam_by_contradiction, cost_rows, cost_total)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="mcfd_trial_report_{today_filename}.pdf"'},
    )


def _build_caryma_brief_bytes(contradiction_rows, cost_total: float, today_str: str) -> bytes:
    W, H = 612, 792        # Letter portrait
    ML, MT, MR, MB = 60, 60, 60, 50
    TW = W - ML - MR       # 492pt

    doc = fitz.open()
    state = {"page": None, "y": 0, "n": 0}

    def _new_page():
        state["n"] += 1
        p = doc.new_page(width=W, height=H)
        state["page"] = p
        state["y"] = MT
        p.draw_rect(fitz.Rect(0, 0, W, 18), color=None, fill=(0.2, 0.1, 0.35))
        p.insert_text(
            (ML, H - 22),
            f"THE MCFD FILES — Caryma S'd Brief  |  PC 19700  —  Page {state['n']}",
            fontname="helv", fontsize=7, color=(0.5, 0.5, 0.5),
        )

    def _wrap(text: str, fs: int) -> list:
        max_c = max(1, int(TW / (fs * 0.55)))
        words = (text or "").split()
        lines, cur = [], []
        for word in words:
            if sum(len(w) for w in cur) + len(cur) + len(word) > max_c:
                lines.append(" ".join(cur))
                cur = [word]
            else:
                cur.append(word)
        if cur:
            lines.append(" ".join(cur))
        return lines or [""]

    def write(text: str, fs: int = 10, bold: bool = False, gap: int = 6, color=(0, 0, 0)):
        fn = "hebo" if bold else "helv"
        lh = fs + 3
        for line in _wrap(text, fs):
            if state["y"] + lh > H - MB - 30:
                _new_page()
            state["page"].insert_text((ML, state["y"]), line, fontname=fn, fontsize=fs, color=color)
            state["y"] += lh
        state["y"] += gap

    def rule():
        state["page"].draw_line((ML, state["y"]), (ML + TW, state["y"]), color=(0.6, 0.6, 0.6), width=0.5)
        state["y"] += 10

    _new_page()

    # ── Header bar text ──────────────────────────────────────────
    state["y"] = 30
    write("CARYMA S'D — CASE BRIEF", fs=16, bold=True, gap=4, color=(0.85, 0.85, 1.0))
    write(f"PC 19700  |  BC Provincial Court, Kamloops  |  Trial: May 19–21, 2026  |  {today_str}", fs=8, gap=10, color=(0.5, 0.5, 0.5))
    rule()

    # ── Section 1: Case Overview ─────────────────────────────────
    write("1. CASE OVERVIEW", fs=12, bold=True, gap=6)
    write("File: PC 19700 — LaPointe, Christopher  /  PC 19709  /  SC 64242  /  SC 064851", fs=9, gap=4)
    write("Child: Nadia LaPointe (minor, complex needs)", fs=9, gap=4)
    write("Pharmacogenomic profile: CYP2B6, CYP2C19, COMT, MTHFR (CEN4GEN patient D8146200CAN)", fs=9, gap=4)
    write("Removal date: August 7, 2025", fs=9, gap=4)
    write("Days in care at brief date: 214", fs=9, gap=4)
    write("OIPC complaint: INV-F-26-00220 (active — FOI disclosure gap)", fs=9, gap=4)
    write("Judicial review: SC 064851 — MCFD defaulted on response", fs=9, gap=4)
    write("Family court: SC 64242 — F5 counterclaim, 15 exhibits filed", fs=9, gap=4)
    write("Trial: May 19–21, 2026, BC Provincial Court, Kamloops, BC", fs=9, gap=4)
    write("Pro se applicant.", fs=9, gap=10)
    rule()

    # ── Section 2: Key Personnel ─────────────────────────────────
    write("2. KEY PERSONNEL", fs=12, bold=True, gap=6)
    write("SW:   Nicki Wolfenden  |  nicki.wolfenden@gov.bc.ca  |  250-319-1739", fs=9, gap=3)
    write("TL:   Tammy Newton", fs=9, gap=3)
    write("ATL:  Jordon Muileboom", fs=9, gap=3)
    write("Screening TL:  Robyn Burnstein (directed removal — never observed child — CFCSA s.30)", fs=9, gap=3)
    write("MCFD Counsel:  Cheryl Martin, Martin & Martin", fs=9, gap=3)
    write("Opp. Counsel:  Plessa Walden, PGS Law  |  pwalden@pgslaw.ca", fs=9, gap=3)
    state["y"] += 6
    rule()

    # ── Section 3: Top 3 Contradictions ──────────────────────────
    write(f"3. TOP CONTRADICTIONS BY SEVERITY  ({len(contradiction_rows)} shown)", fs=12, bold=True, gap=6)
    for i, r in enumerate(contradiction_rows, 1):
        sev = f"[{r.severity}]" if r.severity else "[UNKNOWN]"
        write(f"  {i}. {sev}  {(r.claim or '')[:160]}", fs=9, gap=3)
        if r.evidence:
            write(f"     Contradicted by: {r.evidence[:160]}", fs=8, gap=3, color=(0.35, 0.35, 0.35))
        if r.source_doc:
            src = r.source_doc + (f"  ·  p.{r.page_ref}" if r.page_ref else "")
            write(f"     Source: {src}", fs=8, gap=5, color=(0.45, 0.45, 0.45))
    state["y"] += 4
    rule()

    # ── Section 4: FOI Disclosure Gap ────────────────────────────
    write("4. FOI DISCLOSURE GAP", fs=12, bold=True, gap=6)
    write("Represented to OIPC:          1,792 pages", fs=9, gap=3)
    write("Received by LaPointe:           906 pages", fs=9, gap=3)
    write("Internal stamp count (est.):  ~1,235 pages", fs=9, gap=3)
    write("Unaccounted:                    886 pages", fs=9, gap=4)
    write("Missing document: September 8, 2025 Wolfenden email (not in FOI disclosure)", fs=9, gap=4)
    write("OIPC file: INV-F-26-00220  |  Response pending.", fs=9, gap=10)
    rule()

    # ── Section 5: FOIPPA Breach ──────────────────────────────────
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    write("5. FOIPPA BREACH — NW / DOLSON", fs=12, bold=True, gap=6)
    write(f"Date of record: {today_date}", fs=9, gap=4)
    write(
        "SW Wolfenden shared LaPointe personal contact information with Robb Dolson RCC "
        "(Centre for Dignity, Kamloops) without consent or request from Dolson. "
        "Voicemail preserved. Wolfenden was on approved leave at time of sharing. "
        "Contact was shared on the first day leave ended.",
        fs=9, gap=4
    )
    write("Statute: FOIPPA RSBC 1996 c.165 ss.33–39 (unauthorized disclosure of personal information)", fs=9, gap=10)
    rule()

    # ── Section 6: Taxpayer Cost ─────────────────────────────────
    write("6. DOCUMENTED TAXPAYER COST", fs=12, bold=True, gap=6)
    write(f"Documented total (live from DB):  ${cost_total:,.2f}", fs=11, bold=True, gap=4, color=(0.7, 0.1, 0.1))
    write("Basis: BC government-published rates. One case. 214 days.", fs=9, gap=4)
    write("Estimated true cost: $285,000 – $420,000  |  BC-wide (5,000 children): $1.4B – $2.1B / year", fs=9, gap=10)
    rule()

    # ── Section 7: Statutory Violations ──────────────────────────
    write("7. STATUTORY VIOLATIONS ALLEGED", fs=12, bold=True, gap=6)
    for statute in [
        "CFCSA RSBC 1996 c.46 s.30    — Removal directed by Burnstein without observing child",
        "FOIPPA RSBC 1996 c.165 ss.33–39 — Unauthorized disclosure (Wolfenden, Mar 9 2026)",
        "Charter s.7                  — Life, liberty, security of the person",
        "Charter s.2(b)               — Freedom of expression",
        "Charter s.8                  — Unreasonable search and seizure",
        "Charter s.15                 — Equality rights (disability / neurodivergent child)",
        "Mental Health Act RSBC 1996 c.288 s.96 — Pre-removal misuse",
    ]:
        write(f"  • {statute}", fs=9, gap=3)
    state["y"] += 6
    rule()

    # ── Section 8: Evidence Inventory ────────────────────────────
    write("8. EVIDENCE INVENTORY", fs=12, bold=True, gap=6)
    for item in [
        "27-min continuous video — August 7, 2025 (contradicts Form F1)",
        "FOI file CFD-2025-53478 (906 pages, OCR'd, indexed — 23+ contradictions identified)",
        "CEN4GEN genetic analysis — patient D8146200CAN",
        "OT Sheila Branscombe report — July 29, 2025",
        "Audio recording: Newton supervised visit — August 21, 2025",
        "Newton letter: September 24, 2025 (unsubstantiated allegations)",
        "F5 counterclaim SC 64242 — 15 exhibits filed",
        "SC 064851 judicial review — MCFD defaulted on response",
        "Taxpayer cost: $175,041.32 / 214 days (all line items cited to BC gov rates)",
        "OIPC complaint INV-F-26-00220 — active",
    ]:
        write(f"  • {item}", fs=9, gap=3)
    state["y"] += 8
    rule()

    # ── Footer note ──────────────────────────────────────────────
    write(
        "This brief is prepared for counsel Caryma S'd. All figures are based on publicly available "
        "BC government rates and FOI-disclosed records. Pro Patria.",
        fs=8, gap=6, color=(0.4, 0.4, 0.4)
    )

    # ── SHA-256 two-pass footer ───────────────────────────────────
    draft_bytes = doc.tobytes()
    sha = hashlib.sha256(draft_bytes).hexdigest()[:16]

    doc2 = fitz.open(stream=draft_bytes, filetype="pdf")
    last_page = doc2[-1]
    last_page.insert_text(
        (ML, H - 34),
        f"SHA-256: {sha}...  |  Generated: {today_str}  |  ALL FIGURES CITED TO PUBLIC RECORD",
        fontname="helv", fontsize=7, color=(0.5, 0.5, 0.5),
    )
    return doc2.tobytes()


@router.get("/caryma-brief.pdf")
async def export_caryma_brief(db: AsyncSession = Depends(get_db), _: None = Depends(rate_limit_public)):
    """Public PDF brief for counsel — no auth required."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    contradiction_rows = (await db.execute(text("""
        SELECT id, claim, evidence, source_doc, severity, page_ref
        FROM contradictions
        ORDER BY
            CASE severity WHEN 'DIRECT' THEN 0 WHEN 'PARTIAL' THEN 1 ELSE 2 END
        LIMIT 3
    """))).all()

    cost_total_row = (await db.execute(text("SELECT COALESCE(SUM(total), 0) FROM cost_entries"))).one()
    cost_total = float(cost_total_row[0])

    pdf_bytes = _build_caryma_brief_bytes(contradiction_rows, cost_total, today_str)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="caryma-brief.pdf"'},
    )
