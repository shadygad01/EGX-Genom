"""The Claim Registry extends the hypothesis methodology pipeline.

It deliberately uses the existing ``GateSpec`` methodology definition and
the shared versioned repository.  There is no second workflow engine.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from agx_research.claims.claim import (
    CLAIM_LIFECYCLE,
    TERMINAL_STAGES,
    Claim,
    ClaimEvidence,
    ClaimStage,
)
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.storage.repository import JsonFileRepository


class ClaimRegistry(JsonFileRepository[Claim]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(Claim, persist_path)

    def register_hypothesis(self, hypothesis: Hypothesis) -> Claim:
        existing = self.latest(hypothesis.id)
        if existing is not None:
            return existing
        claim = Claim(
            id=hypothesis.id,
            statement=hypothesis.statement,
            created_by=hypothesis.created_by,
            created_at=hypothesis.created_at,
            horizon=hypothesis.horizon,
            affected_assets=hypothesis.affected_assets,
            provenance=Provenance(
                produced_by="claims.registry.register_hypothesis",
                produced_at=datetime.now(),
                inputs=[
                    ProvenanceRef(
                        kind="hypothesis",
                        ref_id=hypothesis.id,
                        ref_version=hypothesis.version,
                    )
                ],
            ),
            methodology_id="hypothesis_pipeline_v1",
            methodology=hypothesis.pipeline,
            hypothesis_id=hypothesis.id,
        )
        return self.add(claim)

    def decompose_paper(self, paper_id: str, hypotheses: list[Hypothesis]) -> list[Claim]:
        """Register every explicit claim extracted from one paper.

        Empty papers are rejected: storing a paper without testable claims
        would recreate the paper-centred dead end this registry removes.
        """
        if not hypotheses:
            raise ValueError("A paper must be decomposed into at least one testable claim")
        claims: list[Claim] = []
        for hypothesis in hypotheses:
            claim = self.register_hypothesis(hypothesis)
            claims.append(self.attach_paper(claim.id, paper_id))
        return claims

    def record(
        self,
        claim_id: str,
        *,
        stage: ClaimStage,
        evidence_type: str,
        ref_id: str,
        passed: bool,
        notes: str = "",
        metrics: dict[str, float] | None = None,
    ) -> Claim:
        current = self.latest(claim_id)
        if current is None:
            raise KeyError(f"Unknown claim {claim_id}")
        if current.stage in TERMINAL_STAGES:
            raise ValueError(f"Claim {claim_id} is terminal at {current.stage.value}")
        if evidence_type == "paper":
            raise ValueError("Papers are evidence containers and cannot validate a claim")
        current_index = CLAIM_LIFECYCLE.index(current.stage)
        requested_index = CLAIM_LIFECYCLE.index(stage)
        if requested_index not in {current_index, current_index + 1}:
            raise ValueError(
                f"Cannot skip claim lifecycle stage {current.stage.value} -> {stage.value}"
            )
        evidence = ClaimEvidence(
            stage=stage,
            evidence_type=evidence_type,
            ref_id=ref_id,
            recorded_at=datetime.now(),
            passed=passed,
            notes=notes,
            metrics=metrics or {},
        )
        next_stage = stage if passed else ClaimStage.REJECTED
        revision = current.model_copy(
            update={
                "version": current.version + 1,
                "stage": next_stage,
                "evidence_history": [*current.evidence_history, evidence],
                "rejection_reason": None if passed else (notes or f"Failed {stage.value}"),
            }
        )
        return self.add(revision)

    def attach_paper(self, claim_id: str, paper_id: str) -> Claim:
        current = self.latest(claim_id)
        if current is None:
            raise KeyError(f"Unknown claim {claim_id}")
        if paper_id in current.source_paper_ids:
            return current
        return self.add(current.model_copy(update={
            "version": current.version + 1,
            "source_paper_ids": [*current.source_paper_ids, paper_id],
        }))

    def attach_knowledge(self, claim_id: str, knowledge_id: str) -> Claim:
        current = self.latest(claim_id)
        if current is None or not current.is_experimentally_validated:
            raise ValueError("Only experimentally validated claims may link production knowledge")
        return self.add(current.model_copy(update={
            "version": current.version + 1,
            "knowledge_id": knowledge_id,
        }))

    def production_eligible(self) -> list[Claim]:
        return [claim for claim in self.all_latest() if claim.is_experimentally_validated]
