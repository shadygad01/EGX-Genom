"""Fast, CI-sized coverage for `patterns.control_suite` (mission Phase 8).

These tests use a single seed per control (not the multi-seed, several-
minute run `scripts/run_pattern_control_suite.py` performs for the
persisted `docs/PATTERN_DISCOVERY_CONTROL_SUITE.md` artifact) -- enough to
prove each construction and the full discover -> validate -> final_holdout
wiring behave correctly, without making the default test suite slow.
"""

from __future__ import annotations

from agx_research.patterns.control_suite import (
    ControlKind,
    _block_momentum_closes,
    build_independent_random_predictor_panel,
    build_lead_lag_panel,
    build_mean_reversion_panel,
    build_momentum_panel,
    build_pure_noise_panel,
    build_shuffled_returns_panel,
    build_shuffled_timestamps_panel,
    run_control,
)


def test_momentum_positive_control_recovers_a_validated_pattern():
    result = run_control("momentum", ControlKind.POSITIVE, [1], description="d")
    assert result.per_seed[0].patterns_validated >= 1
    assert result.kind is ControlKind.POSITIVE


def test_mean_reversion_positive_control_recovers_a_validated_pattern():
    result = run_control("mean_reversion", ControlKind.POSITIVE, [1], description="d")
    assert result.per_seed[0].patterns_validated >= 1


def test_lead_lag_positive_control_recovers_a_validated_pattern():
    result = run_control("lead_lag", ControlKind.POSITIVE, [1], description="d")
    assert result.per_seed[0].patterns_validated >= 1


def test_pure_noise_negative_control_produces_zero_validated_patterns():
    result = run_control("pure_noise", ControlKind.NEGATIVE, [1], description="d")
    assert result.per_seed[0].patterns_validated == 0


def test_shuffled_returns_negative_control_destroys_the_planted_relationship():
    # The unshuffled version of this exact series is `momentum`, which
    # reliably validates -- proving the shuffle, not a weak construction,
    # is what's suppressing the count here.
    result = run_control("shuffled_returns", ControlKind.NEGATIVE, [1], description="d")
    assert result.per_seed[0].patterns_validated <= 1


def test_shuffled_timestamps_negative_control_destroys_the_planted_relationship():
    result = run_control("shuffled_timestamps", ControlKind.NEGATIVE, [1], description="d")
    assert result.per_seed[0].patterns_validated == 0


def test_run_control_acceptance_rule_flips_pass_state_correctly():
    # A positive control that recovers on 1/1 seeds clears ">50% of seeds".
    positive = run_control("momentum", ControlKind.POSITIVE, [1], description="d")
    assert positive.rate == 1.0
    assert positive.passed is True

    # A clean negative control (0/1 seeds) clears "<=40% of seeds".
    negative = run_control("pure_noise", ControlKind.NEGATIVE, [1], description="d")
    assert negative.rate == 0.0
    assert negative.passed is True


def test_panel_builders_produce_valid_ohlc_and_ascending_dates():
    builders = [
        build_momentum_panel, build_mean_reversion_panel, build_lead_lag_panel, build_pure_noise_panel,
        build_shuffled_returns_panel, build_shuffled_timestamps_panel, build_independent_random_predictor_panel,
    ]
    for builder in builders:
        panel = builder(1)
        for ticker, series in panel.series.items():
            assert series.dates == sorted(series.dates)
            assert len(set(series.dates)) == len(series.dates)
            for lo, hi in zip(series.low, series.high):
                assert lo <= hi
            for c in series.close:
                assert c > 0


def test_momentum_and_shuffled_returns_share_the_same_marginal_return_distribution():
    """The shuffle only reorders returns -- it must not change which
    values occur, only when they occur, so the buy-and-hold baseline stays
    a fair comparison for the shuffled negative control. `build_shuffled_
    returns_panel` shuffles the exact same real source series ticker A's
    momentum construction uses (seed 11, block_length=10, drift=0.01,
    noise=0.0005) regardless of its own `seed` argument -- only the
    permutation varies by seed, not the underlying real series."""
    real_closes = _block_momentum_closes(200, 11, block_length=10, daily_drift=0.01, noise_stdev=0.0005)
    real_returns = sorted(
        round((real_closes[i] - real_closes[i - 1]) / real_closes[i - 1], 10) for i in range(1, len(real_closes))
    )
    shuffled_panel = build_shuffled_returns_panel(1).series["A"]
    shuffled_returns = sorted(
        round((shuffled_panel.close[i] - shuffled_panel.close[i - 1]) / shuffled_panel.close[i - 1], 10)
        for i in range(1, len(shuffled_panel.close))
    )
    assert real_returns == shuffled_returns
