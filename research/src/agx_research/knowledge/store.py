"""The knowledge store: the only path by which a hypothesis becomes knowledge.

`promote()` is the sole entry point for creating a `KnowledgeObject`, and it
refuses to do so unless the given evidence has actually passed its
pipeline's final gate (`is_ready_for_promotion`). There is deliberately no
API for an agent to write a `KnowledgeObject` directly — see Principle 6
("AI proposes. Evidence approves.") and `agents/base.py`.

`promote()` depends on `PromotableEvidence`, a structural `Protocol`, rather
than importing the concrete `Hypothesis` class. `Hypothesis` satisfies it
today, but so could any future evidence source (e.g. a hypothesis
synthesized from several prior ones) without this module needing to change
or even import `agx_research.hypotheses`.

Storage mechanics (versioned, append-only persistence) are delegated to
`agx_research.storage.JsonFileRepository` rather than hand-rolled here, so
every store in the system persists knowledge, hypotheses, and future
entities the same way.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.knowledge.lifecycle import KnowledgeStatus, can_transition
from agx_research.knowledge.schema import KnowledgeObject, PerformanceRecord
from agx_research.storage.repository import JsonFileRepository, Repository
from agx_research.validation.statistical import StatisticalEvidence


@runtime_checkable
class PromotableEvidence(Protocol):
    """Whatever `promote()` needs from a piece of evidence, structurally.

    `Hypothesis` satisfies this today; nothing here depends on it by name.
    """

    id: str
    version: int
    created_by: str
    created_at: date
    horizon: Horizon
    affected_assets: list[str]
    is_ready_for_promotion: bool
    current_stage_name: str


class KnowledgeStore:
    def __init__(self, persist_path: Path | str | None = None):
        self._repo: Repository[KnowledgeObject] = JsonFileRepository(
            KnowledgeObject, persist_path
        )

    def promote(
        self,
        evidence: PromotableEvidence,
        *,
        confidence: float,
        statistical_evidence: StatisticalEvidence,
        economic_explanation: str,
        expected_return: float,
        expected_risk: float,
        supporting_evidence: list[str] | None = None,
    ) -> KnowledgeObject:
        """Promote evidence that has passed its pipeline's final gate into knowledge."""
        if not evidence.is_ready_for_promotion:
            raise ValueError(
                f"{evidence.id} is not ready for promotion "
                f"(currently at gate '{evidence.current_stage_name}'); "
                f"it must pass the pipeline's final gate first."
            )
        knowledge = KnowledgeObject(
            id=evidence.id,
            version=1,
            discovery_date=evidence.created_at,
            creator_agent=evidence.created_by,
            supporting_evidence=supporting_evidence or [],
            confidence=confidence,
            statistical_evidence=statistical_evidence,
            economic_explanation=economic_explanation,
            affected_assets=evidence.affected_assets,
            horizon=evidence.horizon,
            expected_return=expected_return,
            expected_risk=expected_risk,
            status=KnowledgeStatus.PROMOTED,
            provenance=Provenance(
                produced_by="hypothesis_promotion_pipeline",
                produced_at=datetime.now(),
                inputs=[
                    ProvenanceRef(kind="hypothesis", ref_id=evidence.id, ref_version=evidence.version)
                ],
            ),
        )
        return self._repo.add(knowledge)

    def latest(self, knowledge_id: str) -> KnowledgeObject | None:
        return self._repo.latest(knowledge_id)

    def revisions_for(self, knowledge_id: str) -> list[KnowledgeObject]:
        return self._repo.history(knowledge_id)

    def all_latest(self) -> list[KnowledgeObject]:
        return self._repo.all_latest()

    def transition_status(
        self, knowledge_id: str, target: KnowledgeStatus, *, reason: str | None = None
    ) -> KnowledgeObject:
        current = self._repo.latest(knowledge_id)
        if current is None:
            raise KeyError(f"No knowledge object with id {knowledge_id}")
        if not can_transition(current.status, target):
            raise ValueError(f"Cannot transition {current.status} -> {target}")
        next_revision = current.model_copy(
            update={
                "version": current.version + 1,
                "status": target,
                "retired_at": date.today() if target == KnowledgeStatus.RETIRED else current.retired_at,
                "retirement_reason": reason if target == KnowledgeStatus.RETIRED else current.retirement_reason,
            }
        )
        return self._repo.add(next_revision)

    def record_performance(self, knowledge_id: str, record: PerformanceRecord) -> KnowledgeObject:
        current = self._repo.latest(knowledge_id)
        if current is None:
            raise KeyError(f"No knowledge object with id {knowledge_id}")
        next_revision = current.model_copy(
            update={
                "version": current.version + 1,
                "performance_history": [*current.performance_history, record],
            }
        )
        return self._repo.add(next_revision)
