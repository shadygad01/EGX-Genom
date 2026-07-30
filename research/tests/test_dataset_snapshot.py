from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def provider() -> MockDataProvider:
    return MockDataProvider(MOCK_ROOT)


def test_same_query_produces_same_id():
    snap_a = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    snap_b = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    assert snap_a.id == snap_b.id


def test_different_as_of_produces_different_id():
    snap_a = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )
    snap_b = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 10), lookback_days=30
    )
    assert snap_a.id != snap_b.id


def test_no_data_after_as_of():
    snapshot = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 9), lookback_days=30
    )
    assert all(bar.trade_date <= date(2026, 6, 9) for bar in snapshot.price_history["COMI"])


def test_bundles_corporate_events_and_macro_and_news():
    snapshot = build_snapshot(
        provider(),
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD", "EGP_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    assert len(snapshot.corporate_events["MFPC"]) == 1
    assert len(snapshot.macro_series["BRENT_USD"]) > 0
    assert len(snapshot.news) > 0


def test_financial_statements_empty_when_no_provider_given():
    snapshot = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )
    assert snapshot.financial_statements == {}


def test_financial_statements_populated_when_provider_given():
    from agx_research.financials.provider import FinancialStatementProvider
    from agx_research.financials.schema import FinancialStatementLineItem

    class FakeProvider(FinancialStatementProvider):
        def get_line_items(self, ticker, start, end, *, statement_type=None):
            if ticker != "COMI":
                return []
            return [
                FinancialStatementLineItem(
                    ticker="COMI",
                    period_end_date=date(2025, 12, 31),
                    period_type="ANNUAL",
                    statement_type="INCOME_STATEMENT",
                    line_item="revenue",
                    value=1_000_000,
                )
            ]

    snapshot = build_snapshot(
        provider(),
        tickers=["COMI", "MFPC"],
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=30,
        financials_provider=FakeProvider(),
    )
    assert len(snapshot.financial_statements["COMI"]) == 1
    assert snapshot.financial_statements["COMI"][0].line_item == "revenue"
    assert snapshot.financial_statements["MFPC"] == []


def test_financial_statements_respects_financials_lookback_days():
    from agx_research.financials.provider import FinancialStatementProvider
    from agx_research.financials.schema import FinancialStatementLineItem

    class FakeProvider(FinancialStatementProvider):
        def get_line_items(self, ticker, start, end, *, statement_type=None):
            period_end_date = date(2020, 1, 1)  # far outside any reasonable window
            if not (start <= period_end_date <= end):
                return []
            return [
                FinancialStatementLineItem(
                    ticker=ticker,
                    period_end_date=period_end_date,
                    period_type="ANNUAL",
                    statement_type="INCOME_STATEMENT",
                    line_item="revenue",
                    value=1.0,
                )
            ]

    snapshot = build_snapshot(
        provider(),
        tickers=["COMI"],
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=30,
        financials_provider=FakeProvider(),
        financials_lookback_days=365,
    )
    assert snapshot.financial_statements["COMI"] == []


def test_two_snapshots_differing_only_in_financials_provider_get_different_ids():
    from agx_research.financials.provider import FinancialStatementProvider
    from agx_research.financials.schema import FinancialStatementLineItem

    class FakeProvider(FinancialStatementProvider):
        def get_line_items(self, ticker, start, end, *, statement_type=None):
            return [
                FinancialStatementLineItem(
                    ticker=ticker,
                    period_end_date=date(2026, 1, 1),
                    period_type="ANNUAL",
                    statement_type="INCOME_STATEMENT",
                    line_item="revenue",
                    value=1.0,
                )
            ]

    without = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )
    with_financials = build_snapshot(
        provider(),
        tickers=["COMI"],
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=30,
        financials_provider=FakeProvider(),
    )
    assert without.id != with_financials.id


def test_macro_lookback_days_defaults_to_lookback_days():
    snapshot = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    assert snapshot.macro_lookback_days == 30


def test_macro_lookback_days_windows_macro_series_independently_of_price_history():
    # Mock BRENT_USD/COMI both start 2026-06-01 -- a 5-day price window (start
    # 2026-06-09) drops the early bars, but a 30-day macro window still
    # covers the whole mock fixture. This is the exact independence that a
    # single shared window doesn't give annual/quarterly macro sources.
    snapshot = build_snapshot(
        provider(),
        tickers=["COMI"],
        macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=5,
        macro_lookback_days=30,
    )
    assert all(bar.trade_date >= date(2026, 6, 9) for bar in snapshot.price_history["COMI"])
    assert any(
        obs.observation_date < date(2026, 6, 9) for obs in snapshot.macro_series["BRENT_USD"]
    )


def test_macro_series_sources_drops_not_yet_knowable_observations():
    # Mock BRENT_USD has observations through 2026-06-14; a declared
    # 30-day "worldbank" publication lag means only observations dated on
    # or before as_of - 30 days are knowable yet.
    without_lag = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    with_lag = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
        macro_series_sources={"BRENT_USD": "worldbank"},
    )
    assert len(with_lag.macro_series["BRENT_USD"]) < len(without_lag.macro_series["BRENT_USD"])
    assert all(
        obs.observation_date <= date(2026, 5, 15) for obs in with_lag.macro_series["BRENT_USD"]
    )


def test_pattern_lookback_days_defaults_to_empty_long_price_history():
    snapshot = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=[],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    assert snapshot.pattern_lookback_days == 0
    assert snapshot.long_price_history == {}
    assert snapshot.long_corporate_events == {}


def test_pattern_lookback_days_windows_price_history_independently():
    # Mock COMI data starts 2026-06-01. A 5-day price window (start
    # 2026-06-09) drops the early bars from price_history, but a 30-day
    # pattern window still reaches back to the fixture's start -- the same
    # independence macro_lookback_days already gives macro series.
    snapshot = build_snapshot(
        provider(),
        tickers=["COMI"],
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=5,
        pattern_lookback_days=30,
    )
    assert all(bar.trade_date >= date(2026, 6, 9) for bar in snapshot.price_history["COMI"])
    assert any(bar.trade_date < date(2026, 6, 9) for bar in snapshot.long_price_history["COMI"])
    assert len(snapshot.long_price_history["COMI"]) > len(snapshot.price_history["COMI"])


def test_macro_series_sources_unmapped_series_id_unaffected():
    with_map = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
        macro_series_sources={"SOME_OTHER_SERIES": "worldbank"},
    )
    without_map = build_snapshot(
        provider(), tickers=["COMI"], macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14), lookback_days=30,
    )
    assert with_map.macro_series["BRENT_USD"] == without_map.macro_series["BRENT_USD"]
