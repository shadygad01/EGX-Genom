"""Additional autonomous feature generators: momentum and volatility.

Same contract as `PairwiseCorrelationGenerator`: search the whole universe
mechanically, propose evidence-carrying candidates, never publish anything
— candidates feed the same hypothesis pipeline as everything else.
"""

from __future__ import annotations

import statistics
from datetime import datetime

from agx_research.data.adjustments import adjusted_returns_for_ticker
from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.features.basic import TRAILING_MEAN_RETURN, TRAILING_VOLATILITY
from agx_research.features.discovery import FeatureCandidate, FeatureGenerator
from agx_research.market_memory.state import MarketState


class MomentumGenerator(FeatureGenerator):
    """Proposes a momentum candidate when a ticker's mean adjusted return is
    large relative to its own noise (|t-like score| >= threshold)."""

    name = "momentum_generator"

    def __init__(self, score_threshold: float = 1.0):
        self.score_threshold = score_threshold

    def generate(self, market_state: MarketState) -> list[FeatureCandidate]:
        snapshot = market_state.dataset_snapshot
        candidates: list[FeatureCandidate] = []
        for ticker in sorted(snapshot.tickers):
            returns = adjusted_returns_for_ticker(snapshot, ticker)
            if len(returns) < 5:
                continue
            mean = statistics.fmean(returns)
            std = statistics.pstdev(returns)
            if std == 0:
                continue
            score = mean / (std / len(returns) ** 0.5)
            if abs(score) < self.score_threshold:
                continue
            candidates.append(
                FeatureCandidate(
                    id=new_id("feature_candidate"),
                    feature_id=f"{TRAILING_MEAN_RETURN.id}:{ticker}",
                    definition=f"Trailing mean adjusted daily return of {ticker}",
                    expression=f"mean(adjusted_returns({ticker}))",
                    dependencies=[f"price_history:{ticker}", f"corporate_events:{ticker}"],
                    creator=self.name,
                    discovery_date=market_state.as_of,
                    evidence=[f"mean_return={mean:.6f}", f"t_like_score={score:.3f}"],
                    importance=abs(score),
                    provenance=Provenance(
                        produced_by=self.name,
                        produced_at=datetime.now(),
                        inputs=[
                            ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id),
                            ProvenanceRef(
                                kind="feature",
                                ref_id=TRAILING_MEAN_RETURN.id,
                                ref_version=TRAILING_MEAN_RETURN.version,
                            ),
                        ],
                    ),
                )
            )
        return candidates


class VolatilityGenerator(FeatureGenerator):
    """Proposes a volatility candidate for tickers whose realized volatility is
    an outlier versus the universe median (ratio >= threshold either way)."""

    name = "volatility_generator"

    def __init__(self, ratio_threshold: float = 1.5):
        self.ratio_threshold = ratio_threshold

    def generate(self, market_state: MarketState) -> list[FeatureCandidate]:
        snapshot = market_state.dataset_snapshot
        vols: dict[str, float] = {}
        for ticker in sorted(snapshot.tickers):
            returns = adjusted_returns_for_ticker(snapshot, ticker)
            if len(returns) >= 5:
                vols[ticker] = statistics.pstdev(returns)
        if len(vols) < 2:
            return []
        median_vol = statistics.median(vols.values())
        if median_vol == 0:
            return []

        candidates: list[FeatureCandidate] = []
        for ticker, vol in vols.items():
            ratio = vol / median_vol
            if not (ratio >= self.ratio_threshold or ratio <= 1 / self.ratio_threshold):
                continue
            candidates.append(
                FeatureCandidate(
                    id=new_id("feature_candidate"),
                    feature_id=f"{TRAILING_VOLATILITY.id}:{ticker}",
                    definition=f"Trailing realized volatility of {ticker}",
                    expression=f"pstdev(adjusted_returns({ticker}))",
                    dependencies=[f"price_history:{ticker}", f"corporate_events:{ticker}"],
                    creator=self.name,
                    discovery_date=market_state.as_of,
                    evidence=[f"volatility={vol:.6f}", f"vs_median_ratio={ratio:.3f}"],
                    importance=abs(ratio - 1.0),
                    provenance=Provenance(
                        produced_by=self.name,
                        produced_at=datetime.now(),
                        inputs=[
                            ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id),
                            ProvenanceRef(
                                kind="feature",
                                ref_id=TRAILING_VOLATILITY.id,
                                ref_version=TRAILING_VOLATILITY.version,
                            ),
                        ],
                    ),
                )
            )
        return candidates
