"""The knowledge store: the only path by which a hypothesis becomes knowledge.

`promote()` is the sole entry point for creating a `KnowledgeObject`, and it
refuses to do so unless the given `Hypothesis` has actually passed Peer
Validation (`Hypothesis.is_ready_for_promotion`). There is deliberately no
API for an agent to write a `KnowledgeObject` directly — see Principle 6
("AI proposes. Evidence approves.") and `agents/base.py`.

Every write appends a new versioned revision rather than overwriting the
previous one, so the full history of a knowledge object is reconstructable
from `revisions_for(id)`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.knowledge.lifecycle import KnowledgeStatus, can_transition
from agx_research.knowledge.schema import KnowledgeObject, PerformanceRecord


class KnowledgeStore:
    """In-memory knowledge store with optional JSON-file persistence.

    This is a foundation-scaffold implementation — swap for a real database
    once the knowledge base needs concurrent writers or query performance
    beyond what fits in memory.
    """

    def __init__(self, persist_path: Path | str | None = None):
        self._revisions: dict[str, list[KnowledgeObject]] = {}
        self.persist_path = Path(persist_path) if persist_path else None
        if self.persist_path and self.persist_path.exists():
            self._load()

    def promote(
        self,
        hypothesis: Hypothesis,
        *,
        confidence: float,
        statistical_strength: float,
        economic_explanation: str,
        expected_return: float,
        expected_risk: float,
        supporting_evidence: list[str] | None = None,
    ) -> KnowledgeObject:
        """Promote a hypothesis that has passed Peer Validation into knowledge."""
        if not hypothesis.is_ready_for_promotion:
            raise ValueError(
                f"Hypothesis {hypothesis.id} is not ready for promotion "
                f"(stage={hypothesis.stage.name}); it must pass PEER_VALIDATION first."
            )
        knowledge = KnowledgeObject(
            id=hypothesis.id,
            version=1,
            discovery_date=hypothesis.created_at,
            creator_agent=hypothesis.created_by,
            supporting_evidence=supporting_evidence or [],
            confidence=confidence,
            statistical_strength=statistical_strength,
            economic_explanation=economic_explanation,
            affected_assets=hypothesis.affected_assets,
            horizon=hypothesis.horizon,
            expected_return=expected_return,
            expected_risk=expected_risk,
            status=KnowledgeStatus.PROMOTED,
        )
        self._revisions.setdefault(knowledge.id, []).append(knowledge)
        self._save()
        return knowledge

    def latest(self, knowledge_id: str) -> KnowledgeObject | None:
        revisions = self._revisions.get(knowledge_id)
        return revisions[-1] if revisions else None

    def revisions_for(self, knowledge_id: str) -> list[KnowledgeObject]:
        return list(self._revisions.get(knowledge_id, []))

    def all_latest(self) -> list[KnowledgeObject]:
        return [revisions[-1] for revisions in self._revisions.values()]

    def transition_status(
        self, knowledge_id: str, target: KnowledgeStatus, *, reason: str | None = None
    ) -> KnowledgeObject:
        current = self.latest(knowledge_id)
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
        self._revisions[knowledge_id].append(next_revision)
        self._save()
        return next_revision

    def record_performance(self, knowledge_id: str, record: PerformanceRecord) -> KnowledgeObject:
        current = self.latest(knowledge_id)
        if current is None:
            raise KeyError(f"No knowledge object with id {knowledge_id}")
        next_revision = current.model_copy(
            update={
                "version": current.version + 1,
                "performance_history": [*current.performance_history, record],
            }
        )
        self._revisions[knowledge_id].append(next_revision)
        self._save()
        return next_revision

    def _save(self) -> None:
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            knowledge_id: [json.loads(rev.model_dump_json()) for rev in revisions]
            for knowledge_id, revisions in self._revisions.items()
        }
        self.persist_path.write_text(json.dumps(payload, indent=2))

    def _load(self) -> None:
        payload = json.loads(self.persist_path.read_text())
        self._revisions = {
            knowledge_id: [KnowledgeObject.model_validate(rev) for rev in revisions]
            for knowledge_id, revisions in payload.items()
        }
