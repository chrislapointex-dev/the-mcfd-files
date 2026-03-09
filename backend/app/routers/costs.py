"""GET /api/costs — Taxpayer cost calculator.

Returns all cost entries grouped by category with subtotals and grand total.
"""

from datetime import datetime, timezone
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import CostEntry

router = APIRouter(prefix="/api/costs", tags=["costs"])


@router.get("")
async def get_costs(db: AsyncSession = Depends(get_db)):
    """Return all cost entries grouped by category with subtotals and grand total."""
    rows = (await db.execute(
        select(CostEntry).order_by(CostEntry.category, CostEntry.id)
    )).scalars().all()

    entries = []
    by_category = defaultdict(lambda: {"subtotal": 0.0, "items": []})

    for r in rows:
        item = {
            "id": r.id,
            "category": r.category,
            "line_item": r.line_item,
            "amount_per_unit": r.amount_per_unit,
            "units": r.units,
            "total": r.total,
            "source": r.source,
            "date_range_start": r.date_range_start,
            "date_range_end": r.date_range_end,
        }
        entries.append(item)
        by_category[r.category]["subtotal"] += r.total
        by_category[r.category]["items"].append(item)

    grand_total = sum(r.total for r in rows)

    return {
        "entries": entries,
        "by_category": dict(by_category),
        "grand_total": grand_total,
        "days_in_care": 214,
        "case_ref": "PC 19700 — LaPointe, Christopher",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "All figures based on publicly available BC government rates and published estimates. "
            "Actual costs may be higher."
        ),
    }
