"""Seed taxpayer cost entries into cost_entries table.

Idempotent: clears existing rows before inserting, so safe to re-run.

Run with:
    docker exec the-mcfd-files-backend-1 python3 -m app.scripts.seed_costs
"""

import asyncio

from sqlalchemy import delete

from ..database import SessionLocal
from ..models import CostEntry

COST_ENTRIES = [
    {
        "category": "supervision",
        "line_item": "SW salary cost/day (~$85k/yr BC Gov) × 214 supervision days",
        "amount_per_unit": 232.88,
        "units": 214.0,
        "total": 49836.32,
        "source": "BC Public Service salary schedule",
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "supervision",
        "line_item": "ICS supervision visits ~3x/week @ $150/visit",
        "amount_per_unit": 150.00,
        "units": 90.0,
        "total": 13500.00,
        "source": "MCFD contracted service rates",
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "placement",
        "line_item": "Foster/placement care $65/day BC base rate × 214 days",
        "amount_per_unit": 65.00,
        "units": 214.0,
        "total": 13910.00,
        "source": "BC MCFD foster care rates schedule",
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "legal",
        "line_item": "Director legal counsel ~$300/hr, estimated 100hrs",
        "amount_per_unit": 300.00,
        "units": 100.0,
        "total": 30000.00,
        "source": "BC Law Society published rate ranges",
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "court",
        "line_item": "BC Provincial Court ~$10,000/day × 3 hearing days",
        "amount_per_unit": 10000.00,
        "units": 3.0,
        "total": 30000.00,
        "source": "BC Ministry of AG court admin cost estimates",
        "date_range_start": "2026-05-19",
        "date_range_end": "2026-05-21",
    },
    {
        "category": "administration",
        "line_item": "TL (T. Newton) case mgmt ~2hrs/wk @ $45/hr × 30 weeks",
        "amount_per_unit": 45.00,
        "units": 60.0,
        "total": 2700.00,
        "source": "BC Public Service salary schedule, TL",
        "date_range_start": "2025-08-07",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "administration",
        "line_item": "FOI processing CFD-2025-53478 — 40hrs @ $35/hr",
        "amount_per_unit": 35.00,
        "units": 40.0,
        "total": 1400.00,
        "source": "BC FOIPPA processing cost estimates",
        "date_range_start": "2025-08-15",
        "date_range_end": "2026-02-25",
    },
    {
        "category": "administration",
        "line_item": "OIPC INV-F-26-00220 staff cost — 40hrs @ $45/hr",
        "amount_per_unit": 45.00,
        "units": 40.0,
        "total": 1800.00,
        "source": "OIPC BC operating budget",
        "date_range_start": "2026-01-21",
        "date_range_end": "2026-03-09",
    },
    {
        "category": "administration",
        "line_item": "FOIPPA breach — Wolfenden/Dolson disclosure (March 9 2026) — DOCUMENTED VIOLATION",
        "amount_per_unit": 0.00,
        "units": 1.0,
        "total": 0.00,
        "source": "Voicemail transcript March 9 2026 — documented breach on record",
        "date_range_start": "2026-03-09",
        "date_range_end": "2026-03-09",
    },
]


async def seed():
    async with SessionLocal() as db:
        # Clear existing rows (idempotent re-run)
        await db.execute(delete(CostEntry))
        await db.flush()

        for entry in COST_ENTRIES:
            db.add(CostEntry(**entry))

        await db.commit()
        total = sum(e["total"] for e in COST_ENTRIES)
        print(f"Seeded {len(COST_ENTRIES)} cost entries. Grand total: ${total:,.2f}")


if __name__ == "__main__":
    asyncio.run(seed())
