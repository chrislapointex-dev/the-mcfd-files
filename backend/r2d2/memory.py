"""R2Memory — the main interface for the R2-D2 memory system."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .routing import route
from . import storage

log = logging.getLogger(__name__)


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
