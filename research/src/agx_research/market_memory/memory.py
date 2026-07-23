"""MarketMemory: the single sanctioned way to reconstruct historical state.

Backtesting-style experiments (Phase 5's `ExperimentFactory` outputs) must
call `MarketMemory.reconstruct(as_of)` rather than touching `DataProvider`
directly or reading "today" in any form — that's what makes "backtesting
must never use today's knowledge" an enforceable seam instead of a
convention someone can forget. `DatasetSnapshot` already guarantees no data
after `as_of` (Epoch I); this composes that guarantee with universe and
sector state into one queryable historical reconstruction.
"""

from __future__ import annotations

from datetime import date

from agx_research.data.provider import DataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.market_memory.state import MarketState, TradingSession
from agx_research.universe.provider import UniverseProvider
from agx_research.universe.sector import SectorProvider

# EGX's trading week is Sunday-Thursday; Friday/Saturday are the weekend.
_EGX_WEEKEND_WEEKDAYS = {4, 5}  # date.weekday(): Friday=4, Saturday=5


def is_egx_trading_day(as_of: date) -> bool:
    """A simple, real trading-calendar rule. Does not account for public
    holidays — see docs/EPOCH_II_DESIGN.md for that as a named gap.
    """
    return as_of.weekday() not in _EGX_WEEKEND_WEEKDAYS


class MarketMemory:
    def __init__(
        self,
        data_provider: DataProvider,
        universe_provider: UniverseProvider,
        sector_provider: SectorProvider,
        *,
        tickers: list[str],
        macro_series_ids: list[str] | None = None,
        lookback_days: int = 30,
    ):
        self.data_provider = data_provider
        self.universe_provider = universe_provider
        self.sector_provider = sector_provider
        self.tickers = tickers
        self.macro_series_ids = macro_series_ids or []
        self.lookback_days = lookback_days

    def reconstruct(self, as_of: date) -> MarketState:
        snapshot = build_snapshot(
            self.data_provider,
            tickers=self.tickers,
            macro_series_ids=self.macro_series_ids,
            as_of=as_of,
            lookback_days=self.lookback_days,
        )
        constituents = self.universe_provider.constituents(as_of)
        sectors = {
            ticker: sector
            for ticker in self.tickers
            for sector in [self.sector_provider.sector_of(ticker, as_of)]
            if sector is not None
        }
        trading_session = TradingSession(
            session_date=as_of,
            is_trading_day=is_egx_trading_day(as_of),
        )
        return MarketState(
            as_of=as_of,
            dataset_snapshot=snapshot,
            constituents=constituents,
            sectors=sectors,
            trading_session=trading_session,
        )
