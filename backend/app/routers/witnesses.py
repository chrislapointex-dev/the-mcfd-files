"""GET /api/witnesses — Witness profiles with evidence chunks.

GET /api/witnesses          → list all witnesses with chunk counts
GET /api/witnesses/{name}   → full chunk list for one witness
"""

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..redact import redact_name

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
        "notes": (
            "12 DOCUMENTED FAILURES — March 6 2026 correspondence (CC: RCMP, OIPC, Premier, media)\n\n"
            "1. APPROVED REMOVAL SHE NEVER WITNESSED — Approved post-removal file August 19 2025, 12 days after removal. "
            "Not present at August 7 removal. Never reviewed video before approval. Form A sworn statement (Wolfenden: "
            "'unable to visually see Nadia', 'no least disruptive measures because Christopher would not allow SW to see Nadia') "
            "contradicted by 27 minutes of continuous video. Wolfenden never asked to see Nadia. Not once.\n\n"
            "2. APPROVED REMOVAL BASED ON AI USE — Form A Less Disruptive Measures section states verbatim: 'It is suspected "
            "that Christopher is struggling with his mental health as Christopher stated he has been up for 24 hours and was "
            "using AI to create a court case. Due to the limited capacity and the vulnerability of Nadia, it was decided that "
            "there was no least intrusive measure appropriate.' Newton approved removal of a child because her father was awake "
            "and preparing legal documents.\n\n"
            "3. APPROVED s.30 CFCSA VIOLATION — Burnstein directed removal without personally observing Nadia. Newton approved "
            "the file that codified this statutory violation.\n\n"
            "4. OBSERVED APPROPRIATE PARENTING AUGUST 21 2025 THEN CONTRADICTED HERSELF — Newton's own August 21 supervised "
            "visit (audio recorded): found materials age-appropriate, agreed with developmental assessment, positive visit. "
            "Her September 24 2025 letter then characterized LaPointe as a danger. No new incident in the intervening 21 days. "
            "Inconsistency unexplained and on record.\n\n"
            "5. FALSE AND INFLAMMATORY SEPTEMBER 24 2025 LETTER — Without evidence: alleged harassment/threats/coercion re "
            "diet (diet was 2019 MOU, validated by genetic testing June 2025); alleged LaPointe 'interrogated' Nadia (he "
            "reported sexual assault disclosure to RCMP as required); characterized settlement offer as 'coercive control and "
            "financial abuse' (he was paying $1,000/month voluntarily, double guideline); stated LaPointe 'does not understand "
            "the harm' (no clinical basis). OT Sheila Branscombe documented 'excellent parenting skills' July 29 2025. "
            "Pharmacist Dayton validated pharmacogenomic concerns day after Wolfenden refused to review them on camera. "
            "Newton ignored all of it.\n\n"
            "6. CREATED CONTRADICTORY VISITATION STRUCTURE — August 27 2025: directed Wolfenden to demand 10 days advance "
            "notice from LaPointe to provide 48 hours notice of visit. Shirley Filipe had previously arranged visits with "
            "normal notice. Same August 27 correspondence: told LaPointe ICS would contact him for ongoing visits. September "
            "24 2025 letter: criticized LaPointe for not arranging visits directly with Wolfenden. Gave contradictory "
            "instructions then used compliance with first instruction against him.\n\n"
            "7. SHAMING STATEMENT RE: RECORDING — Asked LaPointe 'why he would feel the need to record his daughter instead "
            "of spending quality time with her.' The recording is the evidence that exposes 15+ false statements in the Form A "
            "she approved. The question was designed to gaslight.\n\n"
            "8. SHIELDED WOLFENDEN FROM THREE UNANSWERED QUESTIONS — October 3 2025 letter: (a) what specific measurable "
            "actions satisfy Director's concerns? (b) what is the timeline for reunification? (c) what documented evidence "
            "justifies the F1? Over 5 months. Zero answers. Questions repeated March 6 2026 on the record.\n\n"
            "9. EXCLUDED WOLFENDEN FROM ACCOUNTABILITY MEETING — Informed LaPointe that Wolfenden will not attend the "
            "requested meeting. Wolfenden is subject of active complaints: OIPC INV-F-26-00220, RCY, BC College of Social "
            "Workers, RCMP. Newton is her supervisor. Never required Wolfenden to answer for contradictions between sworn "
            "statements and video. Now preventing direct accountability. Documented obstruction.\n\n"
            "10. SUPERVISOR REASSIGNMENT WITHOUT EXPLANATION — Moving to reassign supervision personnel instead of increasing "
            "parenting time. No written explanation provided. No revised parenting time plan. No progress toward reunification. "
            "71 days before trial.\n\n"
            "11. CONDITIONED MEETING ON INSTITUTIONAL AFFILIATION — Required support persons to provide institutional "
            "affiliation before attending. No CFCSA provision, FOIPPA section, or MCFD policy cited. No legal basis provided.\n\n"
            "12. LAWYER CONFLICT — Did not answer question asked twice: does MCFD have knowledge of or involvement in the "
            "pattern of legal representation barriers since August 2025? Every lawyer approached either conflicts out, becomes "
            "unavailable, or disengages without explanation. No response on record."
        ),
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
            "name": redact_name(witness["name"]),
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
            "text": redact_name(r.text),
            "source": r.source,
            "citation": r.citation or r.title or "",
            "title": r.title,
        }
        for r in rows
    ]

    return {
        "name": redact_name(witness["name"]),
        "role": witness["role"],
        "file": witness["file"],
        "phone": witness.get("phone", ""),
        "email": witness.get("email", ""),
        "notes": redact_name(witness.get("notes", "")),
        "chunks": chunks,
    }
