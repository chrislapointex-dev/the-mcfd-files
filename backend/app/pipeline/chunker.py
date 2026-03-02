"""Split decision full_text into overlapping chunks and store in the chunks table.

Chunking strategy:
  - Target ~500 words per chunk, ~50-word overlap with the previous chunk
  - Splits on paragraph boundaries (double newlines) first, then sentence
    boundaries, so we never cut mid-sentence
  - Each chunk records: decision_id, chunk_num, text, citation, page_estimate
  - page_estimate = rough page number based on ~250 words/page

Resumable: skips decisions that already have at least one chunk row.

Usage:
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.pipeline.chunker

  # Limit to first N decisions (testing):
  ... --limit 10

  # Re-process a specific decision:
  ... --decision-id 42

  # Dry run (no DB writes):
  ... --dry-run
"""

import argparse
import asyncio
import logging
import re
import time
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import init_db, SessionLocal
from app.models import Chunk, Decision  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────────────

TARGET_WORDS = 500
OVERLAP_WORDS = 50
WORDS_PER_PAGE = 250   # rough estimate for page_estimate field
BATCH_SIZE = 50        # decisions to process per DB commit batch


# ── Text splitting ─────────────────────────────────────────────────────────────


def _split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; remove empty/whitespace-only paragraphs."""
    paras = re.split(r"\n{2,}", text)
    return [p.strip() for p in paras if p.strip()]


def _word_count(s: str) -> int:
    return len(s.split())


def make_chunks(full_text: str) -> list[str]:
    """Split full_text into overlapping chunks respecting paragraph boundaries.

    Returns a list of chunk strings.
    """
    paragraphs = _split_paragraphs(full_text)
    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []       # paragraphs in the current chunk
    current_words = 0
    overlap_buffer: list[str] = []  # paragraphs kept for overlap

    for para in paragraphs:
        pw = _word_count(para)

        # If a single paragraph exceeds target, split it at sentence boundaries
        if pw > TARGET_WORDS * 1.5:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sent in sentences:
                sw = _word_count(sent)
                if current_words + sw > TARGET_WORDS and current:
                    chunks.append(" ".join(current))
                    # Overlap: keep last OVERLAP_WORDS worth of sentences
                    overlap: list[str] = []
                    overlap_words = 0
                    for s in reversed(current):
                        if overlap_words + _word_count(s) > OVERLAP_WORDS:
                            break
                        overlap.insert(0, s)
                        overlap_words += _word_count(s)
                    current = overlap + [sent]
                    current_words = sum(_word_count(s) for s in current)
                else:
                    current.append(sent)
                    current_words += sw
            continue

        if current_words + pw > TARGET_WORDS and current:
            chunks.append("\n\n".join(current))
            # Build overlap from end of current chunk
            overlap = []
            overlap_words = 0
            for p in reversed(current):
                if overlap_words + _word_count(p) > OVERLAP_WORDS:
                    break
                overlap.insert(0, p)
                overlap_words += _word_count(p)
            current = overlap + [para]
            current_words = overlap_words + pw
        else:
            current.append(para)
            current_words += pw

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def build_chunk_records(decision: Decision) -> list[dict]:
    """Convert one Decision into a list of Chunk insert dicts."""
    full_text = (decision.full_text or "").strip()
    if not full_text:
        return []

    texts = make_chunks(full_text)
    records = []
    cumulative_words = 0

    for i, chunk_text in enumerate(texts):
        page_estimate = max(1, cumulative_words // WORDS_PER_PAGE + 1)
        records.append({
            "decision_id": decision.id,
            "chunk_num": i,
            "text": chunk_text,
            "citation": decision.citation,
            "page_estimate": page_estimate,
        })
        cumulative_words += _word_count(chunk_text)

    return records


# ── DB helpers ────────────────────────────────────────────────────────────────


async def _already_chunked_ids(db) -> set[int]:
    """Return the set of decision_ids that already have chunk rows."""
    result = await db.execute(
        text("SELECT DISTINCT decision_id FROM chunks")
    )
    return {row[0] for row in result.all()}


async def _upsert_chunks(db, records: list[dict]) -> int:
    """Insert chunks, skipping any that conflict on (decision_id, chunk_num)."""
    if not records:
        return 0
    stmt = pg_insert(Chunk).values(records)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["decision_id", "chunk_num"]
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


# ── Main pipeline ─────────────────────────────────────────────────────────────


async def run(
    limit: int | None = None,
    decision_id: int | None = None,
    dry_run: bool = False,
) -> None:
    await init_db()

    async with SessionLocal() as db:
        # Build query for decisions that have full_text
        stmt = (
            select(Decision)
            .where(Decision.full_text.isnot(None))
            .where(Decision.full_text != "")
            .order_by(Decision.id)
        )
        if decision_id is not None:
            stmt = stmt.where(Decision.id == decision_id)
        if limit is not None:
            stmt = stmt.limit(limit)

        decisions = (await db.execute(stmt)).scalars().all()
        log.info("Found %d decisions with full_text", len(decisions))

        # Skip already-chunked decisions (unless re-processing a specific id)
        if decision_id is None:
            done = await _already_chunked_ids(db)
            pending = [d for d in decisions if d.id not in done]
            log.info(
                "%d already chunked, %d pending",
                len(decisions) - len(pending),
                len(pending),
            )
        else:
            pending = list(decisions)

        if not pending:
            log.info("Nothing to do.")
            return

        if dry_run:
            log.info("Dry run — showing stats for first 3 decisions:")
            for d in pending[:3]:
                chunks = make_chunks(d.full_text or "")
                words = _word_count(d.full_text or "")
                log.info(
                    "  [%d] %s — %d words → %d chunks",
                    d.id, d.citation or "?", words, len(chunks),
                )
                for i, c in enumerate(chunks):
                    log.info("    chunk %d: %d words", i, _word_count(c))
            return

        # Process in batches
        t0 = time.monotonic()
        total_chunks = 0
        batch_records: list[dict] = []

        for idx, decision in enumerate(pending, 1):
            records = build_chunk_records(decision)
            batch_records.extend(records)

            if len(batch_records) >= BATCH_SIZE * 10 or idx == len(pending):
                inserted = await _upsert_chunks(db, batch_records)
                total_chunks += inserted
                batch_records = []

            if idx % 50 == 0 or idx == len(pending):
                elapsed = time.monotonic() - t0
                rate = idx / elapsed
                log.info(
                    "  %d/%d decisions  |  %d chunks  |  %.1f dec/s",
                    idx, len(pending), total_chunks, rate,
                )

        log.info("Done. %d chunks inserted across %d decisions.", total_chunks, len(pending))

        # Verification summary
        result = await db.execute(text("SELECT COUNT(*) FROM chunks"))
        log.info("chunks table total: %d rows", result.scalar())

        result = await db.execute(
            text("SELECT COUNT(DISTINCT decision_id) FROM chunks")
        )
        log.info("Decisions with chunks: %d", result.scalar())

        result = await db.execute(
            text("SELECT AVG(char_length(text)) FROM chunks")
        )
        log.info("Avg chunk length: %d chars", int(result.scalar() or 0))


# ── Entry point ───────────────────────────────────────────────────────────────


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk decision full_text into the chunks table"
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only N decisions")
    parser.add_argument("--decision-id", type=int, default=None, help="Re-process one decision")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without writing")
    args = parser.parse_args()
    await run(limit=args.limit, decision_id=args.decision_id, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(_main())
