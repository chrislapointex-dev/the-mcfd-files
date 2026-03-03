"""R2Memory — the main interface for the R2-D2 memory system."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .routing import route
from . import storage

log = logging.getLogger(__name__)

# ── Compaction constants ───────────────────────────────────────────────────────

COMPACT_THRESHOLD = 30   # trigger when HIPPOCAMPUS has more than this many entries
COMPACT_BATCH     = 15   # compact this many oldest entries per run
SKIP_CATEGORIES   = {"session_summary", "compaction_event"}  # never re-compact these


class R2Memory:
    """Persistent memory engine. All methods degrade gracefully if DB is unavailable."""

    def __init__(self, db: AsyncSession | None = None, user_id: str = "default"):
        self.db = db
        self.user_id = user_id

    # ── Write ──────────────────────────────────────────────────────────────────

    async def save(
        self,
        key: str,
        value: Any,
        *,
        category: str = "note",
        region: str | None = None,
        context: str | None = None,
        confidence: float = 1.0,
        source: str | None = None,
    ) -> int:
        """Save a memory. Region is auto-routed from category if not specified."""
        if region is None:
            region = route(category)

        if not isinstance(value, dict):
            value = {"data": value}

        kwargs = dict(
            user_id=self.user_id,
            region=region,
            category=category,
            key=key,
            value=value,
            context=context,
            confidence=confidence,
            source=source,
        )

        try:
            if self.db is not None:
                mem_id = await storage.pg_save(self.db, **kwargs)
                log.debug("Memory saved [%s/%s] id=%d", region, key, mem_id)
                return mem_id
        except Exception as exc:
            log.warning("DB save failed, using fallback: %s", exc)

        return storage.fallback_save(**kwargs)

    # ── Read ───────────────────────────────────────────────────────────────────

    async def recall(
        self,
        *,
        region: str | None = None,
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Recall memories, newest first."""
        kwargs = dict(
            user_id=self.user_id,
            region=region,
            category=category,
            limit=limit,
        )
        try:
            if self.db is not None:
                return await storage.pg_recall(self.db, **kwargs)
        except Exception as exc:
            log.warning("DB recall failed, using fallback: %s", exc)

        return storage.fallback_recall(**kwargs)

    async def get_context(self, limit_per_region: int = 5) -> dict[str, list[dict]]:
        """Return recent memories grouped by region for context injection."""
        from .routing import REGIONS
        context: dict[str, list[dict]] = {}
        for region in REGIONS:
            memories = await self.recall(region=region, limit=limit_per_region)
            if memories:
                context[region] = memories
        return context

    # ── Convenience ────────────────────────────────────────────────────────────

    async def log_search(self, query: str, result_count: int, filters: dict | None = None) -> int:
        """Record a search query to HIPPOCAMPUS."""
        return await self.save(
            key=f"search:{query[:120]}",
            value={"query": query, "result_count": result_count, "filters": filters or {}},
            category="search_query",
            source="search_router",
        )

    async def log_view(self, decision_id: int, title: str, citation: str | None) -> int:
        """Record a viewed decision to HIPPOCAMPUS."""
        return await self.save(
            key=f"viewed:{decision_id}",
            value={"id": decision_id, "title": title, "citation": citation},
            category="viewed_decision",
            source="detail_router",
        )

    async def flag(self, key: str, reason: str, source: str | None = None) -> int:
        """Add a red flag to AMYGDALA."""
        return await self.save(
            key=key,
            value={"reason": reason},
            category="red_flag",
            region="AMYGDALA",
            confidence=0.9,
            source=source,
        )

    async def set_goal(self, key: str, description: str) -> int:
        """Record a research goal to PREFRONTAL."""
        return await self.save(
            key=key,
            value={"description": description},
            category="goal",
            region="PREFRONTAL",
        )

    # ── Compaction ─────────────────────────────────────────────────────────────

    async def compact(self) -> int:
        """Compress the oldest HIPPOCAMPUS entries into session summaries.

        Groups the oldest COMPACT_BATCH entries by date, writes one
        session_summary per date group, deletes the originals, then
        records a compaction_event.  Never touches AMYGDALA, PREFRONTAL,
        or entries already categorised as session_summary/compaction_event.

        Returns the number of entries compacted.
        """
        if self.db is None:
            return 0

        from app.models import Memory
        from sqlalchemy import delete, func, select

        # Fetch oldest compactable entries
        stmt = (
            select(Memory)
            .where(
                Memory.user_id == self.user_id,
                Memory.region == "HIPPOCAMPUS",
                ~Memory.category.in_(list(SKIP_CATEGORIES)),
            )
            .order_by(Memory.created_at.asc())
            .limit(COMPACT_BATCH)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        if not rows:
            return 0

        # Group by calendar date (YYYY-MM-DD)
        by_date: dict[str, list] = {}
        for row in rows:
            date_key = row.created_at.strftime("%Y-%m-%d") if row.created_at else "unknown"
            by_date.setdefault(date_key, []).append(row)

        total_compacted = 0

        for date_key, date_rows in by_date.items():
            # Build a plain-text summary from entry values
            parts: list[str] = []
            for row in date_rows:
                v = row.value or {}
                if row.category == "search_query":
                    q = v.get("query", "")
                    if q:
                        parts.append(f"Searched '{q}'")
                elif row.category == "viewed_decision":
                    title = v.get("title", "")
                    if title:
                        parts.append(f"Viewed '{title}'")
                elif row.category == "qa":
                    q = v.get("question", "")
                    if q:
                        parts.append(f"Asked '{q[:60]}'")
                else:
                    parts.append(row.key[:80])

            summary_text = ". ".join(parts) if parts else f"Session on {date_key}"
            ids_to_delete = [r.id for r in date_rows]

            # Write summary entry
            await self.save(
                key=f"summary:{date_key}:{len(date_rows)}",
                value={
                    "summary": summary_text,
                    "original_count": len(date_rows),
                    "date_range": date_key,
                },
                category="session_summary",
                region="HIPPOCAMPUS",
                source="auto_compaction",
            )

            # Delete the originals
            await self.db.execute(
                delete(Memory).where(Memory.id.in_(ids_to_delete))
            )
            await self.db.commit()

            total_compacted += len(date_rows)

        # Record the compaction event
        await self.save(
            key=f"compact:{datetime.now(timezone.utc).isoformat()}",
            value={
                "compacted_count": total_compacted,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            category="compaction_event",
            region="HIPPOCAMPUS",
            source="auto_compaction",
        )

        log.info(
            "Compacted %d HIPPOCAMPUS entries for user %s",
            total_compacted, self.user_id,
        )
        return total_compacted

    async def compact_if_needed(self) -> int:
        """Compact HIPPOCAMPUS if entry count exceeds COMPACT_THRESHOLD."""
        if self.db is None:
            return 0

        from app.models import Memory
        from sqlalchemy import func, select

        count = (
            await self.db.execute(
                select(func.count())
                .select_from(Memory)
                .where(
                    Memory.user_id == self.user_id,
                    Memory.region == "HIPPOCAMPUS",
                    ~Memory.category.in_(list(SKIP_CATEGORIES)),
                )
            )
        ).scalar_one()

        if count > COMPACT_THRESHOLD:
            return await self.compact()
        return 0
