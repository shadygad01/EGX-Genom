from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def provider() -> MockDataProvider:
    return MockDataProvider(MOCK_ROOT)


def test_get_price_history_returns_bars_in_range_sorted_by_date():
    bars = provider().get_price_history("COMI", date(2026, 6, 2), date(2026, 6, 4))
    assert [b.trade_date for b in bars] == [date(2026, 6, 2), date(2026, 6, 3), date(2026, 6, 4)]
    assert bars[0].close == 69.00


def test_get_price_history_unknown_ticker_returns_empty():
    assert provider().get_price_history("NOPE", date(2026, 1, 1), date(2026, 12, 31)) == []


def test_get_corporate_events_filters_by_ticker_and_date():
    events = provider().get_corporate_events("MFPC", date(2026, 6, 1), date(2026, 6, 30))
    assert len(events) == 1
    assert events[0].event_type == "DIVIDEND"


def test_get_macro_series_returns_observations_in_range():
    obs = provider().get_macro_series("BRENT_USD", date(2026, 6, 1), date(2026, 6, 3))
    assert [o.value for o in obs] == [82.10, 82.90, 83.40]


def test_get_news_filters_by_ticker():
    items = provider().get_news("COMI", date(2026, 6, 1), date(2026, 6, 30))
    assert len(items) == 1
    assert "CIB" in items[0].headline

    all_items = provider().get_news(None, date(2026, 6, 1), date(2026, 6, 30))
    assert len(all_items) == 3
