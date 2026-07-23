"""Corporate-action price adjustment: splits and dividends.

Every return calculation in this codebase (correlation, cross-validation,
bootstrap, walk-forward, ...) is computed from `PriceBar.close`. A stock
split or cash dividend causes a purely mechanical price change on its
ex-date that has nothing to do with the return investors actually earned —
left unadjusted, it corrupts every daily-return calculation spanning the
event date. This is a well-known, expensive-to-retrofit bug class in quant
systems if caught late; fixing it now, before real corporate-action data
exists, costs nothing.

Uses the standard backward-adjustment convention used by most vendor
"adjusted close" series: walk from the most recent corporate action
backward, applying a cumulative multiplicative factor to every bar strictly
before each action's ex-date. `CorporateEvent.details` carries the
structured payload (`{"split_ratio": 2.0}` or `{"dividend_amount": 3.5}`);
event types without one of those keys (e.g. EARNINGS) are ignored here.

This module intentionally returns a derived mapping rather than mutating
`PriceBar` — adjusted prices are an analytical derivative of raw observed
data, not raw data themselves, the same distinction Epoch II's Feature
Discovery Engine draws between raw fields and computed features.
"""

from __future__ import annotations

from datetime import date

from agx_research.data.schemas import CorporateEvent, PriceBar
from agx_research.data.snapshot import DatasetSnapshot


def _split_factor(event: CorporateEvent) -> float | None:
    ratio = event.details.get("split_ratio")
    if ratio is None or float(ratio) <= 0:
        return None
    return 1.0 / float(ratio)


def _dividend_factor(event: CorporateEvent, reference_close: float) -> float | None:
    amount = event.details.get("dividend_amount")
    if amount is None or reference_close <= 0:
        return None
    return max(0.0, (reference_close - float(amount)) / reference_close)


def compute_adjusted_closes(bars: list[PriceBar], events: list[CorporateEvent]) -> dict[date, float]:
    """Return {trade_date: adjusted_close} for every bar in `bars`.

    Splits and dividends are applied using the standard backward-adjustment
    convention: events are processed newest-first, and each one's factor is
    computed from the price level *as already adjusted for any newer
    events* (the correct sequential-compounding order), then applied to
    every bar strictly before that event's date.
    """
    sorted_bars = sorted(bars, key=lambda b: b.trade_date)
    adjusted: dict[date, float] = {bar.trade_date: bar.close for bar in sorted_bars}

    adjustable_events = [
        e for e in events if "split_ratio" in e.details or "dividend_amount" in e.details
    ]
    for event in sorted(adjustable_events, key=lambda e: e.event_date, reverse=True):
        factor: float | None
        if "split_ratio" in event.details:
            factor = _split_factor(event)
        else:
            # The reference price is the last *cum*-dividend close -- strictly
            # before the ex-date. Using the ex-date's own close (already
            # reflecting the mechanical drop) would understate the true factor.
            prior_dates = [d for d in adjusted if d < event.event_date]
            if not prior_dates:
                continue
            factor = _dividend_factor(event, adjusted[max(prior_dates)])

        if factor is None:
            continue
        for trade_date in adjusted:
            if trade_date < event.event_date:
                adjusted[trade_date] *= factor

    return adjusted


def adjusted_daily_returns(bars: list[PriceBar], events: list[CorporateEvent]) -> list[float]:
    """Daily returns computed from split/dividend-adjusted closes, in date order."""
    sorted_dates = sorted(b.trade_date for b in bars)
    adjusted = compute_adjusted_closes(bars, events)
    closes = [adjusted[d] for d in sorted_dates]
    return [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1] != 0
    ]


def adjusted_returns_for_ticker(snapshot: DatasetSnapshot, ticker: str) -> list[float]:
    """Convenience: pulls both `price_history` and `corporate_events` for `ticker`
    straight out of a `DatasetSnapshot`. This is what `features.correlation` and
    `hypotheses.experiment_factory` use instead of computing raw, unadjusted
    returns from `PriceBar.close` directly.
    """
    bars = snapshot.price_history.get(ticker, [])
    events = snapshot.corporate_events.get(ticker, [])
    return adjusted_daily_returns(bars, events)
