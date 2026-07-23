"""Single-asset feature definitions: trailing mean return and realized volatility.

Computed from split/dividend-adjusted returns like everything else. These
are the second and third registered features (after pairwise correlation),
which is what makes the FeatureGenerator/Experiment abstractions prove out
beyond one feature type.
"""

from __future__ import annotations

import statistics

from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.features.definition import FeatureDefinition

TRAILING_MEAN_RETURN = FeatureDefinition(
    id="trailing_mean_return",
    version=1,
    name="Trailing mean adjusted daily return",
    description="Mean of a ticker's split/dividend-adjusted daily returns over the snapshot window.",
    inputs=["price_history", "corporate_events"],
)

TRAILING_VOLATILITY = FeatureDefinition(
    id="trailing_volatility",
    version=1,
    name="Trailing realized volatility",
    description=(
        "Population standard deviation of a ticker's adjusted daily returns "
        "over the snapshot window."
    ),
    inputs=["price_history", "corporate_events"],
)


def compute_trailing_mean_return(snapshot: DatasetSnapshot, ticker: str) -> float | None:
    returns = adjusted_returns_for_ticker(snapshot, ticker)
    return statistics.fmean(returns) if len(returns) >= 3 else None


def compute_trailing_volatility(snapshot: DatasetSnapshot, ticker: str) -> float | None:
    returns = adjusted_returns_for_ticker(snapshot, ticker)
    return statistics.pstdev(returns) if len(returns) >= 3 else None
