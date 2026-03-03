"""Regex-based entity extractor for BC court decisions.

Extracts six entity types from decision text:
  - judge         : presiding judges (Justice Smith, Master Jones)
  - statute       : statutory references (s.30 CFCSA, Section 4 FLA)
  - social_worker : ministry / protection worker names
  - lawyer        : counsel and lawyer names
  - office        : MCFD regional offices
  - outcome       : key outcome phrases (continuing custody, apprehension, etc.)

Usage:
    from app.services.extractor import extract_entities

    entities = extract_entities(full_text)
    # → [{"entity_type": "judge", "entity_value": "Justice Smith",
    #      "context_snippet": "...surrounding sentence..."}]
"""

import re
from typing import NamedTuple

# ── Patterns ──────────────────────────────────────────────────────────────────

# Each entry: (entity_type, compiled_pattern)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "judge",
        re.compile(
            r"(?:Justice|Judge|Honourable|Master)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
            re.UNICODE,
        ),
    ),
    (
        "statute",
        re.compile(
            r"(?:Section|s\.)\s*\d+(?:\.\d+)?(?:\(\d+\))?(?:\s*(?:of\s+(?:the\s+)?)?"
            r"(?:CFCSA|CF&CSA|Child,?\s*Family|Family Law Act|FLA|CFCSS|CFSCA))",
            re.IGNORECASE | re.UNICODE,
        ),
    ),
    (
        "social_worker",
        re.compile(
            r"(?:social worker|protection worker|ministry worker|MCFD worker)\s+"
            r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
            re.IGNORECASE | re.UNICODE,
        ),
    ),
    (
        "lawyer",
        re.compile(
            r"(?:counsel|lawyer|Mr\.|Ms\.|Mrs\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
            re.UNICODE,
        ),
    ),
    (
        "office",
        re.compile(
            r"(?:MCFD|Ministry)\s+(?:office|branch|region)\s+(?:in\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
            re.IGNORECASE | re.UNICODE,
        ),
    ),
]

# Outcome phrases matched case-insensitively; value = the matched phrase (title-cased)
_OUTCOME_PHRASES: list[str] = [
    "child returned",
    "permanent custody",
    "temporary custody",
    "supervision order",
    "continuing custody order",
    "continuing custody",
    "access denied",
    "access suspended",
    "apprehension ordered",
    "apprehension",
    "removed from",
    "placed in care",
    "order dismissed",
    "order granted",
    "reunification",
    "adoption order",
]

_OUTCOME_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in _OUTCOME_PHRASES) + r")\b",
    re.IGNORECASE,
)


# ── Context helper ─────────────────────────────────────────────────────────────


def _context_snippet(text: str, start: int, end: int, window: int = 120) -> str:
    """Return up to 2*window chars of text centred on the match."""
    s = max(0, start - window)
    e = min(len(text), end + window)
    return text[s:e].strip()


# ── Public API ─────────────────────────────────────────────────────────────────


def extract_entities(text: str) -> list[dict]:
    """Extract named entities from decision text using regex patterns.

    Returns a deduplicated list of dicts:
        {"entity_type": str, "entity_value": str, "context_snippet": str}

    Deduplication is by (entity_type, normalised value) — case-insensitive,
    whitespace-collapsed. The first occurrence wins.
    """
    if not text:
        return []

    results: list[dict] = []
    seen: set[tuple[str, str]] = set()

    # ── Regex patterns ──
    for entity_type, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            value = " ".join(m.group(0).split())  # collapse whitespace
            key = (entity_type, value.lower())
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "entity_type": entity_type,
                "entity_value": value,
                "context_snippet": _context_snippet(text, m.start(), m.end()),
            })

    # ── Outcome phrases ──
    for m in _OUTCOME_RE.finditer(text):
        value = m.group(1).lower().strip()
        key = ("outcome", value)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "entity_type": "outcome",
            "entity_value": value,
            "context_snippet": _context_snippet(text, m.start(), m.end()),
        })

    return results
