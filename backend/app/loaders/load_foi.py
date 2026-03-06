"""Load FOI file CFD-2025-53478 OCR chunks into the PostgreSQL decisions table.

Each .txt file in data/raw/foi/ becomes one Decision row with source='foi'.
The existing chunker + embedder pipeline handles the rest.

Usage
-----
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.loaders.load_foi

  # Dry run:
  ... --dry-run

  # Custom data dir:
  ... --data-dir data/raw/foi
"""

import argparse
import asyncio
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import Decision  # noqa: F401
from app.database import init_db, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data/raw/foi")
FOI_NUMBER = "CFD-2025-53478"
FOI_DATE = date(2026, 2, 13)  # date of FOI response letter


def _page_range_from_filename(name: str) -> str:
    """Extract 'XXXX-XXXX' from 'foi_pages_0001_to_0050.txt'."""
    m = re.search(r"(\d+)_to_(\d+)", name)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):04d}"
    return name


def _load_record(path: Path) -> dict:
    text_content = path.read_text(encoding="utf-8")
    page_range = _page_range_from_filename(path.stem)
    return {
        "source": "foi",
        "title": f"FOI {FOI_NUMBER} — Pages {page_range}",
        "citation": FOI_NUMBER,
        "date": FOI_DATE,
        "court": None,
        "url": f"foi://{FOI_NUMBER}/pages-{page_range}",
        "snippet": text_content[:300].strip(),
        "full_text": text_content,
        "scraped_at": datetime.now(timezone.utc),
    }


async def load(data_dir: Path, dry_run: bool = False) -> None:
    files = sorted(data_dir.glob("foi_pages_*.txt"))
    log.info("Found %d FOI chunk files in %s", len(files), data_dir)

    if not files:
        log.error("No foi_pages_*.txt files found — check --data-dir path")
        return

    records = [_load_record(f) for f in files]
    log.info("Parsed %d records", len(records))

    if dry_run:
        for r in records:
            log.info("  [dry-run] %s (%d chars)", r["title"], len(r["full_text"]))
        log.info("Dry run — not writing to DB")
        return

    await init_db()

    async with SessionLocal() as session:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await session.commit()

    async with SessionLocal() as session:
        stmt = pg_insert(Decision).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["url"],
            set_={
                "title": stmt.excluded.title,
                "full_text": stmt.excluded.full_text,
                "snippet": stmt.excluded.snippet,
                "scraped_at": stmt.excluded.scraped_at,
            },
        )
        result = await session.execute(stmt)
        await session.commit()
        log.info("Upserted %d rows into decisions table.", result.rowcount)

    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM decisions WHERE source = 'foi'")
        )
        log.info("decisions table now has %d foi rows.", result.scalar())


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Load FOI chunks into PostgreSQL")
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"Directory of foi_pages_*.txt files (default: {DEFAULT_DATA_DIR})",
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
