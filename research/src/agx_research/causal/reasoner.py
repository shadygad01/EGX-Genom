"""CausalReasoner: the architecture for causal reasoning over a hypothesis.

`EconomicRationaleGate` is deliberately not causal inference — it's a real,
enforceable check operationalizing "correlation alone must never be
enough": it refuses to grant meaningful confidence to any hypothesis that
doesn't at least state a candidate cause and an economic rationale. Full
causal inference (structural models, instrumental variables, do-calculus)
is future work; building a fake version of it would be worse than this
honest, narrower gate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from agx_research.causal.assessment import CandidateCause, CausalAssessment
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.hypotheses.hypothesis import Hypothesis


class CausalReasoner(ABC):
    @abstractmethod
    def assess(
        self,
        hypothesis: Hypothesis,
        *,
        candidate_causes: list[CandidateCause] | None = None,
        economic_rationale: str | None = None,
    ) -> CausalAssessment:
        """Produce a CausalAssessment for `hypothesis`."""


class EconomicRationaleGate(CausalReasoner):
    """Rejects any hypothesis relying on correlation alone.

    Passing this gate is necessary, not sufficient — it caps confidence at
    0.5 even when it passes, since it verifies that a rationale was
    *stated*, not that it's correct. That judgment is what
    `review.reviewers.EconomistReviewer` (Phase 10) is for.
    """

    def assess(
        self,
        hypothesis: Hypothesis,
        *,
        candidate_causes: list[CandidateCause] | None = None,
        economic_rationale: str | None = None,
    ) -> CausalAssessment:
        candidate_causes = candidate_causes or []
        has_rationale = bool(economic_rationale and economic_rationale.strip())
        has_candidate_cause = len(candidate_causes) > 0
        passes = has_rationale and has_candidate_cause

        return CausalAssessment(
            hypothesis_id=hypothesis.id,
            candidate_causes=candidate_causes,
            confounders=[],
            alternative_explanations=[],
            confidence=0.5 if passes else 0.0,
            economic_rationale=economic_rationale or "",
            notes=(
                "Has a stated candidate cause and economic rationale; full causal "
                "inference is not yet implemented."
                if passes
                else "Correlation alone is not enough: at least one candidate cause and "
                "a stated economic rationale are required."
            ),
            provenance=Provenance(
                produced_by="EconomicRationaleGate",
                produced_at=datetime.now(),
                inputs=[
                    ProvenanceRef(kind="hypothesis", ref_id=hypothesis.id, ref_version=hypothesis.version)
                ],
            ),
        )
