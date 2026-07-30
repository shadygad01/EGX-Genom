"""MarketMemory: the single sanctioned way to reconstruct historical state.

Backtesting-style experiments must call `MarketMemory.reconstruct(as_of)`
rather than touching `DataProvider` directly or reading "today" in any
form — that's what makes "backtesting must never use today's knowledge" an
enforceable seam instead of a convention someone can forget.
`DatasetSnapshot` already guarantees no data after `as_of` by construction;
this composes that guarantee with universe/sector state, the trading
calendar, and the day's canonical Events (registered through the Event
Platform, so they arrive deduplicated and conflict-resolved) into one
queryable historical reconstruction.
"""

from __future__ import annotations

from datetime import date

from agx_research.data.provider import DataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.events.adapters import derive_events_from_snapshot
from agx_research.events.service import EventPlatform
from agx_research.financials.provider import FinancialStatementProvider
from agx_research.market_memory.calendar import StaticEGXCalendar, TradingCalendar
from agx_research.market_memory.state import MarketState, TradingSession
from agx_research.universe.provider import UniverseProvider
from agx_research.universe.sector import SectorProvider


def is_egx_trading_day(as_of: date) -> bool:
    """Kept for backward compatibility; delegates to the calendar
    (weekends + fixed holidays + the placeholder movable-holiday table)."""
    return StaticEGXCalendar().is_trading_day(as_of)


class MarketMemory:
    def __init__(
        self,
        data_provider: DataProvider,
        universe_provider: UniverseProvider,
        sector_provider: SectorProvider,
        *,
        macro_series_ids: list[str] | None = None,
        lookback_days: int = 30,
        macro_lookback_days: int | None = None,
        macro_series_sources: dict[str, str] | None = None,
        pattern_lookback_days: int = 0,
        calendar: TradingCalendar | None = None,
        event_platform: EventPlatform | None = None,
        financials_provider: FinancialStatementProvider | None = None,
    ):
        self.data_provider = data_provider
        self.universe_provider = universe_provider
        self.sector_provider = sector_provider
        self.macro_series_ids = macro_series_ids or []
        self.lookback_days = lookback_days
        self.macro_lookback_days = macro_lookback_days
        self.macro_series_sources = macro_series_sources
        self.pattern_lookback_days = pattern_lookback_days
        self.calendar = calendar or StaticEGXCalendar()
        self.event_platform = event_platform or EventPlatform()
        self.financials_provider = financials_provider

    def reconstruct(self, as_of: date) -> MarketState:
        constituents = self.universe_provider.constituents(as_of)
        tickers = sorted(constituents)
        snapshot = build_snapshot(
            self.data_provider,
            tickers=tickers,
            macro_series_ids=self.macro_series_ids,
            as_of=as_of,
            lookback_days=self.lookback_days,
            macro_lookback_days=self.macro_lookback_days,
            macro_series_sources=self.macro_series_sources,
            pattern_lookback_days=self.pattern_lookback_days,
            financials_provider=self.financials_provider,
        )
        sectors = {
            ticker: sector
            for ticker in tickers
            for sector in [self.sector_provider.sector_of(ticker, as_of)]
            if sector is not None
        }
        trading_session = TradingSession(
            session_date=as_of,
            is_trading_day=self.calendar.is_trading_day(as_of),
            holiday_name=self.calendar.holiday_name(as_of),
        )
        events = self.event_platform.register_all(derive_events_from_snapshot(snapshot))
        return MarketState(
            as_of=as_of,
            dataset_snapshot=snapshot,
            constituents=constituents,
            sectors=sectors,
            trading_session=trading_session,
            events=events,
        )

    def tickers(self, as_of: date) -> list[str]:
        """Return the provider-backed ticker set for a point in time."""
        return sorted(self.universe_provider.constituents(as_of))
