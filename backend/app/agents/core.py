"""Agent core — registry, status tracking, result dataclass."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AgentStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    SCHEDULED = "SCHEDULED"


@dataclass
class AgentResult:
    agent_name: str
    status: AgentStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_found: int = 0
    records_added: int = 0
    errors: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


# Global registry: agent_name → AgentResult
_registry: dict[str, AgentResult] = {}


def register_agent(name: str) -> AgentResult:
    """Register an agent if not already present; return its result record."""
    if name not in _registry:
        _registry[name] = AgentResult(agent_name=name, status=AgentStatus.IDLE)
    return _registry[name]


def update_status(name: str, result: AgentResult) -> None:
    """Overwrite the registry entry for this agent."""
    _registry[name] = result


def get_all_agents() -> list[AgentResult]:
    """Return all registered agents."""
    return list(_registry.values())


def get_agent_status(name: str) -> Optional[AgentResult]:
    """Return the result for a single agent, or None if not registered."""
    return _registry.get(name)
