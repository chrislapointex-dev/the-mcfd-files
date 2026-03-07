"""GET /api/checklist — all items grouped by category (dict)
PATCH /api/checklist/{id} — update done and/or notes
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..models import ChecklistItem

router = APIRouter(prefix="/api/checklist", tags=["checklist"])

CATEGORY_ORDER = ["EVIDENCE", "FILINGS", "WITNESSES", "LOGISTICS"]


class ChecklistItemOut(BaseModel):
    id: int
    category: str
    item: str
    done: bool
    notes: Optional[str]
    due_date: Optional[str]
    created_at: str


class ChecklistPatch(BaseModel):
    done: Optional[bool] = None    # if provided, set done to this value
    notes: Optional[str] = None    # if provided, update notes


def _serialize(r: ChecklistItem) -> ChecklistItemOut:
    return ChecklistItemOut(
        id=r.id,
        category=r.category,
        item=r.item,
        done=r.done,
        notes=r.notes,
        due_date=r.due_date.isoformat() if r.due_date else None,
        created_at=r.created_at.isoformat(),
    )


@router.get("")
async def list_checklist(db: AsyncSession = Depends(get_db)):
    """Return all items grouped by category."""
    rows = (await db.execute(
        select(ChecklistItem).order_by(ChecklistItem.category, ChecklistItem.id)
    )).scalars().all()

    grouped: dict[str, list] = {cat: [] for cat in CATEGORY_ORDER}
    for r in rows:
        cat = r.category if r.category in grouped else r.category
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(_serialize(r).model_dump())

    # Only include categories that have items
    return {k: v for k, v in grouped.items() if v}


@router.patch("/{item_id}", response_model=ChecklistItemOut)
async def update_item(item_id: int, body: ChecklistPatch, db: AsyncSession = Depends(get_db)):
    """Update done and/or notes on a checklist item."""
    row = await db.get(ChecklistItem, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    if body.done is not None:
        row.done = body.done
    if body.notes is not None:
        row.notes = body.notes
    await db.commit()
    await db.refresh(row)
    return _serialize(row)
