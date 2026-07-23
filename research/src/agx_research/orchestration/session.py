"""The Research Session: what one trading day's research run owns.

Supersedes `ResearchCycle` as the richer Epoch II record — a session owns
its immutable `DatasetSnapshot`, the `Task`s that ran (see `task_graph.py`),
every `Artifact` produced, the findings/hypotheses/knowledge/recommendations
that resulted, and exact timing. `ResearchCycle` is unchanged and still
usable directly for callers that only need agent findings; `ResearchSession`
is the superset for anything that needs the full, replayable record.

Sessions are replayable by construction: everything referenced by id here
(the snapshot, the artifacts) is itself immutable and versioned, so a
session can always be walked back to exactly what it saw and produced.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from agx_research.agents.base import ResearchFinding
from agx_research.orchestration.task_graph import Task


class ResearchSession(BaseModel):
    id: str
    version: int = 1
    run_date: date
    dataset_snapshot_id: str
    agent_versions: dict[str, str] = Field(default_factory=dict)
    tasks: list[Task] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    findings: list[ResearchFinding] = Field(default_factory=list)
    hypothesis_ids: list[str] = Field(default_factory=list)
    knowledge_ids: list[str] = Field(default_factory=list)
    recommendation_ids: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None
