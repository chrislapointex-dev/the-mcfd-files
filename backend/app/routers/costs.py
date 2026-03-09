"""GET /api/costs — Taxpayer cost calculator.

Returns all cost entries grouped by category with subtotals and grand total.
"""

from datetime import datetime, timezone
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import CostEntry

router = APIRouter(prefix="/api/costs", tags=["costs"])


@router.get("/scale")
async def get_cost_scale(db: AsyncSession = Depends(get_db)):
    """Return BC-wide scale projection based on this case's documented costs."""
    result = await db.execute(select(func.sum(CostEntry.total)))
    this_case_total = result.scalar() or 0.0

    return {
        "this_case": {
            "total": this_case_total,
            "days": 214,
            "case_ref": "PC 19700 — LaPointe, Christopher",
        },
        "estimated_true_total": {
            "low": 285000.00,
            "high": 420000.00,
            "note": (
                "Documented costs represent a conservative minimum. True cost including "
                "psychological assessments, private investigator activity, child therapy, "
                "VAC benefit misclassification impact, and CRA dispute costs is estimated "
                "significantly higher."
            ),
        },
        "bc_scale": {
            "children_in_care": 5000,
            "source": "BC MCFD Annual Service Plan 2024-25",
            "source_url": "https://www2.gov.bc.ca/gov/content/family-social-supports/foster-parenting",
            "projected_annual_low": 1425000000.00,
            "projected_annual_high": 2100000000.00,
            "note": "Provincial projection based on per-family estimates × 5,000 children in care",
        },
        "kamloops_region": {
            "note": "Thompson Nicola region — estimated 300-500 active files",
            "projected_annual_low": 85500000.00,
            "projected_annual_high": 210000000.00,
        },
        "disclaimer": (
            "All projections based on publicly available data and documented case costs. "
            "Actual costs may be significantly higher."
        ),
    }


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
            "source_url": r.source_url,
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
