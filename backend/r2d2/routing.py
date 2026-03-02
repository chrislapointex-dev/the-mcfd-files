"""Routing rules: map info types to brain regions."""

REGIONS = {
    "CORTEX": "Active working memory — current session focus and state",
    "HIPPOCAMPUS": "Recent history — searches, viewed decisions, session events",
    "NEOCORTEX": "Long-term knowledge — patterns, entities, case facts",
    "AMYGDALA": "Alerts and red flags — flagged cases, watch items",
    "PREFRONTAL": "Goals and plans — research objectives, next steps",
}

# Category → region routing rules
CATEGORY_ROUTES: dict[str, str] = {
    "search_query": "HIPPOCAMPUS",
    "viewed_decision": "HIPPOCAMPUS",
    "session_start": "HIPPOCAMPUS",
    "session_end": "HIPPOCAMPUS",
    "case_pattern": "NEOCORTEX",
    "entity": "NEOCORTEX",
    "legal_concept": "NEOCORTEX",
    "red_flag": "AMYGDALA",
    "alert": "AMYGDALA",
    "watch_case": "AMYGDALA",
    "goal": "PREFRONTAL",
    "plan": "PREFRONTAL",
    "next_step": "PREFRONTAL",
    "focus": "CORTEX",
    "active_filter": "CORTEX",
}


def route(category: str) -> str:
    """Return the region for a given category. Defaults to HIPPOCAMPUS."""
    return CATEGORY_ROUTES.get(category, "HIPPOCAMPUS")
