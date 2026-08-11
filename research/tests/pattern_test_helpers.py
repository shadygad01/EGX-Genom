"""Shared synthetic-data helpers for `test_pattern_*.py`.

No `test_` prefix -- pytest's default `testpaths=["tests"]` collection
only picks up `test_*.py`, so this module is never collected as a test
file itself, matching how `research/tests/fixtures/` already holds
non-test fixture data.

`make_deterministic_ticker_series` builds a fully deterministic (seeded),
noise-small price path with a genuine, real periodic momentum
relationship baked in by construction: alternating up/down blocks mean
"yesterday's return was positive" is a real, reliable predictor of
"today's return is also positive" within a block. This is what
`test_pattern_engine.py` uses as a positive control — proof the engine
can validate a real pattern, not just always honestly return zero.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from agx_research.patterns.panel import ResearchPanel, TickerSeries


def trading_dates(start: date, n: int) -> list[date]:
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:  # Mon-Fri; good enough for a synthetic calendar
            dates.append(current)
        current += timedelta(days=1)
    return dates


def make_deterministic_ticker_series(
    ticker: str,
    *,
    n_days: int = 400,
    seed: int = 7,
    block_length: int = 20,
    daily_drift: float = 0.003,
    noise_stdev: float = 0.0002,
    start_date: date = date(2020, 1, 2),
    sector: str | None = None,
) -> TickerSeries:
    rng = random.Random(seed)
    dates = trading_dates(start_date, n_days)
    closes = [100.0]
    for i in range(1, n_days):
        block = (i // block_length) % 2
        drift = daily_drift if block == 0 else -daily_drift
        daily_return = drift + rng.gauss(0, noise_stdev)
        closes.append(closes[-1] * (1 + daily_return))

    opens = [closes[0], *closes[:-1]]
    highs = [c * 1.002 for c in closes]
    lows = [c * 0.998 for c in closes]
    volumes = [100_000 + rng.randint(-5000, 5000) for _ in range(n_days)]

    return TickerSeries(
        ticker=ticker,
        dates=dates,
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        adjusted_close=list(closes),
        volume=volumes,
        sector=sector,
    )


def make_flat_ticker_series(
    ticker: str, *, n_days: int = 15, start_date: date = date(2020, 1, 2), price: float = 100.0
) -> TickerSeries:
    """A degenerate, zero-variance series -- useful for proving a stage
    honestly refuses (returns None / empty) rather than fabricating a
    statistic from no real variation."""
    dates = trading_dates(start_date, n_days)
    closes = [price] * n_days
    return TickerSeries(
        ticker=ticker,
        dates=dates,
        open=list(closes),
        high=list(closes),
        low=list(closes),
        close=list(closes),
        adjusted_close=list(closes),
        volume=[100_000] * n_days,
        sector=None,
    )


def make_panel(*, series: dict[str, TickerSeries], sectors: dict[str, str] | None = None) -> ResearchPanel:
    as_of = max(max(s.dates) for s in series.values())
    return ResearchPanel(
        as_of=as_of,
        tickers=sorted(series),
        series=series,
        sectors=sectors or {t: s.sector for t, s in series.items() if s.sector},
    )
