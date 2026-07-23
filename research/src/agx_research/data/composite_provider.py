"""Combining multiple data sources: the seam for real multi-vendor composition.

Which vendor(s) to license is a business decision (cost, coverage, contract
terms) outside this engineering scope — see `docs/PHASE_STATUS.md`. This is
the interface that decision plugs into: `FallbackDataProvider` tries each
configured `DataProvider` in priority order, falling back to the next if
the primary returns nothing for a given query. Conflict resolution between
providers that both return data (e.g. disagreeing on the same bar) is
explicitly out of scope until there's a second real provider to reconcile
against — resolving it speculatively now would be guessing at a policy no
real data has yet motivated.
"""

from __future__ import annotations

from datetime import date

from agx_research.data.provider import DataProvider
from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar


class FallbackDataProvider(DataProvider):
    def __init__(self, providers: list[DataProvider]):
        if not providers:
            raise ValueError("FallbackDataProvider requires at least one provider")
        self.providers = providers

    def get_price_history(self, ticker: str, start: date, end: date) -> list[PriceBar]:
        for provider in self.providers:
            result = provider.get_price_history(ticker, start, end)
            if result:
                return result
        return []

    def get_corporate_events(self, ticker: str, start: date, end: date) -> list[CorporateEvent]:
        for provider in self.providers:
            result = provider.get_corporate_events(ticker, start, end)
            if result:
                return result
        return []

    def get_macro_series(self, series_id: str, start: date, end: date) -> list[MacroObservation]:
        for provider in self.providers:
            result = provider.get_macro_series(series_id, start, end)
            if result:
                return result
        return []

    def get_news(self, ticker: str | None, start: date, end: date) -> list[NewsItem]:
        for provider in self.providers:
            result = provider.get_news(ticker, start, end)
            if result:
                return result
        return []
