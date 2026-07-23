"""The production pipeline's stage vocabulary: one name per link in the
chain the mission specifies, in the order it specifies them. Nothing here
does any work -- `pipeline.py` does the wiring; this module just gives
every stage a stable name and a uniform result shape so the execution
report can describe exactly what happened, stage by stage.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class StageName(str, Enum):
    ENTRYPOINT = "entrypoint"
    SOURCE_REGISTRY = "source_registry"
    DISCOVERY_ENGINE = "discovery_engine"
    COLLECTOR_SELECTION = "collector_selection"
    COLLECTOR_EXECUTION = "collector_execution"
    RAW_ARCHIVE = "raw_archive"
    CANONICAL_TRANSFORMATION = "canonical_transformation"
    VALIDATION = "validation"
    EVENT_PLATFORM = "event_platform"
    MARKET_MEMORY = "market_memory"
    KNOWLEDGE_BASE = "knowledge_base"
    RESEARCH_PIPELINE = "research_pipeline"
    GENOME = "genome"
    INVESTMENT_CASE_GENERATOR = "investment_case_generator"
    DASHBOARD_ARTIFACT_GENERATOR = "dashboard_artifact_generator"
    MISSION_CONTROL_UPDATE = "mission_control_update"
    EXECUTION_REPORT = "execution_report"


class StageStatus(str, Enum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"  # ran, but part of its work failed (e.g. one of several collectors)
    FAILED = "failed"
    SKIPPED = "skipped"


class StageResult(BaseModel):
    name: StageName
    status: StageStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    detail: str = ""
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
