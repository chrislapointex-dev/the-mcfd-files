"""Generate embeddings for chunks using a local sentence-transformers model.

Model: all-MiniLM-L6-v2  (384 dimensions, runs fully local, no API key needed)
Install: pip install sentence-transformers

Strategy:
  - Load model once, keep in memory for the whole run
  - Fetch un-embedded chunks in batches from DB
  - Encode with the local model (CPU, batched for speed)
  - Bulk-update chunks.embedding
  - Resumable: skips chunks where embedding IS NOT NULL

Usage:
  cd backend
  DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
    .venv/bin/python3.12 -m app.pipeline.embedder

  # Embed only N chunks (test):
  ... --limit 100

  # Embed chunks for one decision only:
  ... --decision-id 42
"""

import argparse
import asyncio
import logging
import time

from sentence_transformers import SentenceTransformer
from sqlalchemy import select, update

from app.database import init_db, SessionLocal
from app.models import Chunk, Decision  # noqa: F401

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

# ── Config ────────────────────────────────────────────────────────────────────

EMBED_MODEL = "all-MiniLM-L6-v2"   # 384-dim, fast, good quality
ENCODE_BATCH = 256                  # texts per model.encode() call
DB_BATCH = 500                      # rows per UPDATE commit


# ── Pipeline ──────────────────────────────────────────────────────────────────


async def run(
    limit: int | None = None,
    decision_id: int | None = None,
) -> None:
    await init_db()

    log.info("Loading model %s …", EMBED_MODEL)
    model = SentenceTransformer(EMBED_MODEL)
    log.info("Model loaded. Output dims: %d", model.get_sentence_embedding_dimension())

    async with SessionLocal() as db:
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
            return

        ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]

        t0 = time.monotonic()
        total_embedded = 0

        for batch_start in range(0, len(ids), ENCODE_BATCH):
            batch_ids = ids[batch_start: batch_start + ENCODE_BATCH]
            batch_texts = texts[batch_start: batch_start + ENCODE_BATCH]

            # Encode synchronously in thread so event loop stays free
            embeddings = await asyncio.to_thread(
                model.encode,
                batch_texts,
                batch_size=64,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # Write in DB_BATCH-sized UPDATE commits
            for db_start in range(0, len(batch_ids), DB_BATCH):
                db_ids = batch_ids[db_start: db_start + DB_BATCH]
                db_embs = embeddings[db_start: db_start + DB_BATCH]
                for chunk_id, emb in zip(db_ids, db_embs):
                    await db.execute(
                        update(Chunk)
                        .where(Chunk.id == chunk_id)
                        .values(embedding=emb.tolist())
                    )
                await db.commit()

            total_embedded += len(batch_ids)
            elapsed = time.monotonic() - t0
            rate = total_embedded / elapsed
            pct = total_embedded / len(ids) * 100
            log.info(
                "  %d/%d  (%.0f%%)  |  %.0f chunks/s  |  %.0fs elapsed  |  ETA ~%.0fs",
                total_embedded, len(ids), pct, rate, elapsed,
                (len(ids) - total_embedded) / rate if rate > 0 else 0,
            )

    elapsed = time.monotonic() - t0
    log.info("Done. %d embeddings written in %.1fs  (%.0f chunks/s).",
             total_embedded, elapsed, total_embedded / elapsed)


# ── Entry point ───────────────────────────────────────────────────────────────


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed chunks with local sentence-transformers model"
    )
    parser.add_argument("--limit", type=int, default=None, help="Embed only N chunks")
    parser.add_argument("--decision-id", type=int, default=None, help="Embed chunks for one decision")
    args = parser.parse_args()
    await run(limit=args.limit, decision_id=args.decision_id)


if __name__ == "__main__":
    asyncio.run(_main())
