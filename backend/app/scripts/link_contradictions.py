"""Link each contradiction to its top supporting evidence chunks via semantic search.

Re-runnable: deletes existing rows per contradiction before inserting new ones.

Run with:
    docker exec <backend> python3 -m app.scripts.link_contradictions
"""

import asyncio

from sqlalchemy import select, text, delete

from ..database import SessionLocal
from ..models import Contradiction, ContradictionEvidence
from ..services.embed_service import embed_query, load_model

PERSONAL_SOURCES = ['foi', 'personal']
THRESHOLD = 0.3
TOP_K = 5


async def link_all():
    load_model()
    async with SessionLocal() as db:
        # Fetch all contradictions
        contradictions = (await db.execute(select(Contradiction))).scalars().all()
        print(f"Linking {len(contradictions)} contradictions...")

        total_linked = 0
        for i, c in enumerate(contradictions, 1):
            # Build query text from claim + evidence (first 500 chars)
            query_text = (c.claim + " " + (c.evidence or ""))[:500].strip()

            # Embed query
            try:
                vec = await embed_query(query_text)
            except Exception as e:
                print(f"  [!] Contradiction {c.id}: embedding failed — {e}")
                continue

            vec_literal = "[" + ",".join(str(x) for x in vec) + "]"

            # Vector search: top 5 FOI/personal chunks above threshold
            sql = text(f"""
                SELECT c.id AS chunk_id,
                       1 - (c.embedding <=> '{vec_literal}'::vector) AS score,
                       c.text, c.citation, c.page_estimate, d.source, d.title
                FROM chunks c
                JOIN decisions d ON d.id = c.decision_id
                WHERE c.embedding IS NOT NULL
                  AND d.source = ANY(:sources)
                  AND 1 - (c.embedding <=> '{vec_literal}'::vector) >= :threshold
                ORDER BY c.embedding <=> '{vec_literal}'::vector
                LIMIT :k
            """)
            rows = (await db.execute(sql, {
                "sources": PERSONAL_SOURCES,
                "threshold": THRESHOLD,
                "k": TOP_K,
            })).all()

            # Delete existing links for this contradiction (re-runnable)
            await db.execute(
                delete(ContradictionEvidence).where(
                    ContradictionEvidence.contradiction_id == c.id
                )
            )

            # Insert new links
            for row in rows:
                db.add(ContradictionEvidence(
                    contradiction_id=c.id,
                    chunk_id=row.chunk_id,
                    similarity_score=float(row.score),
                ))

            await db.flush()
            print(f"  Linked contradiction {i}/{len(contradictions)} (id={c.id}): found {len(rows)} supporting chunks")
            total_linked += len(rows)

        await db.commit()
        print(f"\nDone. Total evidence records inserted: {total_linked}")


if __name__ == "__main__":
    asyncio.run(link_all())
