"""Cross-examination question generator.

POST /api/crossexam/generate  — generate questions for one or all contradictions
GET  /api/crossexam/{id}      — retrieve stored questions for a contradiction
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Contradiction, CrossExamQuestion
from ..redact import redact_name
from ..services.claude_service import _get_client

router = APIRouter(prefix="/api/crossexam", tags=["crossexam"])

_SYSTEM_PROMPT = """\
You are a legal assistant helping a self-represented litigant prepare for a BC Provincial Court
child protection trial (PC 19700). Generate pointed, admissible cross-examination questions.
Questions must be: short and closed (yes/no or specific answer), based strictly on the
provided evidence, designed to expose the contradiction, sequenced to build toward the
contradiction, and numbered. Each question followed by its FOI source reference.
Format: numbered list only, no preamble.\
"""


class GenerateRequest(BaseModel):
    contradiction_id: Optional[int] = None
    style: str = "cross-examination"


async def _generate_for_contradiction(r, db: AsyncSession, style: str) -> str:
    """Generate cross-exam questions for one contradiction row. Returns questions_text."""
    # Fetch top 3 evidence chunks
    sql = text("""
        SELECT ce.similarity_score, c.text, d.source
        FROM contradiction_evidence ce
        JOIN chunks c ON c.id = ce.chunk_id
        JOIN decisions d ON d.id = c.decision_id
        WHERE ce.contradiction_id = :cid
        ORDER BY ce.similarity_score DESC
        LIMIT 3
    """)
    evidence_rows = (await db.execute(sql, {"cid": r.id})).all()

    evidence_parts = []
    for i, ev in enumerate(evidence_rows, 1):
        excerpt = (ev.text or "")[:300].strip().replace("\n", " ")
        evidence_parts.append(f"[{i}] Source: {ev.source} | {excerpt}")
    evidence_text = "\n".join(evidence_parts) if evidence_parts else "(no linked evidence chunks)"

    user_message = (
        f"CONTRADICTION:\n"
        f"Statement A (sworn): {r.claim}\n"
        f"Statement B (contradicting): {r.evidence or '(none)'}\n"
        f"Severity: {r.severity or 'UNKNOWN'}\n"
        f"Source: {r.source_doc or 'unknown'}\n\n"
        f"SUPPORTING FOI EVIDENCE:\n{evidence_text}\n\n"
        f"Generate 5-8 cross-examination questions that expose this contradiction.\n"
        f"After the questions, add: \"FOLLOW-UP IF DENIED: [one follow-up question]\""
    )

    client = _get_client()
    response = await client.messages.create(
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


@router.post("/generate")
async def generate_crossexam(body: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate cross-examination questions for one or all contradictions."""
    model_name = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    if body.contradiction_id is not None:
        # Single contradiction
        r = (await db.execute(
            select(Contradiction).where(Contradiction.id == body.contradiction_id)
        )).scalar_one_or_none()
        if r is None:
            raise HTTPException(status_code=404, detail="Contradiction not found")

        try:
            questions_text = await _generate_for_contradiction(r, db, body.style)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"AI service error: {exc}")

        # Upsert: update if exists, insert if not
        existing = (await db.execute(
            select(CrossExamQuestion).where(CrossExamQuestion.contradiction_id == r.id)
        )).scalar_one_or_none()

        if existing:
            existing.questions_text = questions_text
            existing.style = body.style
            existing.model_used = model_name
            existing.generated_at = datetime.now(timezone.utc)
        else:
            db.add(CrossExamQuestion(
                contradiction_id=r.id,
                questions_text=questions_text,
                style=body.style,
                model_used=model_name,
            ))

        await db.commit()
        return {
            "contradiction_id": r.id,
            "claim": redact_name(r.claim),
            "evidence": redact_name(r.evidence) if r.evidence else r.evidence,
            "severity": r.severity,
            "questions_text": redact_name(questions_text),
            "model_used": model_name,
        }

    else:
        # Batch mode — all contradictions
        all_rows = (await db.execute(
            select(Contradiction).order_by(Contradiction.id)
        )).scalars().all()

        results = []
        for r in all_rows:
            try:
                questions_text = await _generate_for_contradiction(r, db, body.style)
            except Exception:
                questions_text = "(generation failed)"

            existing = (await db.execute(
                select(CrossExamQuestion).where(CrossExamQuestion.contradiction_id == r.id)
            )).scalar_one_or_none()

            if existing:
                existing.questions_text = questions_text
                existing.style = body.style
                existing.model_used = model_name
            else:
                db.add(CrossExamQuestion(
                    contradiction_id=r.id,
                    questions_text=questions_text,
                    style=body.style,
                    model_used=model_name,
                ))
            await db.flush()
            results.append({"contradiction_id": r.id, "severity": r.severity})

        await db.commit()
        return {"generated": len(results), "contradictions": results}


@router.get("/{contradiction_id}")
async def get_crossexam(contradiction_id: int, db: AsyncSession = Depends(get_db)):
    """Return stored questions for a contradiction (no regeneration)."""
    # Join to get contradiction details
    sql = text("""
        SELECT cq.questions_text, cq.generated_at, cq.model_used, cq.style,
               c.claim, c.evidence, c.severity, c.source_doc
        FROM crossexam_questions cq
        JOIN contradictions c ON c.id = cq.contradiction_id
        WHERE cq.contradiction_id = :cid
    """)
    row = (await db.execute(sql, {"cid": contradiction_id})).one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="No questions generated yet for this contradiction")

    return {
        "contradiction_id": contradiction_id,
        "claim": redact_name(row.claim),
        "evidence": redact_name(row.evidence) if row.evidence else row.evidence,
        "severity": row.severity,
        "source_doc": row.source_doc,
        "questions_text": redact_name(row.questions_text),
        "style": row.style,
        "generated_at": row.generated_at.isoformat(),
        "model_used": row.model_used,
    }
