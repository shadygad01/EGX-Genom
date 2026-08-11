"""Baseline models: before trusting any discovered pattern, the mission
requires it to beat these simple, transparent baselines out-of-sample
after realistic costs (section 16) — never assumed alpha exists just
because a candidate is statistically "significant" in isolation.

Every baseline here shares `targets.forward_return_series` with the
Target Factory itself, so a baseline and a candidate are always compared
on identically-defined forward returns, never a subtly different
calculation that could make the comparison meaningless.
"""

from __future__ import annotations

import statistics
from datetime import date

from pydantic import BaseModel

from agx_research.patterns.evaluation import OutcomeDistribution
from agx_research.patterns.panel import ResearchPanel
from agx_research.patterns.targets import forward_return_series

DEFAULT_MOMENTUM_LOOKBACK_DAYS = 20
DEFAULT_MEAN_REVERSION_LOOKBACK_DAYS = 20


class BaselineResult(BaseModel):
    name: str
    ticker: str | None = None
    horizon_days: int
    sample_size: int
    mean_outcome: float
    hit_rate: float
    stdev: float


def _from_outcomes(name: str, ticker: str | None, horizon_days: int, outcomes: list[float]) -> BaselineResult | None:
    if len(outcomes) < 2:
        return None
    return BaselineResult(
        name=name,
        ticker=ticker,
        horizon_days=horizon_days,
        sample_size=len(outcomes),
        mean_outcome=statistics.fmean(outcomes),
        hit_rate=sum(1 for o in outcomes if o > 0) / len(outcomes),
        stdev=statistics.pstdev(outcomes),
    )


def unconditional_market_baseline(panel: ResearchPanel, horizon_days: int) -> BaselineResult | None:
    outcomes: list[float] = []
    for series in panel.series.values():
        outcomes.extend(v for v in forward_return_series(series.adjusted_close, horizon_days) if v is not None)
    return _from_outcomes("unconditional_market", None, horizon_days, outcomes)


def buy_and_hold_baseline(panel: ResearchPanel, ticker: str, horizon_days: int) -> BaselineResult | None:
    series = panel.series.get(ticker)
    if series is None:
        return None
    outcomes = [v for v in forward_return_series(series.adjusted_close, horizon_days) if v is not None]
    return _from_outcomes("buy_and_hold", ticker, horizon_days, outcomes)


def _trailing_return(closes: list[float], lookback_days: int) -> list[float | None]:
    return [
        (closes[i] - closes[i - lookback_days]) / closes[i - lookback_days]
        if i >= lookback_days and closes[i - lookback_days] != 0
        else None
        for i in range(len(closes))
    ]


def momentum_baseline(
    panel: ResearchPanel, ticker: str, horizon_days: int, *, lookback_days: int = DEFAULT_MOMENTUM_LOOKBACK_DAYS
) -> BaselineResult | None:
    series = panel.series.get(ticker)
    if series is None:
        return None
    closes = series.adjusted_close
    trailing = _trailing_return(closes, lookback_days)
    forward = forward_return_series(closes, horizon_days)
    outcomes = [f for t, f in zip(trailing, forward) if t is not None and t > 0 and f is not None]
    return _from_outcomes(f"momentum_{lookback_days}d", ticker, horizon_days, outcomes)


def mean_reversion_baseline(
    panel: ResearchPanel, ticker: str, horizon_days: int, *, lookback_days: int = DEFAULT_MEAN_REVERSION_LOOKBACK_DAYS
) -> BaselineResult | None:
    series = panel.series.get(ticker)
    if series is None:
        return None
    closes = series.adjusted_close
    trailing = _trailing_return(closes, lookback_days)
    forward = forward_return_series(closes, horizon_days)
    outcomes = [f for t, f in zip(trailing, forward) if t is not None and t < 0 and f is not None]
    return _from_outcomes(f"mean_reversion_{lookback_days}d", ticker, horizon_days, outcomes)


def sector_relative_baseline(panel: ResearchPanel, ticker: str, horizon_days: int) -> BaselineResult | None:
    series = panel.series.get(ticker)
    sector = panel.sectors.get(ticker)
    if series is None or not sector:
        return None
    own_forward = dict(zip(series.dates, forward_return_series(series.adjusted_close, horizon_days)))
    sector_by_date: dict[date, list[float]] = {}
    for peer_ticker, peer_series in panel.series.items():
        if panel.sectors.get(peer_ticker) != sector:
            continue
        for d, v in zip(peer_series.dates, forward_return_series(peer_series.adjusted_close, horizon_days)):
            if v is not None:
                sector_by_date.setdefault(d, []).append(v)
    outcomes: list[float] = []
    for d, own_value in own_forward.items():
        peers = sector_by_date.get(d)
        if own_value is None or not peers:
            continue
        outcomes.append(own_value - statistics.fmean(peers))
    return _from_outcomes("sector_relative", ticker, horizon_days, outcomes)


def fundamental_baseline(panel: ResearchPanel, ticker: str, horizon_days: int) -> BaselineResult | None:
    """Only ever runs "where data permits" (mission section 16) — returns
    None, never a fabricated result, when no financial statement line
    items are collected for `ticker` (currently every ticker; see
    `docs/PATTERN_DISCOVERY_DATA_AUDIT.md`)."""
    items = panel.financial_statements.get(ticker, [])
    revenue_items = sorted(
        (i for i in items if i.line_item == "revenue"), key=lambda i: i.period_end_date
    )
    if len(revenue_items) < 5:
        return None
    series = panel.series.get(ticker)
    if series is None:
        return None
    closes = series.adjusted_close
    forward = dict(zip(series.dates, forward_return_series(closes, horizon_days)))
    outcomes: list[float] = []
    for i in range(4, len(revenue_items)):
        prior = revenue_items[i - 4].value
        current = revenue_items[i].value
        if prior == 0:
            continue
        growth = (current - prior) / abs(prior)
        anchor = revenue_items[i].period_end_date
        candidate_dates = [d for d in forward if d >= anchor]
        if not candidate_dates or growth <= 0:
            continue
        first = min(candidate_dates)
        if forward.get(first) is not None:
            outcomes.append(forward[first])
    return _from_outcomes("revenue_growth_positive", ticker, horizon_days, outcomes)


def beats_baseline(distribution: OutcomeDistribution, baseline: BaselineResult, *, transaction_cost_bps: float = 20.0) -> bool:
    """Whether a candidate/pattern's own outcome distribution clears its
    baseline's mean, net of realistic transaction costs — the mission's
    explicit "must beat appropriate baselines out-of-sample after realistic
    costs; otherwise reject it" bar."""
    net_expectancy = distribution.expectancy - (transaction_cost_bps / 10_000)
    return net_expectancy > baseline.mean_outcome


__all__ = [
    "DEFAULT_MEAN_REVERSION_LOOKBACK_DAYS",
    "DEFAULT_MOMENTUM_LOOKBACK_DAYS",
    "BaselineResult",
    "beats_baseline",
    "buy_and_hold_baseline",
    "fundamental_baseline",
    "mean_reversion_baseline",
    "momentum_baseline",
    "sector_relative_baseline",
    "unconditional_market_baseline",
]
