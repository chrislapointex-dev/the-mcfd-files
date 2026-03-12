"""Name redaction for public-facing display.

Government employees: First initial + last name (public scrutiny permitted).
Minors: First initial only, no last name.
Private individuals: Initials only.
The father (applicant): C.L. or "the father".

Raw chunk text and decision full_text are NOT redacted — those are behind
auth and needed for trial prep. Only display-level fields (titles, claims,
evidence summaries, descriptions, notes) are redacted.
"""

import re

# Order matters — longer/more specific patterns first
_REPLACEMENTS = [
    # Child (minor — strongest protection)
    ("Nadia Seyler-LaPointe", "N. (the child)"),
    ("Nadia Seyler-La Pointe", "N. (the child)"),
    ("Nadia LaPointe", "N. (the child)"),
    ("Nadia La Pointe", "N. (the child)"),
    ("Nadia", "N."),

    # Father (applicant)
    ("Christopher Scott La Pointe", "C.L. (the father)"),
    ("Christopher Scott LaPointe", "C.L. (the father)"),
    ("Christopher LaPointe", "C.L."),
    ("Christopher La Pointe", "C.L."),
    ("Chris LaPointe", "C.L."),
    ("Chris La Pointe", "C.L."),
    ("Christopher", "C.L."),
    ("LaPointe, Christopher", "C.L."),

    # Mother (private individual)
    ("Natasha Seyler", "N.S."),
    ("Natasha", "N.S."),

    # Government employees (first initial + last name — public scrutiny OK)
    ("Nicki Wolfenden", "N. Wolfenden"),
    ("Tammy Newton", "T. Newton"),
    ("Jordon Muileboom", "J. Muileboom"),
    ("Robyn Burnstein", "R. Burnstein"),
    ("Cheryl Martin", "C. Martin"),
    ("Plessa Walden", "P. Walden"),
    ("Kaitlyn Elias", "K. Elias"),

    # Hashtags
    ("#FreeNadia", "#ProtectBCKids"),
]


def redact_name(text: str) -> str:
    """Apply all name replacements to a string. Case-sensitive."""
    if not text:
        return text
    for old, new in _REPLACEMENTS:
        text = text.replace(old, new)
    return text


def redact_dict(d: dict, fields: list[str]) -> dict:
    """Redact specified string fields in a dict. Returns a new dict."""
    result = dict(d)
    for f in fields:
        if f in result and isinstance(result[f], str):
            result[f] = redact_name(result[f])
    return result
