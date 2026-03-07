"""Seed 20 hearing prep checklist items across 4 categories.

Idempotent — if >= 20 rows already exist, skips insertion.

Usage:
    docker exec the-mcfd-files-backend-1 python3 -m app.loaders.seed_checklist
"""

import asyncio
import logging

from sqlalchemy import text

from app.models import ChecklistItem
from app.database import init_db, SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ITEMS = [
    # EVIDENCE
    {"category": "EVIDENCE", "item": "Print 2 copies of all FOI contradiction exhibits"},
    {"category": "EVIDENCE", "item": "Compile 25-contradiction Exhibit A (sworn statement vs video)"},
    {"category": "EVIDENCE", "item": "Prepare pharmacogenomic report exhibit (FOI pages 601-650)"},
    {"category": "EVIDENCE", "item": "Export trial package ZIP and save to USB"},
    {"category": "EVIDENCE", "item": "Verify 27-minute video is playable + clipped to key moments"},
    {"category": "EVIDENCE", "item": "Prepare timeline of Aug 4-7 directive chain (Muileboom → Burnstein → Wolfenden)"},
    # FILINGS
    {"category": "FILINGS", "item": "File response to any MCFD pre-trial applications"},
    {"category": "FILINGS", "item": "Confirm PC 19700 trial dates May 19-21 still scheduled"},
    {"category": "FILINGS", "item": "Serve any outstanding notices to Plessa Walden / PGS Law"},
    {"category": "FILINGS", "item": "File witness list if required by court"},
    {"category": "FILINGS", "item": "Confirm judicial review SC 064851 status"},
    # WITNESSES
    {"category": "WITNESSES", "item": "Prepare cross-examination questions for Nicki Wolfenden"},
    {"category": "WITNESSES", "item": "Prepare cross-examination questions for Tammy Newton"},
    {"category": "WITNESSES", "item": "Prepare questions for Jordon Muileboom re: directive chain"},
    {"category": "WITNESSES", "item": "Subpoena Robyn Burnstein if not already served"},
    {"category": "WITNESSES", "item": "Confirm attendance or arrange testimony for each witness"},
    # LOGISTICS
    {"category": "LOGISTICS", "item": "Book parking or transit to courthouse for May 19"},
    {"category": "LOGISTICS", "item": "Arrange care for Nadia on trial days May 19-21"},
    {"category": "LOGISTICS", "item": "Bring printed copy of all case numbers and court addresses"},
    {"category": "LOGISTICS", "item": "Charge laptop and backup battery — USB-C + USB-A"},
]


async def main() -> None:
    await init_db()

    async with SessionLocal() as db:
        row = await db.execute(text("SELECT COUNT(*) FROM checklist_items"))
        count = row.scalar()
        log.info("Current checklist count: %d", count)

        if count >= 20:
            log.info("Already have >= 20 checklist items — skipping seed.")
            return

        for item in ITEMS:
            db.add(ChecklistItem(**item))

        await db.commit()

        row = await db.execute(text("SELECT COUNT(*) FROM checklist_items"))
        new_count = row.scalar()
        log.info("Seeded %d items. Total now: %d", len(ITEMS), new_count)


if __name__ == "__main__":
    asyncio.run(main())
