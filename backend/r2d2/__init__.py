"""R2-D2 Memory System for The MCFD Files.

Provides persistent context across research sessions using five brain regions:
  CORTEX       — active working memory (current session focus)
  HIPPOCAMPUS  — recent search history and session events
  NEOCORTEX    — long-term knowledge (case patterns, entities)
  AMYGDALA     — alerts, red flags, watch items
  PREFRONTAL   — research goals and plans
"""

from .memory import R2Memory
from .routing import REGIONS

__all__ = ["R2Memory", "REGIONS"]
