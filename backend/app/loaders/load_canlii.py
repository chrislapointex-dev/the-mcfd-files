"""Load scraped CanLII JSON files into the decisions table.

CanLII files are organised as data/raw/canlii/{db_id}/{case_id}.json.
This loader walks the tree recursively, parses each file, and upserts
into the decisions table using the URL as the unique key.

Fields from the scraper:
    citation, title, date, court, database_id, case_id, judge,
    url, full_text, scraped_at

The judge name (when present) is stored in the snippet column as
"Judge: <name>" since the decisions table has no dedicated judge column.

Usage
-----
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.loaders.load_canlii

  # Dry run (no DB writes):
  ... --dry-run

  # Custom data dir:
  ... --data-dir data/raw/canlii
"""

import argparse
import asyncio
import json
import logging
from datetime import date, datetime
from pathlib import Path

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

DEFAULT_DATA_DIR = Path("data/raw/canlii")

BATCH = 50  # smaller batches — full_text can be large


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

    judge = (data.get("judge") or "").strip()
    snippet = f"Judge: {judge}" if judge else None

    return {
        "source": "canlii",
        "title": data.get("title", "") or "",
        "citation": data.get("citation") or None,
        "date": _parse_date(data.get("date")),
        "court": data.get("court") or None,
        "url": url,
        "snippet": snippet,
        "full_text": data.get("full_text") or None,
        "scraped_at": _parse_dt(data.get("scraped_at")),
    }


async def load(data_dir: Path, dry_run: bool = False) -> None:
    # Recursive glob — files live in subdirs by database_id
    files = sorted(data_dir.glob("**/*.json"))
    log.info("Found %d JSON files under %s", len(files), data_dir)

    if not files:
        log.error("No JSON files found — run the CanLII scraper first.")
        return

    records = []
    for path in files:
        rec = _load_record(path)
        if rec:
            records.append(rec)

    log.info(
        "Parsed %d valid records (%d skipped)",
        len(records),
        len(files) - len(records),
    )

    # Deduplicate by URL — prefer the record with more text
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

    upserted = 0

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
            upserted += result.rowcount
            log.info(
                "Batch %d/%d — %d rows upserted so far",
                i // BATCH + 1,
                -(-len(records) // BATCH),
                upserted,
            )

    log.info("Done. %d CanLII rows upserted.", upserted)

    # Sanity check
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM decisions WHERE source = 'canlii'")
        )
        count = result.scalar()
        log.info("decisions table: %d CanLII rows total.", count)

        result = await session.execute(text("SELECT COUNT(*) FROM decisions"))
        total = result.scalar()
        log.info("decisions table: %d rows total (all sources).", total)


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Load scraped CanLII JSON files into the decisions table"
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"Root directory of CanLII JSON files (default: {DEFAULT_DATA_DIR})",
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
