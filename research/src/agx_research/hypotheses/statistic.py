"""The statistic a hypothesis is judged on, dispatched by its asset arity.

Shared by the Experiment Factory and the concrete validators (backtester,
stress tester) so "what number does this hypothesis claim is non-random"
is defined in exactly one place:

- two affected assets  -> Pearson correlation of their adjusted daily
  returns (a co-movement claim);
- one affected asset   -> mean adjusted daily return (a drift/momentum
  claim).

Anything more exotic (a hypothesis about three assets, or about a
non-return quantity) raises rather than guessing — a new arity needs an
explicit statistic definition here, not silent fallback behavior.
"""

from __future__ import annotations

import statistics as _statistics

from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.features.correlation import pearson_correlation
from agx_research.hypotheses.hypothesis import Hypothesis


def series_for_hypothesis(hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> list[list[float]]:
    """Adjusted-return series for each affected asset, aligned to equal length."""
    if not 1 <= len(hypothesis.affected_assets) <= 2:
        raise ValueError(
            f"{hypothesis.id}: no statistic is defined for {len(hypothesis.affected_assets)} "
            "affected assets; add one to hypotheses/statistic.py explicitly"
        )
    all_series = [
        adjusted_returns_for_ticker(snapshot, ticker) for ticker in hypothesis.affected_assets
    ]
    n = min(len(series) for series in all_series)
    return [series[-n:] for series in all_series]


def hypothesis_statistic(series: list[list[float]]) -> float | None:
    """The claim's test statistic over the given (already aligned) series."""
    if len(series) == 2:
        return pearson_correlation(series[0], series[1])
    if len(series) == 1:
        return _statistics.fmean(series[0]) if series[0] else None
    raise ValueError(f"No statistic defined for {len(series)} series")


def slice_series(series: list[list[float]], start: int, end: int) -> list[list[float]]:
    return [s[start:end] for s in series]
