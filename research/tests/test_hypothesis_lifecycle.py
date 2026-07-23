from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.hypothesis import Hypothesis, StageResult
from agx_research.hypotheses.pipeline import DEFAULT_PIPELINE, GateSpec, StageName


def make_hypothesis(pipeline: list[GateSpec] | None = None) -> Hypothesis:
    return Hypothesis(
        id="hyp-001",
        statement="EGX70 leads EGX30 by one trading day",
        created_by="market_structure_agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=["COMI", "MFPC"],
        provenance=Provenance(produced_by="market_structure_agent@0.1.0", produced_at=datetime.now()),
        pipeline=pipeline or list(DEFAULT_PIPELINE),
    )


def test_starts_at_first_gate():
    hypothesis = make_hypothesis()
    assert hypothesis.current_stage_name == StageName.OBSERVATION.value
    assert hypothesis.version == 1


def test_passing_result_advances_one_gate_and_bumps_version():
    hypothesis = make_hypothesis()
    advanced = hypothesis.advance(
        StageResult(stage_name=StageName.OBSERVATION.value, passed=True, evaluated_at=datetime.now())
    )
    assert advanced.current_stage_name == StageName.HYPOTHESIS.value
    assert advanced.version == 2
    # original is untouched -- advance() returns a new revision
    assert hypothesis.current_stage_name == StageName.OBSERVATION.value


def test_failing_result_does_not_advance():
    hypothesis = make_hypothesis()
    advanced = hypothesis.advance(
        StageResult(stage_name=StageName.OBSERVATION.value, passed=False, evaluated_at=datetime.now())
    )
    assert advanced.current_stage_name == StageName.OBSERVATION.value
    assert advanced.version == 2  # still a new revision, recording the failed attempt


def test_cannot_record_result_for_wrong_gate():
    hypothesis = make_hypothesis()
    with pytest.raises(ValueError):
        hypothesis.advance(
            StageResult(stage_name=StageName.EXPERIMENT.value, passed=True, evaluated_at=datetime.now())
        )


def test_full_progression_to_final_gate_marks_ready_for_promotion():
    hypothesis = make_hypothesis()
    for stage in StageName:
        hypothesis = hypothesis.advance(
            StageResult(stage_name=stage.value, passed=True, evaluated_at=datetime.now())
        )

    assert hypothesis.current_stage_name == StageName.PEER_VALIDATION.value
    assert hypothesis.is_ready_for_promotion
    assert hypothesis.version == 1 + len(StageName)


def test_not_ready_for_promotion_before_final_gate():
    hypothesis = make_hypothesis()
    hypothesis = hypothesis.advance(
        StageResult(stage_name=StageName.OBSERVATION.value, passed=True, evaluated_at=datetime.now())
    )
    assert not hypothesis.is_ready_for_promotion


def test_custom_pipeline_is_not_hardcoded():
    """A hypothesis track can use a completely different set of gates."""
    custom_pipeline = [
        GateSpec(name="QUICK_SCREEN", order=0),
        GateSpec(name="BACKTEST_ONLY", order=1),
    ]
    hypothesis = make_hypothesis(pipeline=custom_pipeline)

    assert hypothesis.current_stage_name == "QUICK_SCREEN"
    hypothesis = hypothesis.advance(
        StageResult(stage_name="QUICK_SCREEN", passed=True, evaluated_at=datetime.now())
    )
    assert hypothesis.current_stage_name == "BACKTEST_ONLY"
    assert not hypothesis.is_ready_for_promotion

    hypothesis = hypothesis.advance(
        StageResult(stage_name="BACKTEST_ONLY", passed=True, evaluated_at=datetime.now())
    )
    assert hypothesis.is_ready_for_promotion
