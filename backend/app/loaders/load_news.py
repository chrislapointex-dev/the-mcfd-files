"""Load scraped news articles into the decisions table.

Reads every .json file from data/raw/news/ (skipping manifest.json),
then upserts into the decisions table.

News articles use source='news'. citation holds the source domain.
court and date are left NULL.

Usage:
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.loaders.load_news

  # Dry run (no DB writes):
  ... --dry-run
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime
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

DEFAULT_DATA_DIR = Path("data/raw/news")
BATCH = 100


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def build_record(json_path: Path) -> dict | None:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Bad JSON %s: %s", json_path.name, exc)
        return None

    url = data.get("url", "").strip()
    if not url:
        log.warning("No URL in %s — skipping", json_path.name)
        return None

    title = data.get("title", "").strip() or url
    full_text = data.get("full_text", "").strip() or None
    snippet = data.get("snippet", "").strip() or (full_text or "")[:300] or None

    return {
        "source": "news",
        "title": title,
        "citation": data.get("domain", "").strip() or None,
        "date": None,
        "court": None,
        "url": url,
        "snippet": snippet,
        "full_text": full_text,
        "scraped_at": _parse_dt(data.get("scraped_at")),
    }


async def load(data_dir: Path, dry_run: bool = False) -> None:
    json_files = [
        f for f in sorted(data_dir.glob("*.json"))
        if f.name != "manifest.json"
    ]
    log.info("Found %d article files in %s", len(json_files), data_dir)

    if not json_files:
        log.error("No article files found — run the news scraper first.")
        return

    records = []
    for jf in json_files:
        rec = build_record(jf)
        if rec:
            records.append(rec)

    log.info("Built %d records (%d skipped)", len(records), len(json_files) - len(records))

    # Deduplicate by URL
    seen: dict[str, dict] = {}
    for rec in records:
        seen[rec["url"]] = rec
    records = list(seen.values())
    log.info("After dedup: %d unique URLs", len(records))

    if dry_run:
        log.info("Dry run — not writing to DB.")
        chars = sum(len(r["full_text"] or "") for r in records)
        log.info("Total text chars: %s", f"{chars:,}")
        return

    await init_db()

    upserted = 0
    async with SessionLocal() as session:
        for i in range(0, len(records), BATCH):
            batch = records[i: i + BATCH]
            stmt = pg_insert(Decision).values(batch)
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
            upserted += result.rowcount

    log.info("Done. %d news rows upserted.", upserted)

    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM decisions WHERE source = 'news'")
        )
        log.info("decisions table: %d news rows total.", result.scalar())
        result = await session.execute(text("SELECT COUNT(*) FROM decisions"))
        log.info("decisions table: %d rows total (all sources).", result.scalar())


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Load scraped news articles into the decisions table"
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"Directory containing article JSON files (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse records but do not write to DB",
    )
    args = parser.parse_args()
    await load(Path(args.data_dir), dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(_main())
