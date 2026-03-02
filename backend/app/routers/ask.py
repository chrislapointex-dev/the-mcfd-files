"""POST /api/ask — natural language Q&A over the MCFD database.

Flow:
  1. Load R2-D2 context (recent searches, flagged cases, research goals)
  2. Run FTS + semantic search in parallel, merge and deduplicate chunks
  3. Pass question + chunks + R2 context to claude_service.ask()
  4. Extract cited sources from the answer
  5. Save Q&A to R2 HIPPOCAMPUS
  6. Return answer, sources list, memory_updated flag
"""

import asyncio
import re
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.claude_service import ask as claude_ask
from ..services.embed_service import embed_query
from r2d2 import R2Memory
from r2d2.context import ContextBuilder

router = APIRouter(prefix="/api", tags=["ask"])

FTS_LIMIT = 15
SEMANTIC_LIMIT = 15
MERGED_CAP = 20


# ── Schemas ───────────────────────────────────────────────────────────────────


class AskRequest(BaseModel):
    question: str
    user_id: str = "default"


class SourceRef(BaseModel):
    citation: Optional[str]
    title: str
    source: str
    url: str
    decision_id: int


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    chunks_used: int
    memory_updated: bool


# ── Chunk retrieval ───────────────────────────────────────────────────────────


async def _fetch_fts_chunks(db: AsyncSession, question: str) -> list[dict]:
    """Full-text search the chunks table."""
    sql = text("""
        SELECT
            c.id, c.text, c.citation, c.chunk_num,
            d.id   AS decision_id,
            d.title, d.source, d.url, d.court, d.date,
            ts_rank_cd(
                to_tsvector('english', c.text),
                websearch_to_tsquery('english', :q)
            ) AS rank
        FROM chunks c
        JOIN decisions d ON d.id = c.decision_id
        WHERE to_tsvector('english', c.text) @@ websearch_to_tsquery('english', :q)
        ORDER BY rank DESC
        LIMIT :limit
    """)
    rows = (await db.execute(sql, {"q": question, "limit": FTS_LIMIT})).all()
    return [_row_to_dict(r) for r in rows]


async def _fetch_semantic_chunks(db: AsyncSession, question: str) -> list[dict]:
    """Vector similarity search the chunks table."""
    try:
        query_vec = await embed_query(question)
        vec_literal = f"[{','.join(str(x) for x in query_vec)}]"
        sql = text(f"""
            SELECT
                c.id, c.text, c.citation, c.chunk_num,
                d.id   AS decision_id,
                d.title, d.source, d.url, d.court, d.date
            FROM chunks c
            JOIN decisions d ON d.id = c.decision_id
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> '{vec_literal}'::vector
            LIMIT :limit
        """)
        rows = (await db.execute(sql, {"limit": SEMANTIC_LIMIT})).all()
        return [_row_to_dict(r) for r in rows]
    except Exception:
        return []


def _row_to_dict(r) -> dict:
    return {
        "id": r.id,
        "citation": r.citation,
        "text": r.text,
        "source": r.source,
        "decision_id": r.decision_id,
        "title": r.title,
        "url": r.url,
        "court": r.court,
        "date": str(r.date) if r.date else None,
    }


def _merge_chunks(fts: list[dict], semantic: list[dict]) -> list[dict]:
    """Merge FTS and semantic results, deduplicate by chunk id, cap at MERGED_CAP.

    FTS results come first (they matched the exact query terms); semantic fills
    the remaining slots with conceptually similar chunks not already present.
    """
    seen: set[int] = set()
    merged: list[dict] = []
    for chunk in fts + semantic:
        if chunk["id"] not in seen:
            seen.add(chunk["id"])
            merged.append(chunk)
        if len(merged) >= MERGED_CAP:
            break
    return merged


# ── Source extraction ─────────────────────────────────────────────────────────


def _extract_sources(answer: str, chunks: list[dict]) -> list[SourceRef]:
    """Find all [Source: citation] tags in the answer and match to chunk metadata."""
    # Pull every citation string that appears in [Source: ...] tags
    cited = set(re.findall(r'\[Source:\s*([^\]]+)\]', answer))

    # Build a lookup: citation → chunk metadata (first match wins)
    lookup: dict[str, dict] = {}
    for c in chunks:
        cit = (c.get("citation") or "").strip()
        if cit and cit not in lookup:
            lookup[cit] = c

    sources: list[SourceRef] = []
    seen_ids: set[int] = set()

    for cit in cited:
        cit = cit.strip()
        # Exact match first; fall back to prefix match (Claude may append ", para N")
        meta = lookup.get(cit)
        if meta is None:
            for db_cit, chunk in lookup.items():
                if cit.startswith(db_cit):
                    meta = chunk
                    break
        if meta and meta["decision_id"] not in seen_ids:
            seen_ids.add(meta["decision_id"])
            sources.append(SourceRef(
                citation=meta["citation"],
                title=meta["title"],
                source=meta["source"],
                url=meta["url"],
                decision_id=meta["decision_id"],
            ))

    # Sort by citation string for stable output
    sources.sort(key=lambda s: s.citation or "")
    return sources


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.post("/ask", response_model=AskResponse)
async def ask_endpoint(
    body: AskRequest,
    db: AsyncSession = Depends(get_db),
):
    question = body.question.strip()
    mem = R2Memory(db=db, user_id=body.user_id)

    # 1. Load R2 context
    r2_context = ""
    try:
        builder = ContextBuilder(mem)
        r2_context = await builder.build(limit_per_region=3)
    except Exception:
        pass

    # 2. FTS + semantic search in parallel, merge results
    fts_chunks, sem_chunks = await asyncio.gather(
        _fetch_fts_chunks(db, question),
        _fetch_semantic_chunks(db, question),
    )
    chunks = _merge_chunks(fts_chunks, sem_chunks)

    # 3. Build prompt — prepend R2 context as a system note if available
    if r2_context:
        question_with_context = (
            f"[Research context from previous sessions]\n{r2_context}\n\n"
            f"Question: {question}"
        )
    else:
        question_with_context = question

    # 4. Ask Claude
    answer = await claude_ask(question=question_with_context, chunks=chunks)

    # 5. Extract cited sources
    sources = _extract_sources(answer, chunks)

    # 6. Save to R2 memory
    memory_updated = False
    try:
        await mem.save(
            key=f"qa:{question[:100]}",
            value={
                "question": question,
                "answer": answer,
                "sources_cited": [s.citation for s in sources],
                "chunks_used": len(chunks),
                "fts_chunks": len(fts_chunks),
                "semantic_chunks": len(sem_chunks),
            },
            category="search_query",
            region="HIPPOCAMPUS",
            source="ask_endpoint",
        )
        memory_updated = True
    except Exception:
        pass

    return AskResponse(
        answer=answer,
        sources=sources,
        chunks_used=len(chunks),
        memory_updated=memory_updated,
    )
