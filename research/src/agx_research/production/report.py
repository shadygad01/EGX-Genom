"""ExecutionReport: what `agx run` produces after every execution, and
`PipelineExecutionRepository`: the versioned history Mission Control reads
to answer "last successful pipeline" / "last failed pipeline" -- the exact
same append-only `Repository[T]` pattern every other store in this
codebase uses, not a bespoke log format.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.production.stages import StageName, StageResult, StageStatus
from agx_research.storage.repository import JsonFileRepository

PIPELINE_VERSION = "1.0.0"


class ExecutionReport(BaseModel):
    id: str
    version: int = 1
    pipeline_version: str = PIPELINE_VERSION
    execution_mode: str
    run_dates: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    overall_status: StageStatus
    stages: list[StageResult] = Field(default_factory=list)
    artifacts_generated: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    skipped_stages: list[str] = Field(default_factory=list)
    knowledge_before: int = 0
    knowledge_after: int = 0
    genome_before: int = 0
    genome_after: int = 0
    events_before: int = 0
    events_after: int = 0

    @property
    def knowledge_delta(self) -> int:
        return self.knowledge_after - self.knowledge_before

    @property
    def genome_delta(self) -> int:
        return self.genome_after - self.genome_before

    @property
    def events_delta(self) -> int:
        return self.events_after - self.events_before

    def stage(self, name: StageName) -> StageResult | None:
        return next((s for s in self.stages if s.name == name), None)


def derive_overall_status(stages: list[StageResult]) -> StageStatus:
    """SUCCEEDED only if every stage succeeded; FAILED only if every stage
    that actually ran failed (nothing meaningful was produced); otherwise
    PARTIAL -- some stages degraded but the run still produced something,
    which is the honest middle state "one stage failing must not corrupt
    later stages" implies must exist.
    """
    statuses = [s.status for s in stages]
    if all(status == StageStatus.SUCCEEDED for status in statuses):
        return StageStatus.SUCCEEDED
    ran = [s for s in statuses if s != StageStatus.SKIPPED]
    if ran and all(status == StageStatus.FAILED for status in ran):
        return StageStatus.FAILED
    return StageStatus.PARTIAL


class PipelineExecutionRepository(JsonFileRepository[ExecutionReport]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(ExecutionReport, persist_path)

    def last_successful(self) -> ExecutionReport | None:
        successes = [
            r for r in self.all_latest() if r.overall_status == StageStatus.SUCCEEDED
        ]
        return max(successes, key=lambda r: r.completed_at, default=None)

    def last_failed(self) -> ExecutionReport | None:
        failures = [r for r in self.all_latest() if r.overall_status == StageStatus.FAILED]
        return max(failures, key=lambda r: r.completed_at, default=None)
