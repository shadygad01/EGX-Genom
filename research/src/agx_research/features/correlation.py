"""The pairwise return-correlation feature.

Pulled out of `agents/market_structure.py` so the correlation computation
is a versioned, named, reusable `FeatureDefinition` rather than inline
arithmetic duplicated across whichever agents happen to need it.
"""

from __future__ import annotations

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.features.definition import FeatureDefinition
from agx_research.features.registry import FeatureRegistry

PAIRWISE_RETURN_CORRELATION = FeatureDefinition(
    id="pairwise_return_correlation",
    version=1,
    name="Pairwise daily-return correlation",
    description=(
        "Pearson correlation of two tickers' daily returns over a "
        "snapshot's lookback window."
    ),
    inputs=["price_history"],
)


def daily_returns(closes: list[float]) -> list[float]:
    """Public: reused by `hypotheses.experiment_factory`'s cross-validation,
    bootstrap, walk-forward, and out-of-sample experiments.
    """
    return [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]


def pearson_correlation(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[-n:], b[-n:]
    mean_a, mean_b = sum(a) / n, sum(b) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    if var_a == 0 or var_b == 0:
        return None
    return cov / (var_a**0.5 * var_b**0.5)


def compute_pairwise_return_correlation(
    snapshot: DatasetSnapshot, ticker_a: str, ticker_b: str
) -> float | None:
    bars_a = snapshot.price_history.get(ticker_a, [])
    bars_b = snapshot.price_history.get(ticker_b, [])
    if len(bars_a) < 3 or len(bars_b) < 3:
        return None
    returns_a = daily_returns([b.close for b in bars_a])
    returns_b = daily_returns([b.close for b in bars_b])
    return pearson_correlation(returns_a, returns_b)


def default_feature_registry() -> FeatureRegistry:
    registry = FeatureRegistry()
    registry.register(PAIRWISE_RETURN_CORRELATION)
    return registry
