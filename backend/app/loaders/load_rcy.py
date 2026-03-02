"""Load RCY PDF reports into the decisions table.

Reads every .meta.json file from data/raw/rcy/, extracts text from the
companion PDF using PyMuPDF, then upserts into the decisions table.

RCY reports use source='rcy'. court and citation are left NULL since these
are government reports, not court decisions. The existing FTS search endpoint
covers them automatically.

Usage
-----
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.loaders.load_rcy

  # Dry run (no DB writes):
  ... --dry-run

  # Custom data dir:
  ... --data-dir data/raw/rcy
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import Decision  # noqa: F401 — registers with Base.metadata
from app.database import init_db, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data/raw/rcy")


def extract_text(pdf_path: Path) -> str:
    """Extract plain text from a PDF using PyMuPDF.

    Tries get_text() first; falls back to blocks extraction if a page yields
    no text (e.g. scanned image pages where layout analysis differs).
    """
    try:
        doc = fitz.open(str(pdf_path))
        pages = []
        for page in doc:
            text = page.get_text()
            if not text.strip():
                # Fallback: blocks returns (x0,y0,x1,y1,text,block_no,type)
                blocks = page.get_text("blocks")
                text = "\n".join(b[4] for b in blocks if isinstance(b[4], str) and b[4].strip())
            pages.append(text)
        doc.close()
        return "\n".join(pages).strip()
    except Exception as exc:
        log.warning("PDF extraction failed for %s: %s", pdf_path.name, exc)
        return ""


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return date.fromisoformat(val[:10])
    except (ValueError, TypeError):
        return None


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def build_record(meta_path: Path) -> dict | None:
    """Read a .meta.json and its companion PDF, return a DB record dict."""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Bad meta JSON %s: %s", meta_path.name, exc)
        return None

    url = meta.get("url", "").strip()
    if not url:
        log.warning("No URL in %s — skipping", meta_path.name)
        return None

    filename = meta.get("filename", "")
    pdf_path = meta_path.parent / filename
    if not pdf_path.exists():
        log.warning("PDF not found: %s — skipping", pdf_path)
        return None

    log.info("Extracting text: %s", filename)
    full_text = extract_text(pdf_path)
    if not full_text:
        log.warning("  No text extracted from %s", filename)

    return {
        "source": "rcy",
        "title": meta.get("title", filename),
        "citation": None,
        "date": _parse_date(meta.get("date")),
        "court": None,
        "url": url,
        "snippet": None,
        "full_text": full_text or None,
        "scraped_at": _parse_dt(meta.get("scraped_at")),
    }


async def load(data_dir: Path, dry_run: bool = False) -> None:
    meta_files = sorted(data_dir.glob("*.meta.json"))
    log.info("Found %d .meta.json files in %s", len(meta_files), data_dir)

    if not meta_files:
        log.error("No .meta.json files found — run the RCY scraper first.")
        return

    records = []
    for mf in meta_files:
        rec = build_record(mf)
        if rec:
            records.append(rec)

    log.info(
        "Built %d records (%d skipped)",
        len(records),
        len(meta_files) - len(records),
    )

    # Deduplicate by URL — prefer the record with more extracted text
    seen: dict[str, dict] = {}
    for rec in records:
        url = rec["url"]
        existing = seen.get(url)
        if existing is None:
            seen[url] = rec
        else:
            existing_len = len(existing.get("full_text") or "")
            new_len = len(rec.get("full_text") or "")
            if new_len > existing_len:
                seen[url] = rec
    records = list(seen.values())
    log.info("After dedup: %d unique URLs", len(records))

    if dry_run:
        log.info("Dry run — not writing to DB.")
        chars = sum(len(r["full_text"] or "") for r in records)
        log.info("Total text chars: %s", f"{chars:,}")
        return

    # Create tables
    await init_db()

    # Upsert: on URL conflict update all fields (re-extraction may improve text)
    BATCH = 50  # smaller batches — full_text can be large
    upserted = 0

    async with SessionLocal() as session:
        for i in range(0, len(records), BATCH):
            batch = records[i : i + BATCH]
            stmt = pg_insert(Decision).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["url"],
                set_={
                    "title": stmt.excluded.title,
                    "date": stmt.excluded.date,
                    "full_text": stmt.excluded.full_text,
                    "scraped_at": stmt.excluded.scraped_at,
                },
            )
            result = await session.execute(stmt)
            await session.commit()
            upserted += result.rowcount
            log.info(
                "Batch %d/%d — %d rows upserted so far",
                i // BATCH + 1,
                -(-len(records) // BATCH),
                upserted,
            )

    log.info("Done. %d RCY rows upserted.", upserted)

    # Sanity check
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM decisions WHERE source = 'rcy'")
        )
        count = result.scalar()
        log.info("decisions table: %d RCY rows total.", count)

        result = await session.execute(text("SELECT COUNT(*) FROM decisions"))
        total = result.scalar()
        log.info("decisions table: %d rows total (all sources).", total)


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract text from RCY PDFs and load into decisions table"
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"Directory containing .meta.json files (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract text but do not write to DB",
    )
    args = parser.parse_args()

    await load(Path(args.data_dir), dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(_main())
