"""Seed 6 additional taxpayer cost entries into cost_entries table.

Idempotent: checks for existing row by line_item before inserting.
Does NOT touch existing 9 entries.

Run with:
    docker exec the-mcfd-files-backend-1 python3 -m app.scripts.seed_costs_v2
"""

import asyncio

from sqlalchemy import select

from ..database import SessionLocal
from ..models import CostEntry

NEW_ENTRIES = [
    {
        "category": "enforcement",
        "line_item": "RCMP s.96 Mental Health Act wellness checks — 3 call-outs @ $800",
        "amount_per_unit": 800.00,
        "units": 3.0,
        "total": 2400.00,
        "source": "RCMP contract policing cost estimates",
        "source_url": "https://www.rcmp-grc.gc.ca/en/contract-policing",
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "supervision",
        "line_item": "Supervised visit coordinator/facilitator — 2x/week, 2hr, 30 weeks @ $75/hr",
        "amount_per_unit": 75.00,
        "units": 120.0,
        "total": 9000.00,
        "source": "BC MCFD contracted family services rates",
        "source_url": "https://www2.gov.bc.ca/gov/content/family-social-supports/foster-parenting",
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "administration",
        "line_item": "MCFD ATL (Muileboom) directive chain + oversight ~1hr/week @ $50/hr",
        "amount_per_unit": 50.00,
        "units": 30.0,
        "total": 1500.00,
        "source": "BC Public Service salary schedule, ATL",
        "source_url": None,
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "administration",
        "line_item": "Centralized Screening TL (Burnstein) removal direction ~5hrs @ $50/hr",
        "amount_per_unit": 50.00,
        "units": 5.0,
        "total": 250.00,
        "source": "BC Public Service salary schedule, TL",
        "source_url": None,
        "date_range_start": "2025-08-07",
        "date_range_end": "2025-08-07",
    },
    {
        "category": "court",
        "line_item": "BC Provincial Court pre-trial appearances — 6 appearances @ $2,500",
        "amount_per_unit": 2500.00,
        "units": 6.0,
        "total": 15000.00,
        "source": "BC Ministry of AG court admin cost estimates",
        "source_url": "https://www2.gov.bc.ca/gov/content/justice/courthouse-services",
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "enforcement",
        "line_item": "MCFD case documentation overhead — 30min/day SW admin @ $35/hr x 214 days",
        "amount_per_unit": 17.50,
        "units": 214.0,
        "total": 3745.00,
        "source": "BC Public Service salary schedule, SW",
        "source_url": None,
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
]


async def seed():
    async with SessionLocal() as db:
        inserted = 0
        skipped = 0
        for entry in NEW_ENTRIES:
            existing = (await db.execute(
                select(CostEntry).where(CostEntry.line_item == entry["line_item"])
            )).scalars().first()
            if existing:
                print(f"  SKIP (exists): {entry['line_item'][:60]}")
                skipped += 1
            else:
                db.add(CostEntry(**entry))
                print(f"  INSERT: {entry['line_item'][:60]}")
                inserted += 1

        await db.commit()
        new_total = sum(e["total"] for e in NEW_ENTRIES)
        print(f"\nDone: {inserted} inserted, {skipped} skipped.")
        print(f"New entries total: ${new_total:,.2f}")


if __name__ == "__main__":
    asyncio.run(seed())
