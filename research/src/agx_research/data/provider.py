"""The DataProvider contract every market data source must implement.

Research agents and validation code should depend only on this interface,
never on a specific vendor's API shape. Today the only implementation is
`MockDataProvider` (local CSVs); a real EGX vendor integration is future
work and should be added as a new class implementing this same interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar


class DataProvider(ABC):
    """Abstract source of market, corporate action, macro, and news data."""

    @abstractmethod
    def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> list[PriceBar]:
        """Return daily OHLCV bars for `ticker` between `start` and `end`, inclusive."""

    @abstractmethod
    def get_corporate_events(
        self, ticker: str, start: date, end: date
    ) -> list[CorporateEvent]:
        """Return corporate events for `ticker` between `start` and `end`, inclusive."""

    @abstractmethod
    def get_macro_series(
        self, series_id: str, start: date, end: date
    ) -> list[MacroObservation]:
        """Return observations for a macro series between `start` and `end`, inclusive."""

    @abstractmethod
    def get_news(
        self, ticker: str | None, start: date, end: date
    ) -> list[NewsItem]:
        """Return news items between `start` and `end`, optionally filtered to `ticker`."""
