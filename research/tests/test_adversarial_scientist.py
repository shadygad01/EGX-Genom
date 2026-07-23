from datetime import date, datetime
from pathlib import Path

from agx_research.adversarial.attacks import AttackType
from agx_research.adversarial.scientist import AdversarialScientist, apply_adversarial_review
from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.experiment import ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def hypothesis(created_at=date(2026, 6, 1)) -> Hypothesis:
    return Hypothesis(
        id="hyp-adversarial",
        statement="test",
        created_by="agent",
        created_at=created_at,
        horizon=Horizon.MICRO,
        affected_assets=["COMI", "MFPC"],
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )


def snapshot():
    provider = MockDataProvider(MOCK_ROOT)
    return build_snapshot(
        provider, tickers=["COMI", "MFPC"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )


def test_reports_all_nine_attack_types():
    results = AdversarialScientist().attack(hypothesis(), {}, snapshot())
    assert {r.attack_type for r in results} == set(AttackType)


def test_unimplemented_attacks_are_marked_not_attempted():
    results = AdversarialScientist().attack(hypothesis(), {}, snapshot())
    unimplemented = {
        AttackType.RANDOM_COINCIDENCE,
        AttackType.OVERFITTING,
        AttackType.PARAMETER_INSTABILITY,
        AttackType.REGIME_DEPENDENCY,
        AttackType.OUT_OF_SAMPLE_DEGRADATION,
    }
    for result in results:
        if result.attack_type in unimplemented:
            assert result.attempted is False
            assert result.confidence_delta == 0.0
        else:
            assert result.attempted is True


def test_small_sample_bias_succeeds_below_threshold():
    scientist = AdversarialScientist(min_sample_size=100)
    results = scientist.attack(
        hypothesis(),
        {"exp": ExperimentResult(statistic=1.0, p_value=0.01, sample_size=9)},
        snapshot(),
    )
    attack = next(r for r in results if r.attack_type == AttackType.SMALL_SAMPLE_BIAS)
    assert attack.succeeded is True
    assert attack.confidence_delta < 0


def test_small_sample_bias_fails_above_threshold():
    scientist = AdversarialScientist(min_sample_size=5)
    results = scientist.attack(
        hypothesis(),
        {"exp": ExperimentResult(statistic=1.0, p_value=0.01, sample_size=9)},
        snapshot(),
    )
    attack = next(r for r in results if r.attack_type == AttackType.SMALL_SAMPLE_BIAS)
    assert attack.succeeded is False
    assert attack.confidence_delta > 0


def test_time_leakage_detected_when_hypothesis_postdates_snapshot():
    results = AdversarialScientist().attack(hypothesis(created_at=date(2026, 7, 1)), {}, snapshot())
    attack = next(r for r in results if r.attack_type == AttackType.TIME_LEAKAGE)
    assert attack.succeeded is True
    assert attack.confidence_delta < 0


def test_time_leakage_not_detected_when_hypothesis_predates_snapshot():
    results = AdversarialScientist().attack(hypothesis(created_at=date(2026, 6, 1)), {}, snapshot())
    attack = next(r for r in results if r.attack_type == AttackType.TIME_LEAKAGE)
    assert attack.succeeded is False


def test_weak_economic_rationale_flagged_when_missing():
    results = AdversarialScientist().attack(hypothesis(), {}, snapshot())
    attack = next(r for r in results if r.attack_type == AttackType.WEAK_ECONOMIC_RATIONALE)
    assert attack.succeeded is True


def test_weak_economic_rationale_not_flagged_when_substantive():
    results = AdversarialScientist().attack(
        hypothesis(),
        {},
        snapshot(),
        economic_rationale="Both are large-cap EGX30 names subject to similar market-wide capital flows.",
    )
    attack = next(r for r in results if r.attack_type == AttackType.WEAK_ECONOMIC_RATIONALE)
    assert attack.succeeded is False


def test_apply_adversarial_review_reduces_confidence_on_successful_attacks():
    results = AdversarialScientist(min_sample_size=100).attack(
        hypothesis(created_at=date(2026, 7, 1)),
        {"exp": ExperimentResult(statistic=1.0, p_value=0.01, sample_size=9)},
        snapshot(),
    )
    adjusted = apply_adversarial_review(0.8, results)
    assert adjusted < 0.8


def test_apply_adversarial_review_clips_to_valid_range():
    results = AdversarialScientist(min_sample_size=100).attack(
        hypothesis(created_at=date(2026, 7, 1)),
        {"exp": ExperimentResult(statistic=1.0, p_value=0.01, sample_size=1)},
        snapshot(),
    )
    adjusted = apply_adversarial_review(0.05, results)
    assert 0.0 <= adjusted <= 1.0
