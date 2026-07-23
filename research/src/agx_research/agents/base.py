"""The research agent contract.

Agents are researchers, not decision makers (Principle 6 / the vision
document's Agents Philosophy). A `ResearchAgent` produces `ResearchFinding`
objects — an observation plus a proposed, falsifiable hypothesis statement
— and nothing else. There is intentionally no method here that writes to a
`KnowledgeStore`; turning a finding into a promoted `KnowledgeObject`
requires it to survive the full hypothesis lifecycle in
`agx_research.hypotheses` and `agx_research.validation` first.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.data.provider import DataProvider


class ResearchFinding(BaseModel):
    """An agent's proposed observation — not yet a hypothesis, not yet knowledge."""

    agent_name: str
    observed_at: date
    observation: str
    proposed_hypothesis_statement: str
    affected_assets: list[str]
    horizon: Horizon
    evidence: list[str] = Field(default_factory=list)


class ResearchAgent(ABC):
    """One responsibility per agent; agents propose findings, never publish knowledge."""

    name: str

    @abstractmethod
    def research(self, data_provider: DataProvider, as_of: date) -> list[ResearchFinding]:
        """Analyze data available as of `as_of` and propose zero or more findings."""
