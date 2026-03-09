"""POST /api/contradictions/analyze — Contradiction engine.

Flow:
  1. Embed claim via embed_query()
  2. Fetch top 10 semantic chunks (filtered to personal sources if requested)
  3. Call Claude with legal analyst prompt
  4. Parse JSON response into contradiction records
  5. INSERT each result into contradictions table
  6. Return { contradictions: [...] }

GET /api/contradictions — list all stored contradiction records, newest first
"""

import json
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..models import Contradiction
from ..services.claude_service import _get_client
from ..services.embed_service import embed_query

router = APIRouter(prefix="/api/contradictions", tags=["contradictions"])

PERSONAL_SOURCES = ['foi', 'personal']

_SYSTEM_PROMPT = """\
You are a legal analyst. The following claim was made in a sworn statement. Review the
provided source documents and identify any direct contradictions, inconsistencies, or
supporting evidence. For each contradiction found, state: the exact claim, the
contradicting evidence, the source document and page, and a severity rating
(DIRECT / PARTIAL / NONE).

Return ONLY a JSON array. Each element must have these exact keys:
  "claim"      — the original claim (string)
  "evidence"   — the contradicting or supporting evidence found (string)
  "source"     — the source document name or citation (string)
  "page"       — page reference if available, else null (string or null)
  "severity"   — one of: "DIRECT", "PARTIAL", "NONE" (string)

If no contradictions are found, return an empty array [].
Do not include any text outside the JSON array.\
"""


class AnalyzeRequest(BaseModel):
    claim: str
    source_filter: Optional[str] = "all"  # "personal" | "all"


class ContradictionRecord(BaseModel):
    id: int
    claim: str
    evidence: Optional[str]
    source_doc: Optional[str]
    page_ref: Optional[str]
    severity: Optional[str]
    created_at: str


@router.get("", response_model=list[ContradictionRecord])
async def list_contradictions(db: AsyncSession = Depends(get_db)):
    """Return all stored contradiction records, newest first."""
    rows = (await db.execute(
        select(Contradiction).order_by(Contradiction.created_at.desc())
    )).scalars().all()
    return [
        ContradictionRecord(
            id=r.id,
            claim=r.claim,
            evidence=r.evidence,
            source_doc=r.source_doc,
            page_ref=r.page_ref,
            severity=r.severity,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/analyze")
async def analyze_contradiction(
    body: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Analyze a claim against stored documents and detect contradictions."""
    claim = body.claim.strip()
    if not claim:
        raise HTTPException(status_code=422, detail="claim cannot be empty")

    use_personal = body.source_filter == "personal"

    # 1. Embed claim
    try:
        query_vec = await embed_query(claim)
        vec_literal = f"[{','.join(str(x) for x in query_vec)}]"
    except Exception:
        raise HTTPException(status_code=503, detail="Embedding service unavailable")

    # 2. Fetch top 10 semantic chunks
    source_clause = "AND d.source = ANY(:sources)" if use_personal else ""
    sql = text(f"""
        SELECT
            c.id, c.text, c.citation, c.chunk_num,
            d.id   AS decision_id,
            d.title, d.source, d.url
        FROM chunks c
        JOIN decisions d ON d.id = c.decision_id
        WHERE c.embedding IS NOT NULL
          {source_clause}
        ORDER BY c.embedding <=> '{vec_literal}'::vector
        LIMIT 10
    """)
    params: dict = {}
    if use_personal:
        params["sources"] = PERSONAL_SOURCES

    rows = (await db.execute(sql, params)).all()

    if not rows:
        return {"contradictions": [], "message": "No relevant documents found"}

    # 3. Build document context for Claude
    doc_parts = []
    for i, r in enumerate(rows, 1):
        citation = r.citation or r.title or f"doc-{i}"
        doc_parts.append(
            f"[Document {i}]\nCitation: {citation}\nSource: {r.source}\nText:\n{r.text.strip()}"
        )
    docs_text = "\n---\n".join(doc_parts)

    user_message = f"Claim: {claim}\n\nDocuments:\n{docs_text}"

    # 4. Call Claude
    try:
        client = _get_client()
        response = await client.messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
    except Exception:
        raise HTTPException(status_code=503, detail="AI service unavailable")

    # 5. Parse JSON response
    try:
        # Strip markdown code fences if Claude added them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            parsed = []
    except (json.JSONDecodeError, ValueError):
        parsed = []

    # 6. Insert into DB and build response
    results = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        rec = Contradiction(
            claim=str(item.get("claim", claim))[:2000],
            evidence=str(item.get("evidence", ""))[:2000] or None,
            source_doc=str(item.get("source", ""))[:500] or None,
            page_ref=str(item.get("page", ""))[:100] or None,
            severity=str(item.get("severity", "NONE"))[:20],
        )
        db.add(rec)
        await db.flush()
        results.append({
            "id": rec.id,
            "claim": rec.claim,
            "evidence": rec.evidence,
            "source_doc": rec.source_doc,
            "page_ref": rec.page_ref,
            "severity": rec.severity,
        })

    await db.commit()
    return {"contradictions": results}


@router.get("/{contradiction_id}/evidence")
async def get_contradiction_evidence(
    contradiction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return a contradiction with its semantically-linked supporting evidence chunks."""
    # Fetch the contradiction
    row = (await db.execute(
        select(Contradiction).where(Contradiction.id == contradiction_id)
    )).scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Contradiction not found")

    # Fetch linked evidence chunks ordered by similarity score
    sql = text("""
        SELECT ce.chunk_id, ce.similarity_score,
               c.text, c.citation, c.page_estimate, d.source
        FROM contradiction_evidence ce
        JOIN chunks c ON c.id = ce.chunk_id
        JOIN decisions d ON d.id = c.decision_id
        WHERE ce.contradiction_id = :cid
        ORDER BY ce.similarity_score DESC
    """)
    evidence_rows = (await db.execute(sql, {"cid": contradiction_id})).all()

    return {
        "contradiction_id": row.id,
        "claim": row.claim,
        "evidence": row.evidence,
        "severity": row.severity,
        "supporting_evidence": [
            {
                "chunk_id": r.chunk_id,
                "similarity_score": r.similarity_score,
                "excerpt": (r.text or "")[:300].strip(),
                "source": r.source,
                "citation": r.citation,
                "page_estimate": r.page_estimate,
            }
            for r in evidence_rows
        ],
    }
