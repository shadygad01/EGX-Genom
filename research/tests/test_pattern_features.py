"""Feature generation correctness for `patterns.features`."""

from __future__ import annotations

from datetime import date

from agx_research.patterns.features import FeatureCategory, FeatureFactory
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_flat_ticker_series, make_panel


def test_return_nd_matches_hand_computed_value():
    series = make_deterministic_ticker_series("T", n_days=30, seed=1)
    panel = make_panel(series={"T": series})
    features = {f.spec.id: f for f in FeatureFactory(panel).build_price_features("T")}
    return_5d = features["return_5d"]
    idx = 10
    expected = (series.adjusted_close[idx] - series.adjusted_close[idx - 5]) / series.adjusted_close[idx - 5]
    assert return_5d.values[idx] == expected
    assert return_5d.values[4] is None  # not enough history yet
    assert return_5d.values[3] is None


def test_every_feature_series_carries_metadata():
    series = make_deterministic_ticker_series("T", n_days=30, seed=1)
    panel = make_panel(series={"T": series})
    for feature in FeatureFactory(panel).build_all():
        assert feature.spec.description
        assert feature.spec.category in FeatureCategory


def test_as_of_value_forward_fills_from_the_most_recent_entry_at_or_before():
    series = make_deterministic_ticker_series("T", n_days=30, seed=1)
    panel = make_panel(series={"T": series})
    features = {f.spec.id: f for f in FeatureFactory(panel).build_price_features("T")}
    return_5d = features["return_5d"]
    d5, d6 = series.dates[5], series.dates[6]
    assert return_5d.as_of_value(d5) == return_5d.values[5]
    # A date strictly between two trading days still resolves to the
    # most recent prior value, never None just because it isn't an exact
    # trading day.
    between = date(min(d5, d6).year, min(d5, d6).month, min(d5, d6).day)
    assert return_5d.as_of_value(between) == return_5d.values[5]


def test_as_of_value_returns_none_before_any_data_exists():
    series = make_deterministic_ticker_series("T", n_days=30, seed=1)
    panel = make_panel(series={"T": series})
    features = {f.spec.id: f for f in FeatureFactory(panel).build_price_features("T")}
    assert features["return_5d"].as_of_value(date(1999, 1, 1)) is None


def test_volatility_is_zero_on_a_flat_series():
    series = make_flat_ticker_series("FLAT", n_days=15)
    panel = make_panel(series={"FLAT": series})
    features = {f.spec.id: f for f in FeatureFactory(panel).build_price_features("FLAT")}
    vol_5d = features["volatility_5d"]
    non_null = [v for v in vol_5d.values if v is not None]
    assert non_null and all(v == 0.0 for v in non_null)


def test_relative_volume_excludes_todays_own_bar_from_its_baseline():
    """`relative_volume` must be computed from the trailing window
    *excluding* the current day -- otherwise every day would be compared
    partly against itself."""
    series = make_deterministic_ticker_series("T", n_days=30, seed=2)
    panel = make_panel(series={"T": series})
    features = {f.spec.id: f for f in FeatureFactory(panel).build_volume_features("T")}
    relative_volume = features["relative_volume_5d"]
    idx = 10
    trailing = series.volume[idx - 5 : idx]
    expected = series.volume[idx] / (sum(trailing) / len(trailing))
    assert abs(relative_volume.values[idx] - expected) < 1e-9


def test_cross_sectional_features_only_populate_market_scope_for_market_wide_ones():
    a = make_deterministic_ticker_series("A", n_days=40, seed=1, sector="Banks")
    b = make_deterministic_ticker_series("B", n_days=40, seed=2, sector="Banks")
    panel = make_panel(series={"A": a, "B": b})
    features = FeatureFactory(panel).build_cross_sectional_features()
    market_wide = [f for f in features if f.spec.id in ("market_breadth", "volume_concentration_hhi")]
    assert market_wide and all(f.ticker == "" for f in market_wide)
    per_ticker = [f for f in features if f.spec.id.startswith("market_percentile_")]
    assert per_ticker and all(f.ticker in ("A", "B") for f in per_ticker)


def test_market_breadth_is_the_fraction_of_positive_return_tickers():
    a = make_deterministic_ticker_series("A", n_days=25, seed=1)
    b = make_deterministic_ticker_series("B", n_days=25, seed=2)
    panel = make_panel(series={"A": a, "B": b})
    features = {f.id: f for f in FeatureFactory(panel).build_cross_sectional_features()}
    breadth = features["market_breadth:MARKET"]
    calendar = panel.all_dates()
    idx = 10
    a_ret = (a.adjusted_close[idx] - a.adjusted_close[idx - 1]) / a.adjusted_close[idx - 1]
    b_ret = (b.adjusted_close[idx] - b.adjusted_close[idx - 1]) / b.adjusted_close[idx - 1]
    expected = sum(1 for r in (a_ret, b_ret) if r > 0) / 2
    assert abs(breadth.values[calendar.index(a.dates[idx])] - expected) < 1e-9


def test_fundamental_features_are_empty_without_financial_statements():
    """Honest empty result -- see docs/PATTERN_DISCOVERY_DATA_AUDIT.md:
    no financial statements are collected for any ticker today."""
    series = make_deterministic_ticker_series("T", n_days=15, seed=1)
    panel = make_panel(series={"T": series})
    assert FeatureFactory(panel).build_fundamental_features("T") == []
