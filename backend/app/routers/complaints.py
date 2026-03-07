"""GET /api/complaints — all complaints sorted by filed_date desc
PATCH /api/complaints/{id} — update status, notes, last_update
"""

from datetime import date as DateType
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..models import Complaint

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


class ComplaintOut(BaseModel):
    id: int
    body: str
    file_ref: Optional[str]
    filed_date: Optional[str]
    status: str
    last_update: Optional[str]
    notes: Optional[str]
    created_at: str


class ComplaintPatch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    last_update: Optional[str] = None


def _serialize(r: Complaint) -> ComplaintOut:
    return ComplaintOut(
        id=r.id,
        body=r.body,
        file_ref=r.file_ref,
        filed_date=r.filed_date.isoformat() if r.filed_date else None,
        status=r.status,
        last_update=r.last_update.isoformat() if r.last_update else None,
        notes=r.notes,
        created_at=r.created_at.isoformat(),
    )


@router.get("", response_model=list[ComplaintOut])
async def list_complaints(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Complaint).order_by(Complaint.filed_date.desc().nullslast(), Complaint.id.desc())
    )).scalars().all()
    return [_serialize(r) for r in rows]


@router.patch("/{complaint_id}", response_model=ComplaintOut)
async def update_complaint(complaint_id: int, body: ComplaintPatch, db: AsyncSession = Depends(get_db)):
    row = await db.get(Complaint, complaint_id)
    if not row:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if body.status is not None:
        row.status = body.status
    if body.notes is not None:
        row.notes = body.notes
    if body.last_update is not None:
        try:
            row.last_update = DateType.fromisoformat(body.last_update)
        except ValueError:
            raise HTTPException(status_code=422, detail="last_update must be YYYY-MM-DD")
    await db.commit()
    await db.refresh(row)
    return _serialize(row)
