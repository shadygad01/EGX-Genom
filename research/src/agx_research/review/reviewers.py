"""Concrete reviewers.

`StatisticianReviewer` and `RiskReviewer` are real, mechanical checks
against thresholds. `EconomistReviewer`, `HistoricalReviewer`, and
`PeerValidatorReviewer` are real interfaces raising `NotImplementedError`
— each needs a domain-specific rubric (macro/sector context for economic
plausibility, a historical-analog database, an actual second researcher's
judgment) that's a research decision, not scaffolding.
"""

from __future__ import annotations

from datetime import datetime

from agx_research.causal.assessment import CausalAssessment
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.hypotheses.experiment import ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.review.candidate import PromotionCandidate
from agx_research.review.reviewer import ReviewerRole, ReviewFinding, ReviewReport, Reviewer


def _provenance(reviewer_name: str, hypothesis: Hypothesis) -> Provenance:
    return Provenance(
        produced_by=reviewer_name,
        produced_at=datetime.now(),
        inputs=[ProvenanceRef(kind="hypothesis", ref_id=hypothesis.id, ref_version=hypothesis.version)],
    )


class StatisticianReviewer(Reviewer):
    role = ReviewerRole.STATISTICIAN

    def __init__(self, alpha: float = 0.05, min_sample_size: int = 30):
        self.alpha = alpha
        self.min_sample_size = min_sample_size

    def review(
        self,
        *,
        hypothesis: Hypothesis,
        candidate: PromotionCandidate,
        experiment_results: dict[str, ExperimentResult],
        causal_assessment: CausalAssessment | None = None,
    ) -> ReviewReport:
        evidence = candidate.statistical_evidence
        significant = evidence.p_value < self.alpha
        enough_samples = evidence.sample_size >= self.min_sample_size

        findings = [
            ReviewFinding(
                description="Statistically significant at alpha",
                passed=significant,
                metric="p_value",
                value=evidence.p_value,
                threshold=self.alpha,
            ),
            ReviewFinding(
                description="Sufficient sample size",
                passed=enough_samples,
                metric="sample_size",
                value=float(evidence.sample_size),
                threshold=float(self.min_sample_size),
            ),
        ]
        passed = significant and enough_samples
        return ReviewReport(
            reviewer_role=self.role,
            passed=passed,
            findings=findings,
            notes="" if passed else "Failed significance and/or sample-size threshold.",
            provenance=_provenance("StatisticianReviewer", hypothesis),
        )


class RiskReviewer(Reviewer):
    role = ReviewerRole.RISK_REVIEWER

    def __init__(self, max_expected_risk: float = 0.10):
        self.max_expected_risk = max_expected_risk

    def review(
        self,
        *,
        hypothesis: Hypothesis,
        candidate: PromotionCandidate,
        experiment_results: dict[str, ExperimentResult],
        causal_assessment: CausalAssessment | None = None,
    ) -> ReviewReport:
        passed = candidate.expected_risk <= self.max_expected_risk
        finding = ReviewFinding(
            description="Expected risk within ceiling",
            passed=passed,
            metric="expected_risk",
            value=candidate.expected_risk,
            threshold=self.max_expected_risk,
        )
        return ReviewReport(
            reviewer_role=self.role,
            passed=passed,
            findings=[finding],
            notes=(
                ""
                if passed
                else f"Expected risk {candidate.expected_risk} exceeds ceiling {self.max_expected_risk}."
            ),
            provenance=_provenance("RiskReviewer", hypothesis),
        )


class EconomistReviewer(Reviewer):
    """Needs macro/sector context to judge economic plausibility -- not yet implemented."""

    role = ReviewerRole.ECONOMIST

    def review(self, **kwargs) -> ReviewReport:
        raise NotImplementedError("EconomistReviewer is not yet implemented")


class HistoricalReviewer(Reviewer):
    """Needs a historical-analog database to compare against -- not yet implemented."""

    role = ReviewerRole.HISTORICAL_REVIEWER

    def review(self, **kwargs) -> ReviewReport:
        raise NotImplementedError("HistoricalReviewer is not yet implemented")


class PeerValidatorReviewer(Reviewer):
    """Needs an actual second researcher/agent's independent judgment -- not yet implemented."""

    role = ReviewerRole.PEER_VALIDATOR

    def review(self, **kwargs) -> ReviewReport:
        raise NotImplementedError("PeerValidatorReviewer is not yet implemented")
