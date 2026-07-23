"""The Scientific Review Board's Reviewer contract.

Every reviewer produces a structured `ReviewReport` — findings with actual
metrics and thresholds, not a bare pass/fail — so a rejection is auditable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.causal.assessment import CausalAssessment
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.experiment import ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.review.candidate import PromotionCandidate


class ReviewerRole(str, Enum):
    STATISTICIAN = "statistician"
    ECONOMIST = "economist"
    RISK_REVIEWER = "risk_reviewer"
    HISTORICAL_REVIEWER = "historical_reviewer"
    PEER_VALIDATOR = "peer_validator"


class ReviewFinding(BaseModel):
    description: str
    passed: bool
    metric: str | None = None
    value: float | None = None
    threshold: float | None = None


class ReviewReport(BaseModel):
    reviewer_role: ReviewerRole
    passed: bool
    findings: list[ReviewFinding] = Field(default_factory=list)
    notes: str = ""
    provenance: Provenance


class Reviewer(ABC):
    role: ReviewerRole

    @abstractmethod
    def review(
        self,
        *,
        hypothesis: Hypothesis,
        candidate: PromotionCandidate,
        experiment_results: dict[str, ExperimentResult],
        causal_assessment: CausalAssessment | None = None,
    ) -> ReviewReport:
        """Produce a structured judgment on whether `candidate` should be promoted."""
