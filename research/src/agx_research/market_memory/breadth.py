"""Market Breadth: a market-wide, evidence-derived rollup of how many
constituents advanced/declined and how many traded on above-average volume,
on the date a `MarketState` reconstructs.

CLAUDE.md's return-adjustment rule ("Return calculations always go through
`data.adjustments.adjusted_returns_for_ticker()`, never raw
`[bar.close for bar in bars]`") applies here exactly as it does to every
agent/experiment -- this module is the one place breadth math happens; the
frontend only ever renders its output (`web/`'s own documented constraint:
no calculation happens in `web/`).
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from agx_research.data.adjustments import adjusted_dated_returns
from agx_research.market_memory.state import MarketState

# A declared, uncalibrated starting window -- same posture as every other
# declared-not-measured constant in this codebase (TD-6/17/20/33/44/45/46/51):
# no real EGX volume-distribution study backs "20" specifically, it is only
# a conventional trading-month length chosen to be defensible, not derived.
TRAILING_VOLUME_WINDOW_DAYS = 20


class MarketBreadthReport(BaseModel):
    as_of: date
    universe_count: int
    tickers_with_price_data: int
    advancers: int
    decliners: int
    unchanged: int
    # advancers / decliners; `None` when there are zero decliners to divide
    # by (undefined, not fabricated as an "infinite" ratio).
    advance_decline_ratio: float | None = None
    average_daily_return_pct: float | None = None
    tickers_with_volume_data: int
    tickers_above_average_volume: int
    tickers_below_average_volume: int


def compute_market_breadth(state: MarketState) -> MarketBreadthReport:
    """Derive breadth/liquidity stats from `state` alone -- no live lookups,
    matching every other Market Memory read (`MarketState` is already the
    reconstructed, point-in-time-correct view for `state.as_of`).
    """
    tickers = sorted(state.constituents) or sorted(state.dataset_snapshot.price_history)

    advancers = decliners = unchanged = 0
    tickers_with_price_data = 0
    returns_today: list[float] = []
    above_average_volume = below_average_volume = 0

    for ticker in tickers:
        bars = sorted(
            (
                bar
                for bar in state.dataset_snapshot.price_history.get(ticker, [])
                if bar.trade_date <= state.as_of
            ),
            key=lambda bar: bar.trade_date,
        )
        if len(bars) < 2:
            continue
        tickers_with_price_data += 1

        events = state.dataset_snapshot.corporate_events.get(ticker, [])
        dated_returns = adjusted_dated_returns(bars, events)
        if dated_returns:
            latest_return_date = max(dated_returns)
            today_return = dated_returns[latest_return_date]
            returns_today.append(today_return)
            if today_return > 0:
                advancers += 1
            elif today_return < 0:
                decliners += 1
            else:
                unchanged += 1

        latest_bar = bars[-1]
        trailing = bars[-(TRAILING_VOLUME_WINDOW_DAYS + 1) : -1]
        if trailing:
            average_volume = sum(bar.volume for bar in trailing) / len(trailing)
            if average_volume > 0:
                if latest_bar.volume > average_volume:
                    above_average_volume += 1
                else:
                    below_average_volume += 1

    return MarketBreadthReport(
        as_of=state.as_of,
        universe_count=len(tickers),
        tickers_with_price_data=tickers_with_price_data,
        advancers=advancers,
        decliners=decliners,
        unchanged=unchanged,
        advance_decline_ratio=(advancers / decliners) if decliners > 0 else None,
        average_daily_return_pct=(
            (sum(returns_today) / len(returns_today)) * 100 if returns_today else None
        ),
        tickers_with_volume_data=above_average_volume + below_average_volume,
        tickers_above_average_volume=above_average_volume,
        tickers_below_average_volume=below_average_volume,
    )


__all__ = ["MarketBreadthReport", "TRAILING_VOLUME_WINDOW_DAYS", "compute_market_breadth"]
