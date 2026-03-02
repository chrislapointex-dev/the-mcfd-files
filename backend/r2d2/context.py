"""ContextBuilder — formats brain regions into a human-readable briefing."""

from .memory import R2Memory


class ContextBuilder:
    """Builds a concise briefing string from active memory regions."""

    def __init__(self, memory: R2Memory):
        self.memory = memory

    async def build(self, limit_per_region: int = 5) -> str:
        """Return a multi-line briefing of relevant memory."""
        ctx = await self.memory.get_context(limit_per_region=limit_per_region)
        if not ctx:
            return ""

        lines = ["=== R2 MEMORY CONTEXT ==="]

        region_order = ["CORTEX", "PREFRONTAL", "AMYGDALA", "HIPPOCAMPUS", "NEOCORTEX"]
        for region in region_order:
            memories = ctx.get(region)
            if not memories:
                continue
            lines.append(f"\n[{region}]")
            for m in memories:
                val = m["value"]
                key = m["key"]
                cat = m["category"]
                if cat == "search_query":
                    q = val.get("query", key)
                    n = val.get("result_count", "?")
                    lines.append(f"  search: {q!r} → {n} results")
                elif cat == "viewed_decision":
                    title = val.get("title", key)
                    cit = val.get("citation") or ""
                    lines.append(f"  viewed: {title} {cit}".rstrip())
                elif cat == "red_flag":
                    lines.append(f"  FLAG: {key} — {val.get('reason', '')}")
                elif cat in ("goal", "plan", "next_step"):
                    lines.append(f"  {cat}: {val.get('description', key)}")
                else:
                    # Generic fallback
                    data = val.get("data") or str(val)
                    lines.append(f"  {key}: {str(data)[:120]}")

        lines.append("\n=== END CONTEXT ===")
        return "\n".join(lines)

    async def recent_searches(self, n: int = 10) -> list[str]:
        """Return the last n search queries as strings."""
        memories = await self.memory.recall(category="search_query", limit=n)
        return [m["value"].get("query", m["key"]) for m in memories]
