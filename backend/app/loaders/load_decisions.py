"""Load scraped JSON decision files into the PostgreSQL database.

Usage
-----
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.loaders.load_decisions

  # Dry run (no writes):
  ... --dry-run

  # Custom data dir:
  ... --data-dir data/raw/bccourts/bccourts
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Import models BEFORE init_db so Base.metadata sees the Decision table
from app.models import Decision  # noqa: F401
from app.database import init_db, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data/raw/bccourts/bccourts")


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


def _load_record(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Bad JSON %s: %s", path.name, exc)
        return None

    url = data.get("url", "").strip()
    if not url:
        log.warning("No URL in %s — skipping", path.name)
        return None

    return {
        "source": data.get("source", "bccourts"),
        "title": data.get("title", "") or "",
        "citation": data.get("citation") or None,
        "date": _parse_date(data.get("date")),
        "court": data.get("court") or None,
        "url": url,
        "snippet": data.get("snippet") or None,
        "full_text": data.get("full_text") or None,
        "scraped_at": _parse_dt(data.get("scraped_at")),
    }


async def load(data_dir: Path, dry_run: bool = False) -> None:
    files = sorted(data_dir.glob("*.json"))
    log.info("Found %d JSON files in %s", len(files), data_dir)

    if not files:
        log.error("No JSON files found — check --data-dir path")
        return

    # Create tables
    await init_db()

    # Enable pgvector extension (idempotent)
    async with SessionLocal() as session:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await session.commit()

    records = []
    for path in files:
        rec = _load_record(path)
        if rec:
            records.append(rec)

    log.info("Parsed %d valid records (skipped %d)", len(records), len(files) - len(records))

    # Deduplicate by URL — prefer records with full_text
    seen: dict[str, dict] = {}
    for rec in records:
        url = rec["url"]
        if url not in seen or (rec["full_text"] and not seen[url]["full_text"]):
            seen[url] = rec
    records = list(seen.values())
    log.info("After dedup: %d unique URLs", len(records))

    if dry_run:
        log.info("Dry run — not writing to DB")
        return

    # Bulk upsert: on URL conflict, update fields (prefer records with full_text)
    BATCH = 200
    inserted = 0
    updated = 0

    async with SessionLocal() as session:
        for i in range(0, len(records), BATCH):
            batch = records[i : i + BATCH]
            stmt = pg_insert(Decision).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["url"],
                set_={
                    "title": stmt.excluded.title,
                    "citation": stmt.excluded.citation,
                    "date": stmt.excluded.date,
                    "court": stmt.excluded.court,
                    "snippet": stmt.excluded.snippet,
                    "full_text": stmt.excluded.full_text,
                    "scraped_at": stmt.excluded.scraped_at,
                },
            )
            result = await session.execute(stmt)
            await session.commit()
            # rowcount = rows affected (inserted + updated)
            inserted += result.rowcount
            log.info(
                "Batch %d/%d — %d rows affected so far",
                i // BATCH + 1,
                -(-len(records) // BATCH),
                inserted,
            )

    log.info("Done. %d rows upserted into decisions table.", inserted)

    # Quick sanity check
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM decisions"))
        count = result.scalar()
        log.info("decisions table now has %d rows.", count)


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Load scraped decisions into PostgreSQL")
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"Directory of JSON files (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse files but do not write to DB",
    )
    args = parser.parse_args()

    await load(Path(args.data_dir), dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(_main())
