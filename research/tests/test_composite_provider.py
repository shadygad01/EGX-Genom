from datetime import date

import pytest

from agx_research.data.composite_provider import FallbackDataProvider
from agx_research.data.provider import DataProvider
from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar


class _StubProvider(DataProvider):
    def __init__(self, price_bars=None, corporate_events=None, macro=None, news=None):
        self._price_bars = price_bars or []
        self._corporate_events = corporate_events or []
        self._macro = macro or []
        self._news = news or []

    def get_price_history(self, ticker, start, end):
        return self._price_bars

    def get_corporate_events(self, ticker, start, end):
        return self._corporate_events

    def get_macro_series(self, series_id, start, end):
        return self._macro

    def get_news(self, ticker, start, end):
        return self._news


def _bar():
    return PriceBar(
        ticker="COMI", trade_date=date(2026, 6, 1), open=1, high=1, low=1, close=1, volume=1
    )


def test_requires_at_least_one_provider():
    with pytest.raises(ValueError):
        FallbackDataProvider([])


def test_falls_back_to_second_provider_when_primary_returns_nothing():
    primary = _StubProvider()  # returns nothing for everything
    secondary = _StubProvider(price_bars=[_bar()])
    provider = FallbackDataProvider([primary, secondary])

    result = provider.get_price_history("COMI", date(2026, 6, 1), date(2026, 6, 1))
    assert result == [_bar()]


def test_uses_primary_when_it_has_data():
    primary_bar = PriceBar(
        ticker="COMI", trade_date=date(2026, 6, 2), open=2, high=2, low=2, close=2, volume=2
    )
    primary = _StubProvider(price_bars=[primary_bar])
    secondary = _StubProvider(price_bars=[_bar()])
    provider = FallbackDataProvider([primary, secondary])

    result = provider.get_price_history("COMI", date(2026, 6, 1), date(2026, 6, 1))
    assert result == [primary_bar]


def test_falls_back_across_all_four_data_kinds():
    empty = _StubProvider()
    full = _StubProvider(
        price_bars=[_bar()],
        corporate_events=[
            CorporateEvent(ticker="COMI", event_date=date(2026, 6, 1), event_type="X", description="x")
        ],
        macro=[MacroObservation(series_id="X", observation_date=date(2026, 6, 1), value=1.0)],
        news=[NewsItem(published_at=date(2026, 6, 1), source="s", headline="h")],
    )
    provider = FallbackDataProvider([empty, full])

    assert len(provider.get_price_history("COMI", date(2026, 6, 1), date(2026, 6, 1))) == 1
    assert len(provider.get_corporate_events("COMI", date(2026, 6, 1), date(2026, 6, 1))) == 1
    assert len(provider.get_macro_series("X", date(2026, 6, 1), date(2026, 6, 1))) == 1
    assert len(provider.get_news(None, date(2026, 6, 1), date(2026, 6, 1))) == 1


def test_returns_empty_when_no_provider_has_data():
    provider = FallbackDataProvider([_StubProvider(), _StubProvider()])
    assert provider.get_price_history("COMI", date(2026, 6, 1), date(2026, 6, 1)) == []
