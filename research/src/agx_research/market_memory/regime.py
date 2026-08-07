"""Market Regime: a market-wide, evidence-derived trend/volatility
classification over a trailing window, computed the same way Market
Breadth is (adjusted, equal-weighted returns across the universe, no live
lookups, no calculation in the frontend -- `web/` only ever renders this
module's output).

Trend and volatility are reported as two independent axes rather than
fused into one combinatorial label (e.g. "bullish-quiet"), the same R5
discipline `decision_service.service` documents: a label derived directly
from a continuous number, never a lookup table over bucketed
combinations -- the Adversarial Review rejected exactly that shape
elsewhere in this codebase for the same combinatorial-growth reason.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from statistics import pstdev

from pydantic import BaseModel, Field

from agx_research.data.adjustments import adjusted_dated_returns
from agx_research.market_memory.state import MarketState

# Declared, uncalibrated starting thresholds -- same posture as every other
# declared-not-measured constant in this codebase (TD-6/17/20/33/44/45/46/
# 51/54): no real multi-year EGX regime history exists yet to calibrate
# against. `REGIME_LOOKBACK_DAYS` mirrors `TRAILING_VOLUME_WINDOW_DAYS`'s
# "a bounded, explainable recent window" reasoning (`production/
# collector_plan.py`), not a specific study.
REGIME_LOOKBACK_DAYS = 20
BULLISH_CUMULATIVE_RETURN_THRESHOLD = 0.03
BEARISH_CUMULATIVE_RETURN_THRESHOLD = -0.03
ELEVATED_VOLATILITY_THRESHOLD = 0.015
HIGH_VOLATILITY_THRESHOLD = 0.025


class MarketTrend(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class VolatilityLevel(str, Enum):
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"


class MarketRegimeReport(BaseModel):
    as_of: date
    lookback_days: int
    tickers_with_sufficient_data: int
    trading_days_observed: int
    cumulative_return_pct: float | None = None
    daily_volatility_pct: float | None = None
    trend: MarketTrend
    volatility: VolatilityLevel
    reasons: list[str] = Field(default_factory=list)


def compute_market_regime(
    state: MarketState, *, lookback_days: int = REGIME_LOOKBACK_DAYS
) -> MarketRegimeReport:
    """Derive a trend/volatility regime from `state` alone -- no live
    lookups, matching every other Market Memory read (`MarketState` is
    already the reconstructed, point-in-time-correct view for
    `state.as_of`).

    Trend: the equal-weighted universe's cumulative adjusted return over
    the trailing `lookback_days` trading days actually observed (never
    padded to a fixed count). Volatility: the population standard
    deviation of that same daily series. Both derive from
    `data.adjustments.adjusted_dated_returns()`, never a raw close-to-close
    calculation.

    The window is one shared set of trailing dates across the whole
    universe, not `lookback_days` computed independently per ticker: a
    ticker whose own history is shorter or gapped (a real, common case --
    different sources implemented on different dates, a real collection
    gap, a later IPO) has its own last-N dates that may not overlap at
    all with a fully-covered ticker's, and slicing before combining let
    the union of two non-overlapping 20-day slices silently report as a
    "40-day" trend -- neither a real 20-day nor a real 40-day reading,
    and not what `lookback_days` promises the reader.
    """
    tickers = sorted(state.constituents) or sorted(state.dataset_snapshot.price_history)

    per_ticker_returns: dict[str, dict[date, float]] = {}
    tickers_with_sufficient_data = 0
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
        events = state.dataset_snapshot.corporate_events.get(ticker, [])
        dated_returns = adjusted_dated_returns(bars, events)
        if not dated_returns:
            continue
        tickers_with_sufficient_data += 1
        per_ticker_returns[ticker] = dated_returns

    all_observed_dates = sorted({d for returns in per_ticker_returns.values() for d in returns})
    window_dates = set(all_observed_dates[-lookback_days:])

    returns_by_date: dict[date, list[float]] = {}
    for dated_returns in per_ticker_returns.values():
        for trade_date, ticker_return in dated_returns.items():
            if trade_date in window_dates:
                returns_by_date.setdefault(trade_date, []).append(ticker_return)

    trading_days = sorted(returns_by_date)
    daily_market_returns = [
        sum(returns_by_date[trade_date]) / len(returns_by_date[trade_date])
        for trade_date in trading_days
    ]

    if not daily_market_returns:
        return MarketRegimeReport(
            as_of=state.as_of,
            lookback_days=lookback_days,
            tickers_with_sufficient_data=tickers_with_sufficient_data,
            trading_days_observed=0,
            trend=MarketTrend.NEUTRAL,
            volatility=VolatilityLevel.LOW,
            reasons=["Insufficient price history to classify a regime."],
        )

    cumulative_return = 1.0
    for daily_return in daily_market_returns:
        cumulative_return *= 1 + daily_return
    cumulative_return -= 1.0

    volatility = pstdev(daily_market_returns) if len(daily_market_returns) > 1 else 0.0

    reasons: list[str] = []
    if cumulative_return >= BULLISH_CUMULATIVE_RETURN_THRESHOLD:
        trend = MarketTrend.BULLISH
        reasons.append(
            f"Equal-weighted universe return over the trailing {len(trading_days)} trading "
            f"day(s): {cumulative_return:+.2%} (bullish floor "
            f"{BULLISH_CUMULATIVE_RETURN_THRESHOLD:+.0%})."
        )
    elif cumulative_return <= BEARISH_CUMULATIVE_RETURN_THRESHOLD:
        trend = MarketTrend.BEARISH
        reasons.append(
            f"Equal-weighted universe return over the trailing {len(trading_days)} trading "
            f"day(s): {cumulative_return:+.2%} (bearish floor "
            f"{BEARISH_CUMULATIVE_RETURN_THRESHOLD:+.0%})."
        )
    else:
        trend = MarketTrend.NEUTRAL
        reasons.append(
            f"Equal-weighted universe return over the trailing {len(trading_days)} trading "
            f"day(s): {cumulative_return:+.2%}, inside the neutral band "
            f"({BEARISH_CUMULATIVE_RETURN_THRESHOLD:+.0%} to "
            f"{BULLISH_CUMULATIVE_RETURN_THRESHOLD:+.0%})."
        )

    if volatility >= HIGH_VOLATILITY_THRESHOLD:
        volatility_level = VolatilityLevel.HIGH
        reasons.append(
            f"Daily return volatility: {volatility:.2%} (high floor "
            f"{HIGH_VOLATILITY_THRESHOLD:.2%})."
        )
    elif volatility >= ELEVATED_VOLATILITY_THRESHOLD:
        volatility_level = VolatilityLevel.ELEVATED
        reasons.append(
            f"Daily return volatility: {volatility:.2%} (elevated floor "
            f"{ELEVATED_VOLATILITY_THRESHOLD:.2%})."
        )
    else:
        volatility_level = VolatilityLevel.LOW
        reasons.append(
            f"Daily return volatility: {volatility:.2%}, below the elevated floor "
            f"({ELEVATED_VOLATILITY_THRESHOLD:.2%})."
        )

    return MarketRegimeReport(
        as_of=state.as_of,
        lookback_days=lookback_days,
        tickers_with_sufficient_data=tickers_with_sufficient_data,
        trading_days_observed=len(trading_days),
        cumulative_return_pct=cumulative_return * 100,
        daily_volatility_pct=volatility * 100,
        trend=trend,
        volatility=volatility_level,
        reasons=reasons,
    )


__all__ = [
    "BEARISH_CUMULATIVE_RETURN_THRESHOLD",
    "BULLISH_CUMULATIVE_RETURN_THRESHOLD",
    "ELEVATED_VOLATILITY_THRESHOLD",
    "HIGH_VOLATILITY_THRESHOLD",
    "REGIME_LOOKBACK_DAYS",
    "MarketRegimeReport",
    "MarketTrend",
    "VolatilityLevel",
    "compute_market_regime",
]
