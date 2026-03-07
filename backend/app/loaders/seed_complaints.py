"""Seed known complaints into the complaints table.

Idempotent — if >= 6 rows already exist, skips insertion.

Usage:
    docker exec the-mcfd-files-backend-1 python3 -m app.loaders.seed_complaints
"""

import asyncio
import logging
from datetime import date

from sqlalchemy import text

from app.models import Complaint
from app.database import init_db, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

COMPLAINTS = [
    {
        "body": "OIPC",
        "file_ref": "INV-F-26-00220",
        "filed_date": date(2026, 1, 21),
        "status": "ACTIVE",
        "notes": "Incomplete FOI — 886 pages missing. Investigator J. Campbell.",
    },
    {
        "body": "BC Ombudsperson",
        "file_ref": None,
        "filed_date": date(2025, 10, 1),
        "status": "FILED",
        "notes": "Filed complaint re MCFD conduct",
    },
    {
        "body": "RCMP",
        "file_ref": None,
        "filed_date": date(2025, 10, 1),
        "status": "FILED",
        "notes": "Filed complaint re removal conduct",
    },
    {
        "body": "Representative for Children and Youth",
        "file_ref": None,
        "filed_date": date(2025, 10, 1),
        "status": "FILED",
        "notes": "Filed referral re Nadia's welfare",
    },
    {
        "body": "CRA",
        "file_ref": "GB260151737209",
        "filed_date": date(2026, 1, 1),
        "status": "ACTIVE",
        "notes": "Notice of Objection — VAC benefits incorrectly taxed",
    },
    {
        "body": "Health Canada",
        "file_ref": None,
        "filed_date": date(2025, 9, 1),
        "status": "FILED",
        "notes": "Pharmacist Dayton escalated re WGS report exclusion",
    },
]


async def main() -> None:
    await init_db()

    async with SessionLocal() as db:
        row = await db.execute(text("SELECT COUNT(*) FROM complaints"))
        count = row.scalar()
        log.info("Current complaint count: %d", count)

        if count >= 6:
            log.info("Already have >= 6 complaints — skipping seed.")
            return

        for item in COMPLAINTS:
            db.add(Complaint(**item))

        await db.commit()

        row = await db.execute(text("SELECT COUNT(*) FROM complaints"))
        new_count = row.scalar()
        log.info("Seeded %d complaints. Total now: %d", len(COMPLAINTS), new_count)


if __name__ == "__main__":
    asyncio.run(main())
