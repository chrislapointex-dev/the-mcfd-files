"""Parent War Room — classified tools for self-represented parents in BC child protection.

POST /api/warroom/foi-generator        — generate FOIPPA request letter
POST /api/warroom/complaint-generator  — generate complaint letter
POST /api/warroom/rights-check         — check rights violations via vector search
GET  /api/warroom/patterns-summary     — top entities from database
GET  /api/warroom/self-rep-guide       — static self-rep toolkit
"""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.claude_service import _get_client
from ..services.embed_service import embed_query

router = APIRouter(prefix="/api/warroom", tags=["warroom"])

# ── Pydantic models ────────────────────────────────────────────────────────────

class FOIRequest(BaseModel):
    name: str
    address: str
    email: str
    date_range_start: str
    date_range_end: str
    file_numbers: Optional[str] = ""
    specific_records: str


class ComplaintRequest(BaseModel):
    type: str  # rcy | oipc | ombudsperson | human_rights
    details: str
    date_of_incident: str
    file_numbers: Optional[str] = ""


class RightsCheckRequest(BaseModel):
    what_happened: str


# ── Office addresses ───────────────────────────────────────────────────────────

_OFFICE_ADDRESSES = {
    "rcy": (
        "Representative for Children and Youth\n"
        "PO Box 9207 Stn Prov Govt\n"
        "Victoria, BC  V8W 9J1\n"
        "Phone: 1-800-476-3933"
    ),
    "oipc": (
        "Office of the Information and Privacy Commissioner\n"
        "PO Box 9038 Stn Prov Govt\n"
        "Victoria, BC  V8W 9A4\n"
        "Phone: 250-387-5629"
    ),
    "ombudsperson": (
        "BC Ombudsperson\n"
        "PO Box 9039 Stn Prov Govt\n"
        "Victoria, BC  V8W 9A5\n"
        "Phone: 1-800-567-3247"
    ),
    "human_rights": (
        "BC Human Rights Tribunal\n"
        "1170 – 605 Robson Street\n"
        "Vancouver, BC  V6B 5J3\n"
        "Phone: 604-775-2000"
    ),
}

_COMPLAINT_CITATIONS = {
    "rcy": "Representative for Children and Youth Act, SBC 2006, c 29",
    "oipc": "Freedom of Information and Protection of Privacy Act (FOIPPA), RSBC 1996, c 165",
    "ombudsperson": "Ombudsperson Act, RSBC 1996, c 340",
    "human_rights": "Human Rights Code, RSBC 1996, c 210",
}

# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/foi-generator")
async def foi_generator(req: FOIRequest):
    client = _get_client()

    prompt = f"""You are a legal document assistant. Generate a formal Freedom of Information request letter under BC's FOIPPA.

Requestor details:
- Name: {req.name}
- Address: {req.address}
- Email: {req.email}
- Date range: {req.date_range_start} to {req.date_range_end}
- File numbers: {req.file_numbers or "not specified"}
- Records requested: {req.specific_records}

Write a complete, professional FOI request letter addressed to:
MCFD Freedom of Information Office
PO Box 9770 Stn Prov Govt
Victoria, BC  V8W 9S5

Cite: FOIPPA s.4 (right of access), s.5 (how to make a request), s.7 (time limit — 30 business days), s.75(5) (fee waiver for public interest). Include today's date. Request fee waiver on grounds of public interest. Request records in electronic format. Include a deadline reminder. Professional but firm tone."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"letter": response.content[0].text}


@router.post("/complaint-generator")
async def complaint_generator(req: ComplaintRequest):
    client = _get_client()
    office_address = _OFFICE_ADDRESSES.get(req.type, "")
    citation = _COMPLAINT_CITATIONS.get(req.type, "")

    body_map = {
        "rcy": "Representative for Children and Youth (RCY)",
        "oipc": "Office of the Information and Privacy Commissioner (OIPC)",
        "ombudsperson": "BC Ombudsperson",
        "human_rights": "BC Human Rights Tribunal",
    }
    body_name = body_map.get(req.type, req.type.upper())

    prompt = f"""You are a legal document assistant. Generate a formal complaint letter to the {body_name}.

Incident details:
- Date of incident: {req.date_of_incident}
- File numbers: {req.file_numbers or "not specified"}
- What happened: {req.details}

Write a complete, professional complaint letter. Cite: {citation}. Include:
1. Clear statement of complaint
2. Chronological facts
3. Relevant legal provisions breached
4. Specific remedy requested
5. Contact information placeholder [YOUR CONTACT INFO]

Today's date header. Professional tone. Addressed to the appropriate officer at {body_name}."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return {"letter": response.content[0].text, "office_address": office_address}


@router.post("/rights-check")
async def rights_check(req: RightsCheckRequest, db: AsyncSession = Depends(get_db)):
    # Vector search for relevant chunks
    vec = await embed_query(req.what_happened)
    vec_str = "[" + ",".join(str(v) for v in vec) + "]"

    rows = await db.execute(text(
        "SELECT c.text, d.title, d.source "
        "FROM chunks c JOIN decisions d ON c.decision_id = d.id "
        f"ORDER BY c.embedding <=> '{vec_str}'::vector LIMIT 8"
    ))
    chunks = rows.fetchall()
    context = "\n\n".join(f"[{r[1]}]\n{r[0]}" for r in chunks) if chunks else "No matching precedents found."

    client = _get_client()
    prompt = f"""You are a legal rights advisor for parents in BC child protection proceedings.

The parent describes: {req.what_happened}

Relevant court decisions and legislation:
{context}

Identify potential rights violations. For each violation, return a JSON array with objects having these fields:
- section: the specific legal provision (e.g., "CFCSA s.4", "Charter s.7")
- title: short name of the right
- explanation: plain-language explanation (2-3 sentences, no jargon)
- what_to_do: concrete next step the parent can take

Also return a "patterns_matched" array of strings naming any patterns you see from BC court decisions.

Respond ONLY with valid JSON: {{"violations": [...], "patterns_matched": [...]}}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    text_out = response.content[0].text.strip()
    # Extract JSON from response
    start = text_out.find('{')
    end = text_out.rfind('}') + 1
    parsed = json.loads(text_out[start:end]) if start >= 0 else {"violations": [], "patterns_matched": []}
    return parsed


@router.get("/patterns-summary")
async def patterns_summary(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text(
        "SELECT entity_value, entity_type, COUNT(*) as freq "
        "FROM entities "
        "GROUP BY entity_value, entity_type "
        "ORDER BY COUNT(*) DESC "
        "LIMIT 20"
    ))
    results = rows.fetchall()
    return [
        {"name": r[0], "type": r[1], "frequency": r[2]}
        for r in results
    ]


@router.get("/self-rep-guide")
async def self_rep_guide():
    return {
        "filing_deadlines": [
            {"item": "Response to CCO application", "deadline": "2 days before hearing (CFCSA s.44)"},
            {"item": "Appeal of CCO/Continuing Custody Order", "deadline": "30 days from order date (CFCSA s.102)"},
            {"item": "Review of CCO conditions", "deadline": "Any time after 6 months (CFCSA s.59)"},
            {"item": "FOI request response", "deadline": "30 business days from receipt (FOIPPA s.7)"},
            {"item": "Complaint to RCY", "deadline": "Within 1 year of incident"},
            {"item": "Human Rights complaint", "deadline": "Within 1 year of last incident (HRC s.22)"},
        ],
        "cfcsa_plain_language": [
            {
                "section": "s.2",
                "title": "Guiding Principles",
                "plain": "The child's best interests are the most important consideration. Family is the preferred environment for raising children.",
            },
            {
                "section": "s.4",
                "title": "Best Interests of Child",
                "plain": "Courts must consider the child's safety, health, and emotional well-being; the child's cultural identity; the importance of family relationships; and continuity of care.",
            },
            {
                "section": "s.13",
                "title": "When a Child Needs Protection",
                "plain": "Lists situations where MCFD can intervene, including physical harm, emotional harm, sexual abuse, or if a parent is unable to care for the child.",
            },
            {
                "section": "s.22",
                "title": "Least Disruptive Measures",
                "plain": "MCFD must use the least disruptive intervention. Removal is a last resort. They must try family support services first.",
            },
            {
                "section": "s.41",
                "title": "Presentation Hearing",
                "plain": "First court appearance after removal. Must happen within 7 days. You have the right to be heard. Bring all evidence of support network.",
            },
            {
                "section": "s.44",
                "title": "Protection Hearing",
                "plain": "Full hearing on whether the child needed protection. You can call witnesses, cross-examine MCFD workers, and present evidence.",
            },
            {
                "section": "s.59",
                "title": "Review of Custody Orders",
                "plain": "You can apply to court to review or change a custody order if circumstances have changed significantly.",
            },
        ],
        "legal_aid_links": [
            {"name": "Legal Services Society (Legal Aid BC)", "url": "https://lss.bc.ca", "note": "Free legal advice for qualifying parents"},
            {"name": "Access Pro Bono BC", "url": "https://accessprobono.ca", "note": "Free legal clinics across BC"},
            {"name": "BC Family Law Support", "url": "https://www.familylaw.lss.bc.ca", "note": "Plain-language guides"},
            {"name": "People's Law School", "url": "https://www.peopleslawschool.ca", "note": "Know your rights guides"},
        ],
        "evidence_checklist": [
            "All written communications with MCFD (emails, letters, notes from visits)",
            "Your own dated notes of every interaction — include worker name, date, time, what was said",
            "Photos of your home showing safe conditions",
            "Medical and therapy records for your child",
            "Support letters from teachers, doctors, family members, neighbours",
            "Proof of completed programs (parenting courses, counselling, etc.)",
            "Any previous court orders and their conditions",
            "FOI records from MCFD file",
        ],
        "pharmacogenomics": {
            "title": "Pharmacogenomic Testing",
            "summary": "If medications have been an issue in your case, pharmacogenomic testing shows how your body metabolizes specific drugs. Poor metabolizer status can explain 'non-compliance' or adverse reactions that were biological, not behavioural.",
            "providers": ["Genomics Health (BC)", "Mayo Clinic Laboratories", "GeneSight"],
            "how_to_use": "Request testing through your GP. Results can be submitted as medical evidence. Cites: CFCSA s.4(1)(b) — child's physical and emotional health needs.",
        },
    }
