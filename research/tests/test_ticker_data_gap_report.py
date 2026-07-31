from datetime import date
from pathlib import Path

from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.financials.collected import CollectedFinancialStatementProvider
from agx_research.market_memory.state import MarketState, TradingSession
from agx_research.meta.readiness import assess_decision_readiness, build_ticker_data_gap_report

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def _readiness_row(tmp_path, ticker: str, tickers: list[str], macro_series_ids: list[str]):
    snapshot = build_snapshot(
        MockDataProvider(MOCK_ROOT if ticker == "COMI" else tmp_path),
        tickers=tickers,
        macro_series_ids=macro_series_ids,
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    state = MarketState(
        as_of=date(2026, 6, 14),
        dataset_snapshot=snapshot,
        constituents={t: t for t in tickers},
        sectors={},
        trading_session=TradingSession(session_date=date(2026, 6, 14), is_trading_day=True),
    )
    return assess_decision_readiness(state, CollectedFinancialStatementProvider(tmp_path), [])


def test_gap_report_splits_readiness_into_five_named_layers(tmp_path):
    rows = _readiness_row(tmp_path, "COMI", ["COMI"], ["BRENT_USD"])
    reports = build_ticker_data_gap_report(rows)
    assert len(reports) == 1
    report = reports[0]
    assert report.ticker == "COMI"
    assert {layer.layer for layer in report.layers} == {
        "valuation",
        "disclosures",
        "news",
        "macro",
        "knowledge",
    }
    valuation = next(layer for layer in report.layers if layer.layer == "valuation")
    assert valuation.count == 0
    assert valuation.complete is False
    assert valuation.completeness_pct == 0.0
    assert report.swing_ready is False
    assert report.investment_ready is False
    assert Horizon.INVESTMENT not in report.ready_horizons


def test_gap_report_never_disagrees_with_the_readiness_it_describes(tmp_path):
    rows = _readiness_row(tmp_path, "SWDY", ["SWDY"], [])
    reports = build_ticker_data_gap_report(rows)
    report = reports[0]
    assert report.status == rows[0].status
    assert report.decision == rows[0].decision
    assert report.blockers == rows[0].blockers
    assert report.ready_horizons == rows[0].ready_horizons


def test_layer_completeness_caps_at_100_percent(tmp_path):
    rows = _readiness_row(tmp_path, "COMI", ["COMI"], ["BRENT_USD", "EGP_USD"])
    report = build_ticker_data_gap_report(rows)[0]
    for layer in report.layers:
        assert 0.0 <= layer.completeness_pct <= 100.0
    assert 0.0 <= report.overall_completeness_pct <= 100.0
