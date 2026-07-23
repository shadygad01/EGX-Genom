from datetime import date, datetime
from pathlib import Path

import pytest

from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.validation.backtest import NaiveDirectionalBacktester
from agx_research.validation.stress_test import HistoricalWorstWindowStressTester

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def snapshot():
    provider = MockDataProvider(MOCK_ROOT)
    return build_snapshot(
        provider, tickers=["COMI", "MFPC"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )


def hypothesis(affected_assets=("COMI", "MFPC")) -> Hypothesis:
    return Hypothesis(
        id="hyp-validators",
        statement="test",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=list(affected_assets),
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )


def test_backtester_reports_hit_rate_and_sharpe_for_a_pair():
    result = NaiveDirectionalBacktester().run(hypothesis(), snapshot())
    assert result.hit_rate is not None and 0.0 <= result.hit_rate <= 1.0
    assert result.sharpe_ratio is not None
    assert "transaction costs" in result.notes


def test_backtester_handles_single_asset_momentum_reading():
    result = NaiveDirectionalBacktester().run(hypothesis(affected_assets=("COMI",)), snapshot())
    assert result.hit_rate is not None


def test_backtester_is_deterministic():
    a = NaiveDirectionalBacktester().run(hypothesis(), snapshot())
    b = NaiveDirectionalBacktester().run(hypothesis(), snapshot())
    assert a == b


def test_backtester_thresholds_gate_the_pass():
    permissive = NaiveDirectionalBacktester(min_hit_rate=0.0, min_sharpe=-100.0)
    assert permissive.run(hypothesis(), snapshot()).passed is True

    impossible = NaiveDirectionalBacktester(min_hit_rate=1.01)
    assert impossible.run(hypothesis(), snapshot()).passed is False


def test_backtester_requires_enough_data():
    empty_snapshot = build_snapshot(
        MockDataProvider(MOCK_ROOT),
        tickers=["NOPE"],
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    with pytest.raises(ValueError):
        NaiveDirectionalBacktester().run(hypothesis(affected_assets=("NOPE",)), empty_snapshot)


def test_stress_tester_locates_the_worst_window_and_checks_sign():
    result = HistoricalWorstWindowStressTester(window=5).run(hypothesis(), snapshot())
    assert "worst_window_cumulative_return" in result.scenario_results
    assert "full_window_statistic" in result.scenario_results
    assert "stressed_window_statistic" in result.scenario_results
    full = result.scenario_results["full_window_statistic"]
    stressed = result.scenario_results["stressed_window_statistic"]
    assert result.passed == ((full <= 0) == (stressed <= 0))


def test_stress_tester_is_deterministic():
    a = HistoricalWorstWindowStressTester().run(hypothesis(), snapshot())
    b = HistoricalWorstWindowStressTester().run(hypothesis(), snapshot())
    assert a == b
