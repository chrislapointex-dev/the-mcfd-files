"""Load parsed BC legislation JSON into the decisions table.

Reads every .json file from data/raw/legislation/, converts each section
element into a decisions row, then upserts into the DB.

Each section becomes:
  source      = "legislation"
  title       = "{ABBR} s.{number} — {heading truncated}"
  citation    = "{ABBR} s.{number}"  e.g. "CFCSA s.30"
  url         = "{statute_url}#s{number}"   (unique per section)
  full_text   = section full_text
  snippet     = first 300 chars of full_text
  court/date  = NULL (legislation, not a court decision)

Usage:
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.loaders.load_legislation

  # Dry run:
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

DEFAULT_DATA_DIR = Path("data/raw/legislation")

# Short abbreviations for each statute file
ABBR = {
    "cfcsa": "CFCSA",
    "rcya": "RCYA",
}

BATCH = 100


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def build_records(json_path: Path) -> list[dict]:
    """Convert one legislation JSON file into a list of DB record dicts."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Bad JSON %s: %s", json_path.name, exc)
        return []

    statute_id = json_path.stem                      # e.g. "cfcsa"
    abbr = ABBR.get(statute_id, statute_id.upper())  # e.g. "CFCSA"
    statute_url = data.get("url", "")
    scraped_at = _parse_dt(data.get("scraped_at"))

    records = []
    for el in data.get("elements", []):
        if el.get("type") != "section":
            continue

        num = el.get("number", "")
        heading = el.get("heading", "").strip()
        full_text = el.get("full_text", "").strip() or None

        # Truncate heading for title field
        heading_short = heading[:180] + "…" if len(heading) > 180 else heading
        title = f"{abbr} s.{num}"
        if heading_short:
            title = f"{abbr} s.{num} — {heading_short}"

        citation = f"{abbr} s.{num}"
        url = f"{statute_url}#s{num}"
        snippet = (full_text or "")[:300] or None

        records.append({
            "source": "legislation",
            "title": title,
            "citation": citation,
            "date": None,
            "court": None,
            "url": url,
            "snippet": snippet,
            "full_text": full_text,
            "scraped_at": scraped_at,
        })

    log.info(
        "  %s (%s): %d sections",
        data.get("title", statute_id),
        abbr,
        len(records),
    )
    return records


async def load(data_dir: Path, dry_run: bool = False) -> None:
    json_files = sorted(data_dir.glob("*.json"))
    log.info("Found %d JSON files in %s", len(json_files), data_dir)

    if not json_files:
        log.error("No JSON files found — run the legislation scraper first.")
        return

    all_records: list[dict] = []
    for jf in json_files:
        all_records.extend(build_records(jf))

    log.info("Total sections to load: %d", len(all_records))

    # Deduplicate by URL (shouldn't happen, but be safe)
    seen: dict[str, dict] = {}
    for rec in all_records:
        seen[rec["url"]] = rec
    records = list(seen.values())
    if len(records) < len(all_records):
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
                    "citation": stmt.excluded.citation,
                    "full_text": stmt.excluded.full_text,
                    "snippet": stmt.excluded.snippet,
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

    log.info("Done. %d legislation rows upserted.", upserted)

    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM decisions WHERE source = 'legislation'")
        )
        log.info("decisions table: %d legislation rows total.", result.scalar())
        result = await session.execute(text("SELECT COUNT(*) FROM decisions"))
        log.info("decisions table: %d rows total (all sources).", result.scalar())


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Load parsed BC legislation into the decisions table"
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"Directory containing legislation JSON files (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and count records but do not write to DB",
    )
    args = parser.parse_args()
    await load(Path(args.data_dir), dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(_main())
