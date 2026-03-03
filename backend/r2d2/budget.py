"""Context budget manager — token accounting for /api/ask."""

import os

# ── Constants ─────────────────────────────────────────────────────────────────

PINNED_REGIONS   = {"AMYGDALA", "PREFRONTAL", "CORTEX"}
WEIGHTED_REGIONS = {"NEOCORTEX": 0.40, "HIPPOCAMPUS": 0.30}
OUTPUT_RESERVE   = 4096
MEMORY_BUDGET    = 2000
AVG_TOKENS_PER_CHUNK = 300

MODEL_WINDOWS = {
    "claude-sonnet-4-6": 200_000,
    "claude-opus-4-6":   200_000,
}
DEFAULT_WINDOW = 200_000


# ── Helpers ───────────────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Rough token estimate: word count × 1.3."""
    return int(len(text.split()) * 1.3)


# ── Budget class ──────────────────────────────────────────────────────────────

class ContextBudget:
    def __init__(self):
        model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.max_tokens = MODEL_WINDOWS.get(model, DEFAULT_WINDOW)

    def allocate(
        self,
        system_prompt: str,
        memory_items: list[dict],
        available_chunks: int,
    ) -> dict:
        max_tokens = self.max_tokens

        # Token accounting
        system_prompt_tokens = estimate_tokens(system_prompt)
        safety_margin = int(max_tokens * 0.05)
        chunk_budget = (
            max_tokens
            - system_prompt_tokens
            - OUTPUT_RESERVE
            - safety_margin
            - MEMORY_BUDGET
        )
        max_chunks = min(available_chunks, max(0, chunk_budget // AVG_TOKENS_PER_CHUNK))

        # Group memory items by region
        by_region: dict[str, list[dict]] = {}
        for item in memory_items:
            r = item.get("region", "HIPPOCAMPUS")
            by_region.setdefault(r, []).append(item)

        memory_included: dict[str, int] = {}
        memory_dropped: dict[str, int] = {}
        pinned_tokens = 0

        # Pinned pass — always include AMYGDALA / PREFRONTAL / CORTEX
        for region in PINNED_REGIONS:
            items = by_region.get(region, [])
            if items:
                memory_included[region] = len(items)
                for item in items:
                    pinned_tokens += estimate_tokens(
                        str(item.get("value", "")) + " " + str(item.get("context", ""))
                    )

        # Weighted pass — NEOCORTEX (40%) and HIPPOCAMPUS (30%) of remaining budget
        remaining = max(MEMORY_BUDGET - pinned_tokens, 0)
        for region, weight in WEIGHTED_REGIONS.items():
            items = by_region.get(region, [])
            if not items:
                continue
            region_alloc = int(remaining * weight)
            used = 0
            included = 0
            dropped = 0
            for item in items:  # assumed newest-first from get_context
                cost = estimate_tokens(
                    str(item.get("value", "")) + " " + str(item.get("context", ""))
                )
                if used + cost <= region_alloc:
                    used += cost
                    included += 1
                else:
                    dropped += 1
            if included:
                memory_included[region] = included
            if dropped:
                memory_dropped[region] = dropped

        utilization_pct = round(
            (
                system_prompt_tokens
                + OUTPUT_RESERVE
                + safety_margin
                + MEMORY_BUDGET
                + max_chunks * AVG_TOKENS_PER_CHUNK
            )
            / max_tokens
            * 100,
            1,
        )

        return {
            "max_tokens": max_tokens,
            "system_prompt_tokens": system_prompt_tokens,
            "output_reserve": OUTPUT_RESERVE,
            "safety_margin": safety_margin,
            "memory_budget": MEMORY_BUDGET,
            "memory_included": memory_included,
            "memory_dropped": memory_dropped,
            "chunk_budget": chunk_budget,
            "max_chunks": max_chunks,
            "utilization_pct": utilization_pct,
        }
