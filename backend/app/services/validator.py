"""Citation validator — cross-checks each [Source: X] claim against its chunk.

Uses embedding cosine similarity to score how well the sentence containing a
citation actually matches the text of the cited chunk.

Status thresholds:
  similarity >= 0.5  → VERIFIED
  similarity >= 0.3  → PARTIAL
  similarity <  0.3  → UNVERIFIED
"""

import asyncio
import logging
import math
import re

from .embed_service import embed_query

log = logging.getLogger(__name__)

# Regex: capture the citation string from [Source: X]
_CITATION_RE = re.compile(r'\[Source:\s*([^\]]+)\]')


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _status(sim: float) -> str:
    if sim >= 0.5:
        return "VERIFIED"
    if sim >= 0.3:
        return "PARTIAL"
    return "UNVERIFIED"


def _extract_claim_sentences(answer: str) -> list[tuple[str, str]]:
    """Return (citation_string, claim_sentence) for every [Source: X] tag."""
    pairs = []
    for m in _CITATION_RE.finditer(answer):
        citation = m.group(1).strip()
        # Walk backwards to find the start of this sentence
        preceding = answer[: m.start()]
        boundary = max(
            preceding.rfind(". "),
            preceding.rfind("! "),
            preceding.rfind("? "),
            preceding.rfind("\n"),
        )
        sentence_start = boundary + 2 if boundary >= 0 else 0
        sentence = answer[sentence_start : m.end()].strip()
        pairs.append((citation, sentence))
    return pairs


async def validate_citations(answer: str, chunks: list[dict]) -> list[dict]:
    """Validate every [Source: X] citation in answer against its source chunk.

    Returns a list of validation dicts, one per citation found.
    Never raises — on any failure returns whatever results were collected.
    """
    results: list[dict] = []
    try:
        # Build citation → chunk lookup (first match wins for duplicates)
        lookup: dict[str, dict] = {}
        for chunk in chunks:
            cit = (chunk.get("citation") or "").strip()
            if cit and cit not in lookup:
                lookup[cit] = chunk

        pairs = _extract_claim_sentences(answer)
        if not pairs:
            return []

        # Resolve each citation to a chunk
        matched: list[tuple[str, str, dict | None]] = []
        for citation, claim_text in pairs:
            chunk = lookup.get(citation)
            if chunk is None:
                # Prefix fallback: Claude sometimes appends ", para N"
                for db_cit, c in lookup.items():
                    if citation.startswith(db_cit):
                        chunk = c
                        break
            matched.append((citation, claim_text, chunk))

        # Batch-embed all claim texts + chunk texts in one gather call
        texts: list[str] = []
        for _cit, claim_text, chunk in matched:
            chunk_text = (chunk or {}).get("text") or (chunk or {}).get("full_text") or ""
            texts.append(claim_text[:400])       # claim (capped)
            texts.append(chunk_text[:400])       # chunk (capped)

        vecs = await asyncio.gather(*[embed_query(t) for t in texts])

        for i, (citation, claim_text, chunk) in enumerate(matched):
            claim_vec = vecs[i * 2]
            chunk_vec  = vecs[i * 2 + 1]

            chunk_text = (chunk or {}).get("text") or (chunk or {}).get("full_text") or ""
            source_snippet = chunk_text[:100].strip() if chunk_text else None

            if chunk is None or not chunk_text:
                results.append({
                    "citation_index": i + 1,
                    "citation": citation,
                    "status": "UNVERIFIED",
                    "similarity": 0.0,
                    "claim_text": claim_text[:200],
                    "source_snippet": None,
                })
                continue

            sim = round(_cosine_similarity(claim_vec, chunk_vec), 4)
            results.append({
                "citation_index": i + 1,
                "citation": citation,
                "status": _status(sim),
                "similarity": sim,
                "claim_text": claim_text[:200],
                "source_snippet": source_snippet,
            })

    except Exception as exc:
        log.warning("Citation validation failed: %s", exc)

    return results
