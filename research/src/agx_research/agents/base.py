"""The research agent contract.

Agents are researchers, not decision makers (Principle 6 / the vision
document's Agents Philosophy). A `ResearchAgent` produces `ResearchFinding`
objects — an observation plus a proposed, falsifiable hypothesis statement
— and nothing else. There is intentionally no method here that writes to a
`KnowledgeStore`; turning a finding into a promoted `KnowledgeObject`
requires it to survive the full hypothesis lifecycle in
`agx_research.hypotheses` and `agx_research.validation` first.

Agents consume a `DatasetSnapshot`, not a live `DataProvider` — every
finding is reproducible against the exact, content-hashed data the agent
saw, and carries `provenance` linking back to that snapshot (and whatever
features it used), which is what makes "why does this finding exist"
answerable later instead of just asserted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance


class ResearchFinding(BaseModel):
    """An agent's proposed observation — not yet a hypothesis, not yet knowledge."""

    id: str = Field(default_factory=lambda: new_id("finding"))
    agent_name: str
    agent_version: str
    observed_at: date
    observation: str
    proposed_hypothesis_statement: str
    affected_assets: list[str]
    horizon: Horizon
    evidence: list[str] = Field(default_factory=list)
    provenance: Provenance


class ResearchAgent(ABC):
    """One responsibility per agent; agents propose findings, never publish knowledge."""

    name: str
    version: str = "0.1.0"

    @abstractmethod
    def research(self, snapshot: DatasetSnapshot) -> list[ResearchFinding]:
        """Analyze `snapshot` (a point-in-time dataset) and propose zero or more findings."""
