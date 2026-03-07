"""Load a single personal legal file into the decisions table.

Handles .txt (read directly) and .pdf (via PyMuPDF if available).
Uses source='personal' by default; source='foi' also works.
The url field is the idempotency key — safe to re-run.

Usage
-----
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.loaders.load_personal_file \\
    --file data/raw/personal/wolfenden-form-f1-aug12.txt \\
    --label "Form F1 Wolfenden Aug12" \\
    --source personal \\
    --date 2025-08-12

After loading: run the chunker + embedder as normal.
"""

import argparse
import asyncio
import logging
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


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == '.txt':
        return path.read_text(encoding='utf-8')
    if suffix == '.pdf':
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise RuntimeError(
                "PyMuPDF is required to load PDF files. "
                "Install it: pip install pymupdf"
            )
        doc = fitz.open(str(path))
        pages = [page.get_text() for page in doc]
        doc.close()
        text = "\n".join(pages)
        if len(text.strip()) < 100:
            raise RuntimeError(
                f"PDF text extraction yielded < 100 chars for {path.name}. "
                "The file may be a scanned image. Convert to text first."
            )
        return text
    raise RuntimeError(
        f"Unsupported file type: {suffix}. Only .txt and .pdf are supported."
    )


async def load(file_path: Path, label: str, source: str, file_date: date, dry_run: bool = False) -> None:
    if not file_path.exists():
        log.error("File not found: %s", file_path)
        return

    log.info("Reading %s", file_path)
    full_text = _extract_text(file_path)
    log.info("Extracted %d chars from %s", len(full_text), file_path.name)

    url = f"{source}://{label.replace(' ', '-').lower()}/{file_path.name}"
    record = {
        "source": source,
        "title": label,
        "citation": label,
        "date": file_date,
        "court": None,
        "url": url,
        "snippet": full_text[:300].strip(),
        "full_text": full_text,
        "scraped_at": datetime.now(timezone.utc),
    }

    if dry_run:
        log.info("[dry-run] Would upsert: %s → %s (%d chars)", label, url, len(full_text))
        log.info("Dry run — not writing to DB")
        return

    await init_db()

    async with SessionLocal() as session:
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await session.commit()

    async with SessionLocal() as session:
        stmt = pg_insert(Decision).values([record])
        stmt = stmt.on_conflict_do_update(
            index_elements=["url"],
            set_={
                "title": stmt.excluded.title,
                "full_text": stmt.excluded.full_text,
                "snippet": stmt.excluded.snippet,
                "scraped_at": stmt.excluded.scraped_at,
            },
        )
        await session.execute(stmt)
        await session.commit()

    log.info("Loaded %s → %s", label, url)
    log.info("Next steps: run chunker + embedder to make this file searchable.")


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Load a personal legal file into the decisions table")
    parser.add_argument("--file", required=True, help="Path to .txt or .pdf file")
    parser.add_argument("--label", required=True, help="Human-readable document name (used as title + citation)")
    parser.add_argument("--source", default="personal", help="Source tag: 'personal' or 'foi' (default: personal)")
    parser.add_argument("--date", required=True, help="Document date YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="Parse but do not write to DB")
    args = parser.parse_args()

    file_path = Path(args.file)
    file_date = date.fromisoformat(args.date)
    await load(file_path, args.label, args.source, file_date, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(_main())
