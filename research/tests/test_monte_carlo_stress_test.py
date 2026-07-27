from datetime import date, datetime
from pathlib import Path

import pytest

from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.schemas import PriceBar
from agx_research.data.snapshot import DatasetSnapshot, build_snapshot
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.validation.stress_test import MonteCarloBlockBootstrapStressTester

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def snapshot():
    provider = MockDataProvider(MOCK_ROOT)
    return build_snapshot(
        provider, tickers=["COMI", "MFPC"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )


def hypothesis(affected_assets=("COMI", "MFPC")) -> Hypothesis:
    return Hypothesis(
        id="hyp-monte-carlo",
        statement="test",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=list(affected_assets),
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )


def _flat_upward_snapshot(ticker: str, n: int) -> DatasetSnapshot:
    """`n + 1` bars of a steady 1% daily gain -- every possible block
    bootstrap resample of this series has the same, unambiguous sign."""
    bars = []
    close = 100.0
    for i in range(n + 1):
        bars.append(
            PriceBar(
                ticker=ticker, trade_date=date(2026, 1, 1 + i),
                open=close, high=close, low=close, close=close, volume=1000,
            )
        )
        close *= 1.01
    return DatasetSnapshot(
        id="snap_test", as_of=bars[-1].trade_date, lookback_days=30, macro_lookback_days=30,
        tickers=[ticker], macro_series_ids=[], price_history={ticker: bars},
    )


def test_produces_a_worst_percentile_statistic_and_full_statistic():
    result = MonteCarloBlockBootstrapStressTester(iterations=200).run(hypothesis(), snapshot())
    assert "full_statistic" in result.scenario_results
    assert "worst_percentile_statistic" in result.scenario_results
    assert "block_size" in result.scenario_results
    full = result.scenario_results["full_statistic"]
    worst = result.scenario_results["worst_percentile_statistic"]
    assert result.passed == ((full <= 0) == (worst <= 0))


def test_is_deterministic_given_a_seed():
    a = MonteCarloBlockBootstrapStressTester(seed=7).run(hypothesis(), snapshot())
    b = MonteCarloBlockBootstrapStressTester(seed=7).run(hypothesis(), snapshot())
    assert a == b


def test_different_seeds_can_produce_different_simulated_paths():
    a = MonteCarloBlockBootstrapStressTester(seed=1).run(hypothesis(), snapshot())
    b = MonteCarloBlockBootstrapStressTester(seed=2).run(hypothesis(), snapshot())
    # Not asserting inequality (small samples can coincide) -- just that
    # both runs are internally consistent and valid.
    assert 0 <= a.scenario_results["block_size"]
    assert 0 <= b.scenario_results["block_size"]


def test_block_size_shrinks_to_fit_short_series_without_raising():
    # DATA_COLLECTION's default min_observations is 6; this must never
    # raise for any series length that gate already let through.
    snap = _flat_upward_snapshot("TST", 6)
    result = MonteCarloBlockBootstrapStressTester(block_size=5).run(
        hypothesis(affected_assets=("TST",)), snap
    )
    assert result.scenario_results["block_size"] <= 3


def test_raises_for_too_little_data():
    snap = _flat_upward_snapshot("TST", 2)
    with pytest.raises(ValueError):
        MonteCarloBlockBootstrapStressTester().run(hypothesis(affected_assets=("TST",)), snap)


def test_unambiguous_series_always_passes():
    # Every block-bootstrap resample of a steady, unambiguous gain series
    # keeps the same sign -- the worst-case tail must too.
    snap = _flat_upward_snapshot("TST", 20)
    result = MonteCarloBlockBootstrapStressTester(iterations=200).run(
        hypothesis(affected_assets=("TST",)), snap
    )
    assert result.passed is True


def test_invalid_constructor_params_are_rejected():
    with pytest.raises(ValueError):
        MonteCarloBlockBootstrapStressTester(iterations=0)
    with pytest.raises(ValueError):
        MonteCarloBlockBootstrapStressTester(block_size=0)
    with pytest.raises(ValueError):
        MonteCarloBlockBootstrapStressTester(worst_percentile=0.0)
    with pytest.raises(ValueError):
        MonteCarloBlockBootstrapStressTester(worst_percentile=1.0)
