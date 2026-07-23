from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.hypotheses.hypothesis import Hypothesis, HypothesisStage, StageResult


def make_hypothesis() -> Hypothesis:
    return Hypothesis(
        id="hyp-001",
        statement="EGX70 leads EGX30 by one trading day",
        created_by="market_structure_agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=["COMI", "MFPC"],
    )


def test_starts_at_observation():
    hypothesis = make_hypothesis()
    assert hypothesis.stage == HypothesisStage.OBSERVATION


def test_passing_result_advances_one_stage():
    hypothesis = make_hypothesis()
    hypothesis.advance(
        StageResult(stage=HypothesisStage.OBSERVATION, passed=True, evaluated_at=datetime.now())
    )
    assert hypothesis.stage == HypothesisStage.HYPOTHESIS


def test_failing_result_does_not_advance():
    hypothesis = make_hypothesis()
    hypothesis.advance(
        StageResult(stage=HypothesisStage.OBSERVATION, passed=False, evaluated_at=datetime.now())
    )
    assert hypothesis.stage == HypothesisStage.OBSERVATION


def test_cannot_record_result_for_wrong_stage():
    hypothesis = make_hypothesis()
    with pytest.raises(ValueError):
        hypothesis.advance(
            StageResult(stage=HypothesisStage.EXPERIMENT, passed=True, evaluated_at=datetime.now())
        )


def test_full_progression_to_peer_validation_marks_ready_for_promotion():
    hypothesis = make_hypothesis()
    for stage in HypothesisStage:
        hypothesis.advance(StageResult(stage=stage, passed=True, evaluated_at=datetime.now()))

    assert hypothesis.stage == HypothesisStage.PEER_VALIDATION
    assert hypothesis.is_ready_for_promotion


def test_not_ready_for_promotion_before_peer_validation():
    hypothesis = make_hypothesis()
    hypothesis.advance(
        StageResult(stage=HypothesisStage.OBSERVATION, passed=True, evaluated_at=datetime.now())
    )
    assert not hypothesis.is_ready_for_promotion
