from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.review.board import ScientificReviewBoard
from agx_research.review.candidate import PromotionCandidate
from agx_research.review.reviewers import (
    HistoricalReviewer,
    RiskReviewer,
    StatisticianReviewer,
)
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.validation.statistical import StatisticalEvidence


def hypothesis() -> Hypothesis:
    return Hypothesis(
        id="hyp-review",
        statement="test",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.SWING,
        affected_assets=["COMI"],
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )


def good_candidate() -> PromotionCandidate:
    return PromotionCandidate(
        confidence=0.7,
        statistical_evidence=StatisticalEvidence(
            method="SignificanceThresholdValidator", statistic=2.5, p_value=0.01, sample_size=42
        ),
        economic_explanation="test",
        expected_return=0.03,
        expected_risk=0.02,
    )


def weak_candidate() -> PromotionCandidate:
    return PromotionCandidate(
        confidence=0.4,
        statistical_evidence=StatisticalEvidence(
            method="SignificanceThresholdValidator", statistic=0.3, p_value=0.4, sample_size=8
        ),
        economic_explanation="test",
        expected_return=0.03,
        expected_risk=0.25,
    )


def test_statistician_reviewer_passes_strong_evidence():
    report = StatisticianReviewer().review(
        hypothesis=hypothesis(), candidate=good_candidate(), experiment_results={}
    )
    assert report.passed


def test_statistician_reviewer_rejects_weak_evidence():
    report = StatisticianReviewer().review(
        hypothesis=hypothesis(), candidate=weak_candidate(), experiment_results={}
    )
    assert not report.passed
    assert any(not f.passed for f in report.findings)


def test_risk_reviewer_rejects_excessive_risk():
    report = RiskReviewer(max_expected_risk=0.10).review(
        hypothesis=hypothesis(), candidate=weak_candidate(), experiment_results={}
    )
    assert not report.passed


def test_board_approves_only_when_every_reviewer_passes():
    board = ScientificReviewBoard([StatisticianReviewer(), RiskReviewer()])
    decision = board.review(hypothesis=hypothesis(), candidate=good_candidate(), experiment_results={})
    assert decision.approved
    assert len(decision.reports) == 2


def test_board_rejects_if_any_reviewer_fails():
    board = ScientificReviewBoard([StatisticianReviewer(), RiskReviewer()])
    decision = board.review(hypothesis=hypothesis(), candidate=weak_candidate(), experiment_results={})
    assert not decision.approved


def test_board_skips_unimplemented_reviewers_rather_than_failing():
    board = ScientificReviewBoard([StatisticianReviewer(), HistoricalReviewer()])
    decision = board.review(hypothesis=hypothesis(), candidate=good_candidate(), experiment_results={})
    assert decision.approved
    assert len(decision.reports) == 1  # HistoricalReviewer skipped, not counted as pass or fail


def test_board_with_no_working_reviewers_never_approves():
    board = ScientificReviewBoard([HistoricalReviewer()])
    decision = board.review(hypothesis=hypothesis(), candidate=good_candidate(), experiment_results={})
    assert not decision.approved
    assert decision.reports == []
