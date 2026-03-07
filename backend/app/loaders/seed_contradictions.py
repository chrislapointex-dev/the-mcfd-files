"""Seed 10 known contradictions into the contradictions table.

Idempotent — if >= 10 rows already exist, skips insertion.

Usage:
    docker exec the-mcfd-files-backend-1 python3 -m app.loaders.seed_contradictions
"""

import asyncio
import logging

from sqlalchemy import text

from app.models import Contradiction
from app.database import init_db, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

CONTRADICTIONS = [
    {
        "claim": "Wolfenden Form F1 Aug 12 states father was behaving erratically",
        "evidence": "27-minute video recording from Aug 12 shows no erratic behaviour — father is calm, measured, and child is content throughout",
        "source_doc": "Wolfenden Form F1",
        "page_ref": "Aug 12 2025",
        "severity": "DIRECT",
    },
    {
        "claim": "Removal direction was based on Burnstein's observed child safety concerns",
        "evidence": "Burnstein never personally observed the child or the home — removal was based on secondhand reports from Wolfenden",
        "source_doc": "MCFD Removal Records",
        "page_ref": "Aug 7 2025",
        "severity": "DIRECT",
    },
    {
        "claim": "PC 19700 was based on an independent safety assessment",
        "evidence": "PC 19700 was filed Aug 5 2025 — one day after the custody notice dated Aug 4 2025 — no independent assessment was conducted",
        "source_doc": "Court File PC 19700",
        "page_ref": "Aug 5 2025",
        "severity": "DIRECT",
    },
    {
        "claim": "MCFD disclosed 1,792 pages to OIPC in response to FOI request",
        "evidence": "Father received only 906 pages — 886 pages remain unaccounted for with no exemption log provided",
        "source_doc": "OIPC FOI Disclosure",
        "page_ref": "FOI-2025",
        "severity": "DIRECT",
    },
    {
        "claim": "MCFD reviewed and addressed the WGS pharmacogenomic report",
        "evidence": "WGS pharmacogenomic report appears in MCFD's own file but was never acted on, referenced, or communicated to the father or medical team",
        "source_doc": "MCFD Internal File",
        "page_ref": "WGS Report",
        "severity": "DIRECT",
    },
    {
        "claim": "Removal was initiated based on concerns arising from the Aug 7 visit",
        "evidence": "FOI documents show removal was pre-planned between Aug 4–7 — internal emails reference removal preparation before the Aug 7 visit occurred",
        "source_doc": "FOI Documents",
        "page_ref": "Aug 4-7 2025",
        "severity": "DIRECT",
    },
    {
        "claim": "Father being up for 24 hours using AI was cited as a mental health concern",
        "evidence": "Father was using AI tools to prepare legal documents for the custody hearing — this is lawful legal self-representation, not a mental health indicator",
        "source_doc": "Wolfenden Notes",
        "page_ref": "Aug 2025",
        "severity": "PARTIAL",
    },
    {
        "claim": "Father standing on his own deck was cited as concerning behaviour",
        "evidence": "FOI documents use the phrase 'would not allow' 7 times — mischaracterizing lawful presence on private property as non-compliance",
        "source_doc": "FOI Documents",
        "page_ref": "Aug 7 2025",
        "severity": "PARTIAL",
    },
    {
        "claim": "Nadia's access schedule was maintained per the court order",
        "evidence": "Halloween 2025, Christmas 2025, and Nadia's birthday were all cancelled — no court authorization for cancellation was obtained",
        "source_doc": "Access Records",
        "page_ref": "Oct-Dec 2025",
        "severity": "DIRECT",
    },
    {
        "claim": "Wolfenden answered all of father's communications",
        "evidence": "12 specific questions were sent to Wolfenden by certified letter — no response was received on any of them",
        "source_doc": "Correspondence Log",
        "page_ref": "2025",
        "severity": "DIRECT",
    },
]


async def main() -> None:
    await init_db()

    async with SessionLocal() as db:
        row = await db.execute(text("SELECT COUNT(*) FROM contradictions"))
        count = row.scalar()
        log.info("Current contradiction count: %d", count)

        if count >= 10:
            log.info("Already have >= 10 contradictions — skipping seed.")
            return

        for item in CONTRADICTIONS:
            db.add(Contradiction(**item))

        await db.commit()

        row = await db.execute(text("SELECT COUNT(*) FROM contradictions"))
        new_count = row.scalar()
        log.info("Seeded %d contradictions. Total now: %d", len(CONTRADICTIONS), new_count)


if __name__ == "__main__":
    asyncio.run(main())
