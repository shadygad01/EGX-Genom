"""The first-class representation of one research run.

The vision document's Core Mission is "every trading day the platform must
answer one question" — but nothing recorded which agents (at which code
versions) ran, against which dataset, on a given day. A `ResearchCycle` is
the object that makes that auditable: it is what `HypothesisRepository` and
`KnowledgeStore` entries should eventually be traceable back to.

Deliberately minimal: no scheduling, retries, or parallelism here. Those are
real future needs, but they extend this object rather than requiring one to
be invented later under pressure.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from agx_research.agents.base import ResearchFinding


class ResearchCycle(BaseModel):
    id: str
    version: int = 1
    run_date: date
    dataset_snapshot_id: str
    agent_versions: dict[str, str] = Field(default_factory=dict)
    findings: list[ResearchFinding] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None
