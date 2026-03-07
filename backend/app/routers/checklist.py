"""GET /api/checklist — list all checklist items ordered by category + id
PATCH /api/checklist/{id}/toggle — flip done bool
PATCH /api/checklist/{id}/notes  — update notes field
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..models import ChecklistItem

router = APIRouter(prefix="/api/checklist", tags=["checklist"])


class ChecklistItemOut(BaseModel):
    id: int
    category: str
    item: str
    done: bool
    notes: Optional[str]
    due_date: Optional[str]
    created_at: str


class NotesBody(BaseModel):
    notes: Optional[str]


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


@router.get("", response_model=list[ChecklistItemOut])
async def list_checklist(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ChecklistItem).order_by(ChecklistItem.category, ChecklistItem.id)
    )).scalars().all()
    return [_serialize(r) for r in rows]


@router.patch("/{item_id}/toggle", response_model=ChecklistItemOut)
async def toggle_item(item_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(ChecklistItem, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    row.done = not row.done
    await db.commit()
    await db.refresh(row)
    return _serialize(row)


@router.patch("/{item_id}/notes", response_model=ChecklistItemOut)
async def update_notes(item_id: int, body: NotesBody, db: AsyncSession = Depends(get_db)):
    row = await db.get(ChecklistItem, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    row.notes = body.notes
    await db.commit()
    await db.refresh(row)
    return _serialize(row)
