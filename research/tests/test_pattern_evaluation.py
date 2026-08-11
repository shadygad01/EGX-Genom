"""Discovery statistics for `patterns.evaluation`."""

from __future__ import annotations

from datetime import date, timedelta

from agx_research.patterns.evaluation import evaluate_outcomes


def test_evaluate_outcomes_returns_none_below_two_observations():
    assert evaluate_outcomes([]) is None
    assert evaluate_outcomes([0.01]) is None


def test_evaluate_outcomes_basic_statistics_match_hand_computation():
    outcomes = [0.02, -0.01, 0.03, 0.01, -0.02]
    distribution = evaluate_outcomes(outcomes)
    assert distribution.sample_count == 5
    assert distribution.hit_rate == 3 / 5
    assert abs(distribution.mean_outcome - sum(outcomes) / 5) < 1e-12
    assert distribution.expectancy == distribution.mean_outcome
    assert distribution.median_outcome == 0.01


def test_profit_factor_is_none_when_there_are_no_losses():
    distribution = evaluate_outcomes([0.01, 0.02, 0.03])
    assert distribution.profit_factor is None


def test_profit_factor_matches_hand_computation_with_losses():
    outcomes = [0.02, 0.03, -0.01, -0.02]
    distribution = evaluate_outcomes(outcomes)
    expected = (0.02 + 0.03) / abs(-0.01 - 0.02)
    assert abs(distribution.profit_factor - expected) < 1e-9


def test_confidence_interval_contains_the_mean_for_a_symmetric_sample():
    outcomes = [0.01, -0.01, 0.02, -0.02, 0.015, -0.015, 0.005, -0.005] * 5
    distribution = evaluate_outcomes(outcomes, bootstrap_iterations=500, seed=1)
    low, high = distribution.confidence_interval_95
    assert low <= distribution.mean_outcome <= high


def test_p_value_is_small_for_an_obviously_nonzero_mean():
    outcomes = [0.05] * 30  # zero variance, huge, unambiguous positive mean
    distribution = evaluate_outcomes(outcomes, bootstrap_iterations=500, seed=1)
    assert distribution.p_value_bootstrap == 0.0


def test_stability_score_is_one_when_every_time_bucket_agrees_in_sign():
    start = date(2024, 1, 1)
    outcomes = [0.02] * 12  # consistently positive across the whole span
    dates = [start + timedelta(days=i) for i in range(12)]
    distribution = evaluate_outcomes(outcomes, dates=dates, n_time_buckets=4)
    assert distribution.stability_score == 1.0


def test_stability_score_drops_when_buckets_disagree_in_sign():
    start = date(2024, 1, 1)
    outcomes = [0.02] * 6 + [-0.02] * 6  # first half positive, second half negative
    dates = [start + timedelta(days=i) for i in range(12)]
    distribution = evaluate_outcomes(outcomes, dates=dates, n_time_buckets=4)
    assert distribution.stability_score < 1.0


def test_downside_deviation_is_zero_when_nothing_is_negative():
    distribution = evaluate_outcomes([0.01, 0.02, 0.03])
    assert distribution.downside_deviation == 0.0
