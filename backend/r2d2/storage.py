"""PostgreSQL storage for R2-D2 memory, with JSON file fallback."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

FALLBACK_PATH = Path("data/r2d2_memory.json")


# ── PostgreSQL helpers ─────────────────────────────────────────────────────────


async def pg_save(
    db: AsyncSession,
    *,
    user_id: str,
    region: str,
    category: str,
    key: str,
    value: dict,
    context: str | None,
    confidence: float,
    source: str | None,
) -> int:
    """Upsert a memory row. Returns the row id."""
    from app.models import Memory  # local import avoids circular dep

    stmt = pg_insert(Memory).values(
        user_id=user_id,
        region=region,
        category=category,
        key=key,
        value=value,
        context=context,
        confidence=confidence,
        source=source,
    )
    stmt = stmt.on_conflict_do_update(
        # No unique constraint on key alone — use insert then select approach
        # We do a manual upsert by key + user_id + region
        index_elements=["id"],  # will never conflict — always insert
        set_={"value": stmt.excluded.value},
    )
    # Use plain insert (no upsert by key) — let memory grow, recall queries filter
    result = await db.execute(
        pg_insert(Memory).values(
            user_id=user_id,
            region=region,
            category=category,
            key=key,
            value=value,
            context=context,
            confidence=confidence,
            source=source,
        ).returning(Memory.id)
    )
    await db.commit()
    row = result.fetchone()
    return row[0] if row else -1


async def pg_recall(
    db: AsyncSession,
    *,
    user_id: str,
    region: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Fetch recent memories, optionally filtered by region/category."""
    from app.models import Memory

    stmt = select(Memory).where(Memory.user_id == user_id)
    if region:
        stmt = stmt.where(Memory.region == region)
    if category:
        stmt = stmt.where(Memory.category == category)
    stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    # Update accessed_at + access_count for fetched rows
    if rows:
        ids = [r.id for r in rows]
        await db.execute(
            update(Memory)
            .where(Memory.id.in_(ids))
            .values(
                accessed_at=datetime.now(timezone.utc),
                access_count=Memory.access_count + 1,
            )
        )
        await db.commit()

    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "region": row.region,
        "category": row.category,
        "key": row.key,
        "value": row.value,
        "context": row.context,
        "confidence": row.confidence,
        "source": row.source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "accessed_at": row.accessed_at.isoformat() if row.accessed_at else None,
        "access_count": row.access_count,
    }


# ── JSON fallback ──────────────────────────────────────────────────────────────


def _load_fallback() -> list[dict]:
    if not FALLBACK_PATH.exists():
        return []
    try:
        return json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_fallback(records: list[dict]) -> None:
    FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    FALLBACK_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def fallback_save(
    *,
    user_id: str,
    region: str,
    category: str,
    key: str,
    value: dict,
    context: str | None,
    confidence: float,
    source: str | None,
) -> int:
    records = _load_fallback()
    new_id = (max((r["id"] for r in records), default=0)) + 1
    records.append({
        "id": new_id,
        "user_id": user_id,
        "region": region,
        "category": category,
        "key": key,
        "value": value,
        "context": context,
        "confidence": confidence,
        "source": source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "accessed_at": datetime.now(timezone.utc).isoformat(),
        "access_count": 0,
    })
    _save_fallback(records)
    return new_id


def fallback_recall(
    *,
    user_id: str,
    region: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> list[dict]:
    records = _load_fallback()
    filtered = [
        r for r in records
        if r["user_id"] == user_id
        and (region is None or r["region"] == region)
        and (category is None or r["category"] == category)
    ]
    return list(reversed(filtered))[:limit]
