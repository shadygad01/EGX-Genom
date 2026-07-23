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
    """Structural review of the economic rationale.

    Checks, mechanically and honestly: the rationale exists with real
    substance (minimum length), it engages with the specific hypothesis
    (mentions at least one affected asset, its sector, or a recognized
    economic-mechanism term), and a causal assessment passed the
    correlation-alone gate. This verifies the rationale's *coherence with
    the claim*, not its economic truth — judging truth needs either a
    human economist or a far richer macro model, and pretending otherwise
    would fabricate confidence.
    """

    role = ReviewerRole.ECONOMIST

    _MECHANISM_TERMS = (
        "flow", "margin", "rate", "demand", "supply", "cost", "currency",
        "liquidity", "earnings", "dividend", "index", "sector", "export",
        "import", "inflation", "capital",
    )

    def __init__(self, min_rationale_length: int = 40):
        self.min_rationale_length = min_rationale_length

    def review(
        self,
        *,
        hypothesis: Hypothesis,
        candidate: PromotionCandidate,
        experiment_results: dict[str, ExperimentResult],
        causal_assessment: CausalAssessment | None = None,
    ) -> ReviewReport:
        rationale = (candidate.economic_explanation or "").strip()
        has_substance = len(rationale) >= self.min_rationale_length
        lowered = rationale.lower()
        engages_claim = any(asset.lower() in lowered for asset in hypothesis.affected_assets) or any(
            term in lowered for term in self._MECHANISM_TERMS
        )
        causal_gate_passed = causal_assessment is not None and causal_assessment.confidence > 0.0

        findings = [
            ReviewFinding(
                description="Rationale has real substance (not a placeholder sentence)",
                passed=has_substance,
                metric="rationale_length",
                value=float(len(rationale)),
                threshold=float(self.min_rationale_length),
            ),
            ReviewFinding(
                description="Rationale engages the specific claim (assets or a mechanism)",
                passed=engages_claim,
            ),
            ReviewFinding(
                description="Causal gate passed (a candidate cause was stated)",
                passed=causal_gate_passed,
            ),
        ]
        passed = all(f.passed for f in findings)
        return ReviewReport(
            reviewer_role=self.role,
            passed=passed,
            findings=findings,
            notes=(
                "Structural coherence verified; economic truth is NOT judged here."
                if passed
                else "Rationale lacks substance, doesn't engage the claim, or no causal "
                "assessment passed the correlation-alone gate."
            ),
            provenance=_provenance("EconomistReviewer", hypothesis),
        )


class HistoricalReviewer(Reviewer):
    """Needs a historical-analog database (years of labeled market episodes)
    to compare against -- data-blocked, not yet implemented."""

    role = ReviewerRole.HISTORICAL_REVIEWER

    def review(self, **kwargs) -> ReviewReport:
        raise NotImplementedError("HistoricalReviewer needs a historical-analog database")


class PeerValidatorReviewer(Reviewer):
    """Independent replication as peer validation.

    Re-derives the statistical evidence with a perturbed methodology
    (different fold count, different bootstrap seed) against the same
    snapshot, and passes only if the replication agrees with the reported
    evidence in sign and significance. This is a real, mechanical form of
    peer review — "can an independent run reproduce your result" — not a
    simulated human judgment.
    """

    role = ReviewerRole.PEER_VALIDATOR

    def __init__(self, *, snapshot=None, alpha: float = 0.05):
        # The snapshot to replicate against is injected per-review-cycle by
        # the promotion pipeline; a reviewer constructed without one cannot
        # run (and the board will skip it rather than fake a pass).
        self.snapshot = snapshot
        self.alpha = alpha

    def review(
        self,
        *,
        hypothesis: Hypothesis,
        candidate: PromotionCandidate,
        experiment_results: dict[str, ExperimentResult],
        causal_assessment: CausalAssessment | None = None,
    ) -> ReviewReport:
        if self.snapshot is None:
            raise NotImplementedError(
                "PeerValidatorReviewer requires the review cycle's DatasetSnapshot"
            )
        # Imported here to avoid a package cycle (hypotheses imports validation).
        from agx_research.hypotheses.experiment_factory import (
            BootstrapExperiment,
            CrossValidationExperiment,
        )

        replication_cv = CrossValidationExperiment(folds=2).run(hypothesis, self.snapshot)
        replication_boot = BootstrapExperiment(iterations=300, seed=1337).run(
            hypothesis, self.snapshot
        )

        reported = candidate.statistical_evidence
        sign_agrees = (replication_boot.statistic <= 0) == (reported.statistic <= 0)
        replication_significant = replication_boot.p_value < self.alpha

        findings = [
            ReviewFinding(
                description="Replicated statistic agrees in sign with reported evidence",
                passed=sign_agrees,
                metric="replication_statistic",
                value=replication_boot.statistic,
            ),
            ReviewFinding(
                description="Replication is itself significant",
                passed=replication_significant,
                metric="replication_p_value",
                value=replication_boot.p_value,
                threshold=self.alpha,
            ),
            ReviewFinding(
                description="2-fold cross-validation replication produced a result",
                passed=True,
                metric="replication_cv_p_value",
                value=replication_cv.p_value,
            ),
        ]
        passed = sign_agrees and replication_significant
        return ReviewReport(
            reviewer_role=self.role,
            passed=passed,
            findings=findings,
            notes=(
                "Independent replication (perturbed folds/seed) reproduced the result."
                if passed
                else "Independent replication failed to reproduce the reported evidence."
            ),
            provenance=_provenance("PeerValidatorReviewer", hypothesis),
        )
