"""Idempotent seed: insert Contradiction #23 — Wolfenden FOIPPA breach (March 9 2026).

Run:
    docker exec the-mcfd-files-backend-1 python3 -m app.scripts.seed_contradiction_23
"""

import asyncio
from sqlalchemy import text
from ..database import SessionLocal


CONTRADICTION = {
    "claim": (
        "MCFD social workers are bound by FOIPPA and professional confidentiality obligations "
        "not to share client personal information with third parties without consent."
    ),
    "evidence": (
        "SW Nicki Wolfenden shared Christopher LaPointe's personal contact information with "
        "Robb Dolson RCC (Centre for Dignity, Kamloops) without LaPointe's knowledge or consent. "
        "Dolson left an unsolicited voicemail on March 9 2026 stating 'Nicki had given me your "
        "contact info.' Voicemail preserved. No referral was requested. No consent was given. "
        "FOIPPA s.33-s.39 governs disclosure of personal information."
    ),
    "severity": "DIRECT",
    "source_doc": (
        "Voicemail transcript March 9 2026 | FOIPPA RSBC 1996 c.165 s.33-39 | "
        "Professional conduct obligations SW Wolfenden"
    ),
}


async def main():
    async with SessionLocal() as db:
        # Idempotent check
        existing = (await db.execute(text(
            "SELECT id FROM contradictions WHERE source_doc LIKE '%Voicemail%March 9 2026%'"
        ))).first()

        if existing:
            print(f"Contradiction #23 already exists (id={existing.id}). Skipping.")
            return

        await db.execute(text("""
            INSERT INTO contradictions (claim, evidence, severity, source_doc)
            VALUES (:claim, :evidence, :severity, :source_doc)
        """), CONTRADICTION)
        await db.commit()

        row = (await db.execute(text(
            "SELECT id FROM contradictions WHERE source_doc LIKE '%Voicemail%March 9 2026%'"
        ))).first()
        print(f"Inserted Contradiction #{row.id} — Wolfenden FOIPPA breach (severity=DIRECT)")


if __name__ == "__main__":
    asyncio.run(main())
