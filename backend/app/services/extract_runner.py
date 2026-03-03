"""Batch entity extraction runner.

Finds every decision that has chunks but no entities yet, runs
extract_entities() over the concatenated chunk text, and bulk-inserts
the results into the entities table.

Usage:
    cd backend
    DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \\
        python -m app.services.extract_runner
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import init_db, SessionLocal
from app.models import Entity  # noqa: F401 — registers with Base.metadata
from app.services.extractor import extract_entities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BATCH = 50  # decisions per batch


async def run_extraction() -> dict:
    """Extract entities from all unprocessed decisions.

    A decision is considered 'processed' once it has at least one row in
    the entities table (even a sentinel row for decisions with no matches).

    Returns {"processed": N, "entities_found": M}.
    """
    await init_db()

    async with SessionLocal() as db:
        # ── Collect all unprocessed decision IDs ──────────────────────────
        result = await db.execute(text("""
            SELECT d.id
            FROM decisions d
            WHERE EXISTS (SELECT 1 FROM chunks c WHERE c.decision_id = d.id)
              AND NOT EXISTS (SELECT 1 FROM entities e WHERE e.decision_id = d.id)
            ORDER BY d.id
        """))
        all_ids = [row.id for row in result.all()]

    log.info("Decisions to process: %d", len(all_ids))

    if not all_ids:
        log.info("Nothing to do.")
        return {"processed": 0, "entities_found": 0}

    processed = 0
    entities_found = 0

    # ── Process in batches ────────────────────────────────────────────────
    for i in range(0, len(all_ids), BATCH):
        batch_ids = all_ids[i : i + BATCH]

        async with SessionLocal() as db:
            # Fetch concatenated chunk text for this batch
            result = await db.execute(
                text("""
                    SELECT decision_id,
                           string_agg(text, ' ' ORDER BY chunk_num) AS full_text
                    FROM chunks
                    WHERE decision_id = ANY(:ids)
                    GROUP BY decision_id
                """),
                {"ids": batch_ids},
            )
            rows = result.all()

            rows_to_insert: list[dict] = []

            for row in rows:
                entities = extract_entities(row.full_text or "")

                if entities:
                    for e in entities:
                        rows_to_insert.append({
                            "decision_id": row.decision_id,
                            "entity_type": e["entity_type"],
                            "entity_value": e["entity_value"],
                            "context_snippet": e["context_snippet"],
                        })
                    entities_found += len(entities)
                else:
                    # Sentinel: marks decision as processed even when nothing found
                    rows_to_insert.append({
                        "decision_id": row.decision_id,
                        "entity_type": "none",
                        "entity_value": "-",
                        "context_snippet": None,
                    })

                processed += 1

            if rows_to_insert:
                await db.execute(
                    pg_insert(Entity).values(rows_to_insert).on_conflict_do_nothing()
                )
                await db.commit()

        log.info(
            "Batch %d/%d — %d processed, %d entities so far",
            i // BATCH + 1,
            -(-len(all_ids) // BATCH),
            processed,
            entities_found,
        )

    log.info("Done. processed=%d  entities_found=%d", processed, entities_found)
    return {"processed": processed, "entities_found": entities_found}


async def _main() -> None:
    await run_extraction()


if __name__ == "__main__":
    asyncio.run(_main())
