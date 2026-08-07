from datetime import date

import pytest

from agx_research.data.schemas import PriceBar
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.decision_service.concentration import (
    CORRELATION_CONCENTRATION_THRESHOLD,
    MAX_CORRELATED_CLUSTER_WEIGHT,
    compute_concentration_caps,
)


def test_no_sector_or_snapshot_leaves_weights_uncapped():
    base_targets = {"A": 0.30, "B": 0.30}
    result = compute_concentration_caps(base_targets)
    assert result == {"A": (0.30, []), "B": (0.30, [])}


def test_sector_cap_limits_the_second_ticker_in_a_crowded_sector():
    # A ranks ahead of B (higher base target); both in "Banks". Combined
    # 0.60 exceeds the 0.40 sector ceiling, so B (the weaker, later-walked
    # idea) is the one trimmed -- A is untouched.
    base_targets = {"A": 0.30, "B": 0.30}
    sectors = {"A": "Banks", "B": "Banks"}
    result = compute_concentration_caps(base_targets, sectors=sectors)
    assert result["A"] == (0.30, [])
    capped_weight, reasons = result["B"]
    assert capped_weight == pytest.approx(0.10)
    assert any("Sector concentration cap" in r for r in reasons)
    assert "Banks" in reasons[0]


def test_sector_cap_does_not_apply_across_different_sectors():
    base_targets = {"A": 0.30, "B": 0.30}
    sectors = {"A": "Banks", "B": "Real Estate"}
    result = compute_concentration_caps(base_targets, sectors=sectors)
    assert result == {"A": (0.30, []), "B": (0.30, [])}


def test_unclassified_ticker_is_never_capped_by_a_fabricated_sector():
    base_targets = {"A": 0.30, "B": 0.30}
    sectors = {"A": "Banks"}  # B has no known sector
    result = compute_concentration_caps(base_targets, sectors=sectors)
    assert result["A"] == (0.30, [])
    assert result["B"] == (0.30, [])


def _snapshot_with_correlated_prices(ticker_a: str, ticker_b: str, *, correlated: bool) -> DatasetSnapshot:
    closes_a = [100.0, 102.0, 101.0, 105.0, 103.0, 108.0]
    closes_b = closes_a if correlated else [100.0, 99.0, 100.5, 98.0, 101.0, 97.0]
    bars = {
        ticker: [
            PriceBar(
                ticker=ticker,
                trade_date=date(2026, 6, i + 1),
                open=c, high=c, low=c, close=c, volume=1_000_000,
            )
            for i, c in enumerate(closes)
        ]
        for ticker, closes in [(ticker_a, closes_a), (ticker_b, closes_b)]
    }
    return DatasetSnapshot(
        id="snap-test", as_of=date(2026, 6, 6), lookback_days=6, macro_lookback_days=6,
        tickers=[ticker_a, ticker_b], macro_series_ids=[], price_history=bars,
    )


def test_correlation_cluster_cap_limits_a_highly_correlated_second_ticker():
    snapshot = _snapshot_with_correlated_prices("A", "B", correlated=True)
    base_targets = {"A": 0.30, "B": 0.30}
    result = compute_concentration_caps(base_targets, snapshot=snapshot)
    assert result["A"] == (0.30, [])
    capped_weight, reasons = result["B"]
    assert capped_weight == pytest.approx(MAX_CORRELATED_CLUSTER_WEIGHT - 0.30)
    assert any("Correlation concentration cap" in r for r in reasons)
    assert f"r={1.00:.2f}" in reasons[0] or "r=1.00" in reasons[0]


def test_correlation_cluster_cap_does_not_apply_to_uncorrelated_tickers():
    snapshot = _snapshot_with_correlated_prices("A", "B", correlated=False)
    base_targets = {"A": 0.30, "B": 0.30}
    result = compute_concentration_caps(base_targets, snapshot=snapshot)
    _, reasons_a = result["A"]
    _, reasons_b = result["B"]
    assert reasons_a == []
    assert reasons_b == []


def test_zero_weight_ticker_is_never_flagged_or_counted_toward_a_cluster():
    snapshot = _snapshot_with_correlated_prices("A", "B", correlated=True)
    base_targets = {"A": 0.0, "B": 0.30}
    result = compute_concentration_caps(base_targets, snapshot=snapshot)
    assert result["A"] == (0.0, [])
    assert result["B"] == (0.30, [])


def test_declared_threshold_constants_are_sane():
    assert 0.0 < CORRELATION_CONCENTRATION_THRESHOLD <= 1.0
    assert 0.0 < MAX_CORRELATED_CLUSTER_WEIGHT <= 1.0
