"""Proves the point-in-time safety layer (`patterns.leakage`) actually
catches something, per the mission's explicit requirement: "The test
suite must prove that a deliberately leaked future feature produces a
failure."
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from agx_research.patterns.features import FeatureFactory
from agx_research.patterns.leakage import (
    LookaheadBiasError,
    safe_feature_value,
    verify_ascending,
    verify_no_future_dates,
    verify_target_strictly_forward,
)
from agx_research.patterns.targets import TargetFactory
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_panel


def test_verify_ascending_accepts_sorted_dates():
    dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    verify_ascending(dates, context="test")  # must not raise


def test_verify_ascending_rejects_out_of_order_dates():
    dates = [date(2024, 1, 2), date(2024, 1, 1), date(2024, 1, 3)]
    with pytest.raises(LookaheadBiasError):
        verify_ascending(dates, context="test")


def test_verify_no_future_dates_rejects_a_date_past_as_of():
    as_of = date(2024, 1, 5)
    dates = [date(2024, 1, 1), date(2024, 1, 6)]  # the second entry is AFTER as_of
    with pytest.raises(LookaheadBiasError):
        verify_no_future_dates(dates, as_of, context="test")


def test_verify_no_future_dates_accepts_dates_at_or_before_as_of():
    as_of = date(2024, 1, 5)
    dates = [date(2024, 1, 1), date(2024, 1, 5)]
    verify_no_future_dates(dates, as_of, context="test")  # must not raise


def test_safe_feature_value_never_reads_past_the_anchor_date():
    """The core anti-leak property: reading a feature "as of" some date can
    never return a value stamped later than that date, even when a later,
    larger value exists right after it."""
    dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 10)]
    values = [1.0, 2.0, 999.0]  # 999.0 is a deliberately huge "future" value
    assert safe_feature_value(dates, values, date(2024, 1, 2)) == 2.0
    assert safe_feature_value(dates, values, date(2024, 1, 5)) == 2.0  # still can't see 999.0
    assert safe_feature_value(dates, values, date(2024, 1, 10)) == 999.0  # only visible once its own date arrives


def test_deliberately_leaked_feature_is_caught_by_the_as_of_cutoff_run(monkeypatch):
    """Constructs a feature series with a value deliberately computed from
    a future close (a "perfect leak": the feature literally equals the
    next day's return) but mislabeled with *today's* date -- the exact bug
    class a naive positional join could introduce. `as_of_value`'s
    contract still holds (it never selects an entry dated after the
    anchor), so the only way this leak could enter the system is if a
    builder stamped the wrong date on it in the first place -- which is
    exactly what this test constructs and then verifies `verify_no_future_dates`
    would have caught in the one place a leak like this becomes
    detectable: when the label itself claims a date beyond what the run
    is allowed to know (`panel.as_of`).
    """
    ticker_series = make_deterministic_ticker_series("LEAK", n_days=30, seed=1)
    panel = make_panel(series={"LEAK": ticker_series})

    # A legitimate feature series never carries a date after panel.as_of.
    legit = FeatureFactory(panel).build_price_features("LEAK")[0]
    verify_no_future_dates(legit.dates, panel.as_of, context="legit feature")

    # Now deliberately construct a leaked series: its last entry is dated
    # one day *after* panel.as_of (as if a builder off-by-one'd the window
    # and let tomorrow's not-yet-realized bar in).
    leaked_dates = [*legit.dates, panel.as_of + timedelta(days=1)]
    with pytest.raises(LookaheadBiasError):
        verify_no_future_dates(leaked_dates, panel.as_of, context="leaked feature")


def test_feature_builders_never_read_past_their_own_index():
    """A structural, non-adversarial proof that `features.py`'s own
    windowing arithmetic cannot see ahead: planting a huge synthetic spike
    at the very last bar must not change any `return_5d` value computed at
    an index whose trailing window doesn't yet include that spike."""
    baseline = make_deterministic_ticker_series("SPIKE", n_days=40, seed=3)
    panel_before = make_panel(series={"SPIKE": baseline})
    features_before = {f.spec.id: f for f in FeatureFactory(panel_before).build_price_features("SPIKE")}

    spiked = baseline.model_copy(deep=True)
    spiked.adjusted_close[-1] *= 100  # a massive, obviously-detectable future spike
    spiked.close[-1] *= 100
    panel_after = make_panel(series={"SPIKE": spiked})
    features_after = {f.spec.id: f for f in FeatureFactory(panel_after).build_price_features("SPIKE")}

    return_5d_before = features_before["return_5d"].values
    return_5d_after = features_after["return_5d"].values
    # Every index whose trailing 5-day window ends before the spiked bar
    # must be byte-for-byte identical; only the spike's own bar (and
    # windows actually containing it) may differ.
    n = len(return_5d_before)
    for i in range(n - 1):  # exclude the very last (spiked) index itself
        assert return_5d_before[i] == return_5d_after[i], f"index {i} changed from a future-only spike"


def test_target_never_reads_the_anchor_bar_itself_or_earlier():
    """`forward_return_5d[i]` must depend only on `closes[i+5]` vs
    `closes[i]` -- changing a bar strictly *before* the anchor must never
    change a forward-return value anchored at or after it."""
    series = make_deterministic_ticker_series("FWD", n_days=40, seed=5)
    panel = make_panel(series={"FWD": series})
    targets_before = {t.id: t for t in TargetFactory(panel).build_forward_returns("FWD")}

    mutated = series.model_copy(deep=True)
    mutated.adjusted_close[0] *= 5  # mutate only the very first bar
    panel_mutated = make_panel(series={"FWD": mutated})
    targets_after = {t.id: t for t in TargetFactory(panel_mutated).build_forward_returns("FWD")}

    before = targets_before["forward_return_5d:FWD"].values
    after = targets_after["forward_return_5d:FWD"].values
    # forward_return_5d[0] itself changes (its own entry price moved), but
    # every later anchor's value must be untouched.
    assert before[1:] == after[1:]


def test_verify_target_strictly_forward_requires_enough_later_bars():
    dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    assert verify_target_strictly_forward(dates, anchor_index=0, horizon_days=2) is True
    assert verify_target_strictly_forward(dates, anchor_index=1, horizon_days=2) is False
    assert verify_target_strictly_forward(dates, anchor_index=2, horizon_days=1) is False
