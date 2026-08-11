"""Strengthened multiple-testing control (Mission 2 Phase 7):
`patterns.multiple_testing_family`."""

from __future__ import annotations

from agx_research.patterns.candidates import ConditionOperator, FeatureCondition, PatternCandidate
from agx_research.patterns.multiple_testing_family import (
    block_bootstrap_p_value,
    candidate_family_key,
    deflated_sharpe_ratio,
    expected_max_sharpe_under_noise,
    family_corrected_p_value,
    group_by_family,
    sharpe_like_statistic,
)


def _candidate(feature_id: str, ticker="T", target_id="forward_return_5d:T", regime=None) -> PatternCandidate:
    return PatternCandidate(
        id=f"c_{feature_id}_{ticker}",
        ticker=ticker,
        conditions=[FeatureCondition(feature_id=feature_id, operator=ConditionOperator.GT, threshold=0.0)],
        regime_filter=regime,
        target_id=target_id,
        complexity=1,
    )


def test_family_key_groups_window_variants_of_the_same_feature():
    a = candidate_family_key(_candidate("return_5d:T"))
    b = candidate_family_key(_candidate("return_10d:T"))
    c = candidate_family_key(_candidate("return_5d:T"))
    assert a == c  # identical
    assert a == b  # window-stripped base is identical too


def test_family_key_separates_different_tickers_targets_and_regimes():
    base = candidate_family_key(_candidate("return_5d:T"))
    other_ticker = candidate_family_key(_candidate("return_5d:U", ticker="U"))
    other_target = candidate_family_key(_candidate("return_5d:T", target_id="mfe_5d:T"))
    regime_condition = FeatureCondition(feature_id="market_breadth:MARKET", operator=ConditionOperator.GT, threshold=0.5)
    with_regime = candidate_family_key(_candidate("return_5d:T", regime=regime_condition))
    assert base != other_ticker
    assert base != other_target
    assert base != with_regime


def test_group_by_family_groups_correctly():
    candidates = [_candidate("return_5d:T"), _candidate("return_10d:T"), _candidate("return_5d:U", ticker="U")]
    families = group_by_family(candidates)
    assert len(families) == 2
    sizes = sorted(len(v) for v in families.values())
    assert sizes == [1, 2]


def test_family_corrected_p_value_scales_with_family_size():
    assert family_corrected_p_value(0.01, 1) == 0.01
    assert family_corrected_p_value(0.01, 10) == 0.10
    assert family_corrected_p_value(0.5, 10) == 1.0  # capped


def test_block_bootstrap_p_value_is_small_for_an_obvious_nonzero_mean():
    outcomes = [0.05] * 30
    assert block_bootstrap_p_value(outcomes, iterations=300, seed=1) < 0.05


def test_block_bootstrap_p_value_is_large_for_a_zero_centered_sample():
    outcomes = [0.02, -0.02, 0.03, -0.03, 0.01, -0.01, 0.025, -0.025] * 5
    p = block_bootstrap_p_value(outcomes, iterations=300, seed=1)
    assert p > 0.05


def test_block_bootstrap_p_value_returns_one_for_too_little_data():
    assert block_bootstrap_p_value([0.01, 0.02], iterations=100) == 1.0


def test_sharpe_like_statistic_zero_for_zero_variance_or_short_sample():
    assert sharpe_like_statistic([]) == 0.0
    assert sharpe_like_statistic([0.01]) == 0.0
    assert sharpe_like_statistic([0.01, 0.01, 0.01]) == 0.0  # zero stdev


def test_expected_max_sharpe_grows_with_more_trials():
    small = expected_max_sharpe_under_noise(10, sharpe_variance=1.0)
    large = expected_max_sharpe_under_noise(10_000, sharpe_variance=1.0)
    assert large > small > 0


def test_deflated_sharpe_ratio_is_lower_for_more_trials_given_the_same_outcomes():
    outcomes = [0.02, 0.01, 0.03, -0.01, 0.015, 0.025, -0.005, 0.02, 0.01, 0.03]
    dsr_few_trials = deflated_sharpe_ratio(outcomes, n_trials=2)
    dsr_many_trials = deflated_sharpe_ratio(outcomes, n_trials=5000)
    assert dsr_few_trials is not None and dsr_many_trials is not None
    assert dsr_many_trials < dsr_few_trials


def test_deflated_sharpe_ratio_none_for_too_little_data():
    assert deflated_sharpe_ratio([0.01, 0.02], n_trials=10) is None
