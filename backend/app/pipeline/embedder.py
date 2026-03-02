"""Generate embeddings for chunks and store them in chunks.embedding.

Model: OpenAI text-embedding-3-small  (1536 dimensions, $0.02/1M tokens)
Requires: OPENAI_API_KEY environment variable

Strategy:
  - Fetch chunks where embedding IS NULL, in batches of EMBED_BATCH
  - Call the OpenAI embeddings API (up to 2048 inputs per call)
  - Write results back with a bulk UPDATE
  - Resumable: re-running skips already-embedded chunks
  - Rate-limit aware: backs off on 429s

Usage:
  cd backend
  OPENAI_API_KEY=sk-... DATABASE_URL=... \\
    .venv/bin/python3.12 -m app.pipeline.embedder

  # Embed only N chunks (test):
  ... --limit 100

  # Embed chunks for one decision only:
  ... --decision-id 42
"""

import argparse
import asyncio
import logging
import os
import time

from openai import AsyncOpenAI
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import array as pg_array

from app.database import init_db, SessionLocal
from app.models import Chunk, Decision  # noqa: F401

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

# ── Config ────────────────────────────────────────────────────────────────────

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIMS = 1536
EMBED_BATCH = 20        # chunks per API call — conservative for low-tier keys
INTER_BATCH_DELAY = 3.0 # seconds between API calls to respect TPM limits
DB_BATCH = 200          # rows per UPDATE commit
MAX_RETRIES = 6
RETRY_DELAY = 60.0      # seconds on first 429 — new keys have tight minute windows


# ── Embedding call ────────────────────────────────────────────────────────────


async def _embed_batch(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """Call OpenAI embeddings API with retry/backoff on rate limit errors."""
    delay = RETRY_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.embeddings.create(
                model=EMBED_MODEL,
                input=texts,
                dimensions=EMBED_DIMS,
            )
            # Results are returned in the same order as inputs
            return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "rate_limit" in msg.lower():
                log.warning("Rate limited — retrying in %.0fs (attempt %d/%d)", delay, attempt, MAX_RETRIES)
                await asyncio.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError(f"Failed after {MAX_RETRIES} retries")


# ── Pipeline ──────────────────────────────────────────────────────────────────


async def run(
    limit: int | None = None,
    decision_id: int | None = None,
) -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    await init_db()
    client = AsyncOpenAI(api_key=api_key)

    async with SessionLocal() as db:
        # Fetch un-embedded chunks
        stmt = (
            select(Chunk.id, Chunk.text)
            .where(Chunk.embedding.is_(None))
            .order_by(Chunk.id)
        )
        if decision_id is not None:
            stmt = stmt.where(Chunk.decision_id == decision_id)
        if limit is not None:
            stmt = stmt.limit(limit)

        rows = (await db.execute(stmt)).all()
        log.info("Chunks to embed: %d", len(rows))

        if not rows:
            log.info("Nothing to do — all chunks are already embedded.")
            await client.close()
            return

        ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]

        # Estimate tokens + cost
        est_tokens = sum(len(t) // 4 for t in texts)
        log.info("Est. tokens: %s  (~$%.4f)", f"{est_tokens:,}", est_tokens / 1_000_000 * 0.02)

        t0 = time.monotonic()
        total_embedded = 0

        for batch_start in range(0, len(ids), EMBED_BATCH):
            batch_ids = ids[batch_start: batch_start + EMBED_BATCH]
            batch_texts = texts[batch_start: batch_start + EMBED_BATCH]

            embeddings = await _embed_batch(client, batch_texts)

            # Write in DB_BATCH-sized UPDATE commits
            for db_start in range(0, len(batch_ids), DB_BATCH):
                db_ids = batch_ids[db_start: db_start + DB_BATCH]
                db_embs = embeddings[db_start: db_start + DB_BATCH]
                for chunk_id, emb in zip(db_ids, db_embs):
                    await db.execute(
                        update(Chunk)
                        .where(Chunk.id == chunk_id)
                        .values(embedding=emb)
                    )
                await db.commit()

            total_embedded += len(batch_ids)
            elapsed = time.monotonic() - t0
            rate = total_embedded / elapsed
            pct = total_embedded / len(ids) * 100
            log.info(
                "  %d/%d  (%.0f%%)  |  %.1f chunks/s  |  %.0fs elapsed",
                total_embedded, len(ids), pct, rate, elapsed,
            )

            # Pace requests to stay within per-minute token limits
            if batch_start + EMBED_BATCH < len(ids):
                await asyncio.sleep(INTER_BATCH_DELAY)

    await client.close()

    elapsed = time.monotonic() - t0
    log.info("Done. %d embeddings written in %.1fs.", total_embedded, elapsed)


# ── Entry point ───────────────────────────────────────────────────────────────


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Embed chunks with OpenAI text-embedding-3-small")
    parser.add_argument("--limit", type=int, default=None, help="Embed only N chunks")
    parser.add_argument("--decision-id", type=int, default=None, help="Embed chunks for one decision")
    args = parser.parse_args()
    await run(limit=args.limit, decision_id=args.decision_id)


if __name__ == "__main__":
    asyncio.run(_main())
