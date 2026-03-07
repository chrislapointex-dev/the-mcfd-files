"""Semantic search endpoint — vector similarity over embedded chunks.

GET /api/search/semantic?q=<query>
  Optional params:
    k          — number of results (default 10, max 50)
    source     — filter by source (bccourts / rcy / legislation / news)
    threshold  — minimum cosine similarity score, 0–1 (default 0.3)

Returns ranked chunks with parent decision metadata and similarity score.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Chunk, Decision
from ..schemas import SemanticChunk, SemanticSearchResponse
from ..services.embed_service import embed_query

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    q: str = Query(..., min_length=1),
    k: int = Query(10, ge=1, le=50),
    source: Optional[str] = None,
    threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    # Embed the query
    query_vec = await embed_query(q)
    vec_literal = f"[{','.join(str(x) for x in query_vec)}]"

    PERSONAL_SOURCES = ['foi', 'personal']

    # Inline the vector literal — it's model output (all floats), safe to embed.
    # asyncpg chokes on :param::vector due to the double-colon, so we inline instead.
    if source == 'personal':
        source_filter = "AND d.source = ANY(:sources)"
    elif source:
        source_filter = "AND d.source = :source"
    else:
        source_filter = ""

    sql = text(f"""
        SELECT
            c.id          AS chunk_id,
            c.chunk_num,
            c.text,
            1 - (c.embedding <=> '{vec_literal}'::vector) AS score,
            d.id          AS decision_id,
            d.citation,
            d.title,
            d.source,
            d.date,
            d.court,
            d.url
        FROM chunks c
        JOIN decisions d ON d.id = c.decision_id
        WHERE c.embedding IS NOT NULL
          AND 1 - (c.embedding <=> '{vec_literal}'::vector) >= :threshold
          {source_filter}
        ORDER BY c.embedding <=> '{vec_literal}'::vector
        LIMIT :k
    """)

    params: dict = {"threshold": threshold, "k": k}
    if source == 'personal':
        params["sources"] = PERSONAL_SOURCES
    elif source:
        params["source"] = source

    rows = (await db.execute(sql, params)).all()

    # When no source filter, apply 1.15x boost to personal/FOI results and re-sort
    PERSONAL_BOOST_SOURCES = {'foi', 'personal'}
    boost = source is None

    results = []
    for r in rows:
        raw_score = float(r.score)
        if boost and r.source in PERSONAL_BOOST_SOURCES:
            raw_score = raw_score * 1.15
        results.append(SemanticChunk(
            chunk_id=r.chunk_id,
            chunk_num=r.chunk_num,
            text=r.text,
            score=round(raw_score, 4),
            decision_id=r.decision_id,
            citation=r.citation,
            title=r.title,
            source=r.source,
            date=r.date,
            court=r.court,
            url=r.url,
        ))

    if boost:
        results.sort(key=lambda c: c.score, reverse=True)

    return SemanticSearchResponse(query=q, total=len(results), results=results)
