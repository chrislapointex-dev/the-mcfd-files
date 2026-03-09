"""GET /api/witnesses — Witness profiles with evidence chunks.

GET /api/witnesses          → list all witnesses with chunk counts
GET /api/witnesses/{name}   → full chunk list for one witness
"""

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api/witnesses", tags=["witnesses"])

PERSONAL_SOURCES = ['foi', 'personal']

WITNESS_LIST = [
    {
        "name": "Nicki Wolfenden",
        "role": "Social Worker",
        "file": "PC 19700",
        "phone": "",
        "email": "",
        "notes": "Primary social worker on file. Authored the Section 13 Report and multiple CFAs. Named in formal complaint filed Sept 2, 2025. Key contradictions: initial risk assessment vs. removal justification; statements about N's presentation vs. FOI records.",
    },
    {
        "name": "Tammy Newton",
        "role": "Team Leader",
        "file": "PC 19700",
        "phone": "",
        "email": "",
        "notes": "Team Leader overseeing Wolfenden. Signed off on removal decision Aug 12, 2025. Named in formal complaint filed Sept 2, 2025. Contradictions: supervision claim vs. documented absence from key meetings.",
    },
    {
        "name": "Jordon Muileboom",
        "role": "Acting Team Leader",
        "file": "PC 19700",
        "phone": "",
        "email": "",
        "notes": "Acting TL at time of some key decisions. Involved in interim review. Contradictions: what was communicated to C vs. what was recorded internally.",
    },
    {
        "name": "Robyn Burnstein",
        "role": "Centralized Screening TL",
        "file": "PC 19700",
        "phone": "",
        "email": "",
        "notes": "Centralized Screening Team Leader. Involved in intake decisions. Contradictions: screening criteria applied vs. what was documented at referral stage.",
    },
    {
        "name": "Cheryl Martin",
        "role": "Director Counsel",
        "file": "SC 64242",
        "phone": "",
        "email": "",
        "notes": "Legal counsel for the Director of Child Welfare. Representing MCFD in SC 64242. Key role in procedural decisions and evidence disclosure.",
    },
    {
        "name": "Plessa Walden",
        "role": "Opposing Counsel",
        "file": "SC 064851",
        "phone": "",
        "email": "",
        "notes": "Opposing counsel in SC 064851. Involved in procedural motions and submissions.",
    },
]

# Build a lookup dict for role/file by name
_WITNESS_MAP = {w["name"]: w for w in WITNESS_LIST}


@router.get("")
async def list_witnesses(db: AsyncSession = Depends(get_db)):
    """Return all witnesses with how many chunks mention them."""
    results = []
    for witness in WITNESS_LIST:
        name = witness["name"]
        sql = text("""
            SELECT COUNT(*) AS cnt
            FROM chunks c
            JOIN decisions d ON d.id = c.decision_id
            WHERE lower(c.text) LIKE '%' || lower(:name) || '%'
              AND d.source = ANY(:sources)
        """)
        cnt = (await db.execute(sql, {"name": name, "sources": PERSONAL_SOURCES})).scalar() or 0
        results.append({
            "name": witness["name"],
            "role": witness["role"],
            "file": witness["file"],
            "chunk_count": int(cnt),
        })
    return results


@router.get("/{name:path}")
async def get_witness(name: str, db: AsyncSession = Depends(get_db)):
    """Return all matching chunks for a specific witness."""
    name = unquote(name).strip()
    if name not in _WITNESS_MAP:
        raise HTTPException(status_code=404, detail=f"Witness '{name}' not found")

    witness = _WITNESS_MAP[name]

    sql = text("""
        SELECT
            c.id   AS chunk_id,
            c.text,
            c.citation,
            d.source,
            d.title
        FROM chunks c
        JOIN decisions d ON d.id = c.decision_id
        WHERE lower(c.text) LIKE '%' || lower(:name) || '%'
          AND d.source = ANY(:sources)
        ORDER BY c.id
        LIMIT 20
    """)
    rows = (await db.execute(sql, {"name": name, "sources": PERSONAL_SOURCES})).all()

    chunks = [
        {
            "chunk_id": r.chunk_id,
            "text": r.text,
            "source": r.source,
            "citation": r.citation or r.title or "",
            "title": r.title,
        }
        for r in rows
    ]

    return {
        "name": witness["name"],
        "role": witness["role"],
        "file": witness["file"],
        "phone": witness.get("phone", ""),
        "email": witness.get("email", ""),
        "notes": witness.get("notes", ""),
        "chunks": chunks,
    }
