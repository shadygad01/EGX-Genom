"""Outcome tracking (`patterns.outcomes`) and pattern decay
(`patterns.decay`)."""

from __future__ import annotations

from datetime import date

from agx_research.patterns.candidates import ConditionOperator, FeatureCondition, PatternCandidate
from agx_research.patterns.decay import DecayMonitor, MIN_LIVE_SAMPLE_FOR_DECAY_CHECK
from agx_research.patterns.evaluation import evaluate_outcomes
from agx_research.patterns.live import PatternActivation, RegimeCompatibility
from agx_research.patterns.outcomes import ActivationOutcome, OutcomeRepository, OutcomeTracker
from agx_research.patterns.registry import PatternRegistry, PatternStatus, build_pattern
from agx_research.patterns.validation import WalkForwardResult
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_panel


def _pattern(pattern_id: str, *, hit_rate: float = 0.7, expectancy: float = 0.02):
    candidate = PatternCandidate(
        id=f"c_{pattern_id}", ticker="T",
        conditions=[FeatureCondition(feature_id="return_5d:T", operator=ConditionOperator.GT, threshold=0.0)],
        target_id="forward_return_5d:T", complexity=1,
    )
    distribution = evaluate_outcomes([0.02] * 7 + [-0.01] * 3)
    distribution = distribution.model_copy(update={"hit_rate": hit_rate, "expectancy": expectancy})
    wf_result = WalkForwardResult(
        candidate_id=candidate.id, n_folds_attempted=2, n_folds_valid=2,
        discovery_distribution=distribution, oos_distribution=distribution, oos_sample_size=10,
        survived=True, reasons=["ok"],
    )
    return build_pattern(
        pattern_id=pattern_id, candidate=candidate, horizon_days=5, walk_forward=wf_result, robustness=None,
        discovery_period=(date(2024, 1, 1), date(2024, 6, 1)), validation_period=(date(2024, 6, 1), date(2024, 9, 1)),
        number_of_tests=50, status=PatternStatus.VALIDATED, produced_by="test@1.0.0",
    )


def test_outcome_tracker_fills_in_horizons_as_they_become_available():
    series = make_deterministic_ticker_series("T", n_days=40, seed=1)
    panel = make_panel(series={"T": series})
    activation_date = series.dates[5]

    repo = OutcomeRepository()
    tracker = OutcomeTracker(repo)
    pattern = _pattern("p1")
    activation = PatternActivation(
        id="act1", pattern_id="p1", ticker="T", as_of=activation_date,
        historical_expectancy=0.02, regime_compatibility=RegimeCompatibility.UNKNOWN,
    )
    outcome = tracker.record_activation(activation, pattern, features_at_activation={"return_5d:T": 0.02})
    assert outcome.actual_5d is None

    updated = tracker.update_outcomes(panel)
    assert len(updated) == 1
    refreshed = repo.latest(outcome.id)
    assert refreshed.version == 2
    assert refreshed.actual_5d is not None
    entry = series.adjusted_close[5]
    expected_5d = (series.adjusted_close[10] - entry) / entry
    assert abs(refreshed.actual_5d - expected_5d) < 1e-9
    assert refreshed.mfe is not None and refreshed.mae is not None


def test_outcome_tracker_skips_a_ticker_no_longer_in_the_panel():
    repo = OutcomeRepository()
    tracker = OutcomeTracker(repo)
    pattern = _pattern("p1")
    activation = PatternActivation(
        id="act1", pattern_id="p1", ticker="UNKNOWN", as_of=date(2024, 1, 1),
        historical_expectancy=0.02, regime_compatibility=RegimeCompatibility.UNKNOWN,
    )
    tracker.record_activation(activation, pattern, features_at_activation={})
    series = make_deterministic_ticker_series("T", n_days=10, seed=1)
    panel = make_panel(series={"T": series})
    assert tracker.update_outcomes(panel) == []


def test_decay_check_reports_insufficient_sample_honestly():
    registry = PatternRegistry()
    registry.add(_pattern("p1"))
    monitor = DecayMonitor(registry, OutcomeRepository(), min_live_sample=MIN_LIVE_SAMPLE_FOR_DECAY_CHECK)
    check = monitor.check("p1", as_of=date(2024, 6, 1))
    assert check.flagged is False
    assert check.live_sample_size == 0
    assert "below the floor" in check.reasons[0]


def _add_outcomes(repo: OutcomeRepository, pattern_id: str, actual_values: list[float]) -> None:
    for i, value in enumerate(actual_values):
        repo.add(
            ActivationOutcome(
                id=f"outcome_{pattern_id}_{i}", activation_id=f"act_{i}", pattern_id=pattern_id, ticker="T",
                activation_time=date(2024, 1, 1), predicted_expectancy=0.02, predicted_hit_rate=0.7,
                actual_20d=value,
            )
        )


def test_decay_check_flags_a_material_hit_rate_drop():
    registry = PatternRegistry()
    registry.add(_pattern("p1", hit_rate=0.8, expectancy=0.02))
    repo = OutcomeRepository()
    # Historical hit rate 0.8; live sample is only 20% positive -- a huge drop.
    _add_outcomes(repo, "p1", [0.01] * 2 + [-0.01] * 8)
    monitor = DecayMonitor(registry, repo, min_live_sample=5, hit_rate_drop_threshold=0.2)
    check = monitor.check("p1", as_of=date(2024, 6, 1))
    assert check.flagged is True
    assert check.live_hit_rate == 0.2

    updated = registry.latest("p1")
    assert updated.validation_status is PatternStatus.WEAKENING
    assert updated.version == 2


def test_decay_check_does_not_flag_consistent_performance():
    registry = PatternRegistry()
    registry.add(_pattern("p1", hit_rate=0.7, expectancy=0.02))
    repo = OutcomeRepository()
    _add_outcomes(repo, "p1", [0.02] * 7 + [-0.01] * 3)  # matches historical 0.7 hit rate
    monitor = DecayMonitor(registry, repo, min_live_sample=5)
    check = monitor.check("p1", as_of=date(2024, 6, 1))
    assert check.flagged is False
    assert registry.latest("p1").validation_status is PatternStatus.VALIDATED  # unchanged
