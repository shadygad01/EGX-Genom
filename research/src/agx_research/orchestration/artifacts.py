"""Artifacts: first-class, versioned wrappers around anything a task produces.

`ArtifactKind` names the concrete shapes this system produces today
(`DatasetSnapshot`, correlation matrices from feature discovery, experiment
results, validation reports, promoted-knowledge publications, recommendation
reports). An `Artifact` stores the producing entity's payload as a plain
JSON-compatible dict (via pydantic's `model_dump(mode="json")`) rather than
a typed union — new artifact-producing objects don't require a schema
change here, only a new `ArtifactKind` member.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance
from agx_research.storage.repository import JsonFileRepository


class ArtifactKind(str, Enum):
    DATASET_SNAPSHOT = "dataset_snapshot"
    FEATURE_MATRIX = "feature_matrix"
    CORRELATION_MATRIX = "correlation_matrix"
    EXPERIMENT_RESULT = "experiment_result"
    VALIDATION_REPORT = "validation_report"
    KNOWLEDGE_PUBLICATION = "knowledge_publication"
    RECOMMENDATION_REPORT = "recommendation_report"


class Artifact(BaseModel):
    id: str
    version: int = 1
    kind: ArtifactKind
    produced_by_task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance


class ArtifactRepository(JsonFileRepository[Artifact]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(Artifact, persist_path)

    def store(
        self,
        *,
        kind: ArtifactKind,
        payload: BaseModel | dict[str, Any],
        provenance: Provenance,
        artifact_id: str | None = None,
        produced_by_task_id: str | None = None,
    ) -> Artifact:
        """Wrap `payload` as a new artifact revision and persist it.

        Pass the same `artifact_id` across calls to version the *same*
        logical artifact (e.g. "today's correlation matrix" re-produced
        tomorrow); omit it to mint a fresh id for a one-off artifact.
        """
        resolved_id = artifact_id or new_id("artifact")
        previous = self.latest(resolved_id)
        payload_dict = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        artifact = Artifact(
            id=resolved_id,
            version=(previous.version + 1) if previous else 1,
            kind=kind,
            produced_by_task_id=produced_by_task_id,
            payload=payload_dict,
            provenance=provenance,
        )
        return self.add(artifact)
