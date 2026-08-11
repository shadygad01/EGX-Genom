"""Target calculation correctness for `patterns.targets`."""

from __future__ import annotations

from agx_research.patterns.targets import TargetFactory
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_panel


def test_forward_return_matches_hand_computed_value():
    series = make_deterministic_ticker_series("T", n_days=30, seed=1)
    panel = make_panel(series={"T": series})
    targets = {t.id: t for t in TargetFactory(panel).build_forward_returns("T")}
    forward_5d = targets["forward_return_5d:T"]
    idx = 5
    expected = (series.adjusted_close[idx + 5] - series.adjusted_close[idx]) / series.adjusted_close[idx]
    assert forward_5d.values[idx] == expected


def test_forward_return_is_none_when_horizon_runs_past_available_data():
    series = make_deterministic_ticker_series("T", n_days=10, seed=1)
    panel = make_panel(series={"T": series})
    targets = {t.id: t for t in TargetFactory(panel).build_forward_returns("T")}
    forward_5d = targets["forward_return_5d:T"]
    assert forward_5d.values[-1] is None
    assert forward_5d.values[-2] is None  # index 8: 8+5=13 >= 10, still out of range


def test_mfe_and_mae_use_only_strictly_later_bars():
    series = make_deterministic_ticker_series("T", n_days=30, seed=2)
    panel = make_panel(series={"T": series})
    targets = {t.id: t for t in TargetFactory(panel).build_mfe_mae("T")}
    mfe = targets["mfe_5d:T"]
    mae = targets["mae_5d:T"]
    idx = 4
    entry = series.adjusted_close[idx]
    window_highs = series.high[idx + 1 : idx + 6]
    window_lows = series.low[idx + 1 : idx + 6]
    assert abs(mfe.values[idx] - (max(window_highs) - entry) / entry) < 1e-9
    assert abs(mae.values[idx] - (min(window_lows) - entry) / entry) < 1e-9
    # MFE/MAE are bounded by the window's own high/low band around a
    # possibly-drifting entry price -- not guaranteed <=0/>=0 in a trending
    # series, only that they match the hand-computed window extremes above.


def test_probability_targets_are_binary_indicators_of_the_forward_return():
    series = make_deterministic_ticker_series("T", n_days=30, seed=3)
    panel = make_panel(series={"T": series})
    forward = {t.id: t for t in TargetFactory(panel).build_forward_returns("T")}["forward_return_5d:T"]
    prob = {t.id: t for t in TargetFactory(panel).build_probability_targets("T")}["prob_positive_5d:T"]
    for f, p in zip(forward.values, prob.values):
        if f is None:
            assert p is None
        else:
            assert p == (1.0 if f > 0 else 0.0)


def test_relative_return_market_is_the_ticker_minus_equal_weighted_peer_mean():
    a = make_deterministic_ticker_series("A", n_days=30, seed=1)
    b = make_deterministic_ticker_series("B", n_days=30, seed=2)
    panel = make_panel(series={"A": a, "B": b})
    relative = {t.id: t for t in TargetFactory(panel).build_relative_targets("A")}["relative_return_market_5d:A"]
    factory = TargetFactory(panel)
    own = dict(zip(a.dates, factory._forward_return_series(a.adjusted_close, 5)))
    # The market forward return is the equal-weighted mean across every
    # ticker in the panel (including A itself), not just its peer B alone.
    market = factory._market_forward_returns(5)
    for d, value in zip(a.dates, relative.values):
        if own.get(d) is None or market.get(d) is None:
            assert value is None
        else:
            assert abs(value - (own[d] - market[d])) < 1e-9


def test_target_value_at_returns_none_for_unknown_date():
    series = make_deterministic_ticker_series("T", n_days=10, seed=1)
    panel = make_panel(series={"T": series})
    forward = TargetFactory(panel).build_forward_returns("T")[0]
    from datetime import date

    assert forward.value_at(date(1999, 1, 1)) is None
