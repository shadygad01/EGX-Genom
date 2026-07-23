"""Mission Control's machine-readable pipeline status: `mission_status.json`.

Derived entirely from `ExecutionReport`s already produced by a run --
Mission Control doesn't compute anything new, it just answers the specific
questions the charter's Mission Control system is required to track:
Pipeline Status, Pipeline Version, Last Successful Pipeline, Last Failed
Pipeline, Current Execution Mode, Execution Duration, Artifacts Produced,
Knowledge Updated, Genome Updated.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from agx_research.production.report import ExecutionReport, PipelineExecutionRepository
from agx_research.production.stages import StageStatus


class MissionControlStatus(BaseModel):
    generated_at: datetime
    pipeline_status: StageStatus
    pipeline_version: str
    last_successful_pipeline_id: str | None
    last_successful_pipeline_at: datetime | None
    last_failed_pipeline_id: str | None
    last_failed_pipeline_at: datetime | None
    current_execution_mode: str
    execution_duration_seconds: float
    artifacts_produced: dict[str, int]
    knowledge_updated: int
    genome_updated: int
    total_executions: int


def build_mission_control_status(
    latest: ExecutionReport, history: PipelineExecutionRepository
) -> MissionControlStatus:
    last_success = history.last_successful()
    last_failure = history.last_failed()
    return MissionControlStatus(
        generated_at=datetime.now(),
        pipeline_status=latest.overall_status,
        pipeline_version=latest.pipeline_version,
        last_successful_pipeline_id=last_success.id if last_success else None,
        last_successful_pipeline_at=last_success.completed_at if last_success else None,
        last_failed_pipeline_id=last_failure.id if last_failure else None,
        last_failed_pipeline_at=last_failure.completed_at if last_failure else None,
        current_execution_mode=latest.execution_mode,
        execution_duration_seconds=latest.duration_seconds,
        artifacts_produced=latest.artifacts_generated,
        knowledge_updated=latest.knowledge_delta,
        genome_updated=latest.genome_delta,
        total_executions=len(history.all_latest()),
    )
