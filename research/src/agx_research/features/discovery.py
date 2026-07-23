"""The autonomous Feature Discovery Engine.

Epoch I's `FeatureRegistry` (`features/registry.py`) is a schema registry
for features a human already named. This turns it autonomous: a
`FeatureGenerator` searches a `MarketState` for candidates on its own —
`PairwiseCorrelationGenerator` enumerates every ticker pair in the universe
and proposes a `FeatureCandidate` wherever the existing
`pairwise_return_correlation` feature clears a threshold, instead of a
human hardcoding one pair.
"""

from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.features.correlation import (
    PAIRWISE_RETURN_CORRELATION,
    compute_pairwise_return_correlation,
)
from agx_research.market_memory.state import MarketState
from agx_research.storage.repository import JsonFileRepository


class FeatureCandidateStatus(str, Enum):
    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    PROMOTED = "promoted"
    RETIRED = "retired"


class FeatureCandidate(BaseModel):
    id: str
    version: int = 1
    feature_id: str
    definition: str
    expression: str
    dependencies: list[str] = Field(default_factory=list)
    creator: str
    discovery_date: date
    evidence: list[str] = Field(default_factory=list)
    importance: float | None = None
    status: FeatureCandidateStatus = FeatureCandidateStatus.PROPOSED
    retired_at: date | None = None
    retirement_reason: str | None = None
    provenance: Provenance


class FeatureCandidateRepository(JsonFileRepository[FeatureCandidate]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(FeatureCandidate, persist_path)


class FeatureGenerator(ABC):
    """One strategy for proposing candidate features from market state."""

    name: str

    @abstractmethod
    def generate(self, market_state: MarketState) -> list[FeatureCandidate]:
        """Propose zero or more candidates from `market_state`."""


class PairwiseCorrelationGenerator(FeatureGenerator):
    """Searches every ticker pair in the snapshot for correlation candidates."""

    name = "pairwise_correlation_generator"

    def __init__(self, correlation_threshold: float = 0.5):
        self.correlation_threshold = correlation_threshold

    def generate(self, market_state: MarketState) -> list[FeatureCandidate]:
        snapshot = market_state.dataset_snapshot
        tickers = sorted(t for t in snapshot.tickers if snapshot.price_history.get(t))
        candidates: list[FeatureCandidate] = []

        for ticker_a, ticker_b in itertools.combinations(tickers, 2):
            correlation = compute_pairwise_return_correlation(snapshot, ticker_a, ticker_b)
            if correlation is None or abs(correlation) < self.correlation_threshold:
                continue
            candidates.append(
                FeatureCandidate(
                    id=new_id("feature_candidate"),
                    feature_id=f"{PAIRWISE_RETURN_CORRELATION.id}:{ticker_a}:{ticker_b}",
                    definition=f"Pearson correlation of {ticker_a} and {ticker_b} daily returns",
                    expression=f"corr(returns({ticker_a}), returns({ticker_b}))",
                    dependencies=[f"price_history:{ticker_a}", f"price_history:{ticker_b}"],
                    creator=self.name,
                    discovery_date=market_state.as_of,
                    evidence=[f"pearson_correlation={correlation:.4f}"],
                    importance=abs(correlation),
                    provenance=Provenance(
                        produced_by=self.name,
                        produced_at=datetime.now(),
                        inputs=[
                            ProvenanceRef(kind="dataset_snapshot", ref_id=snapshot.id),
                            ProvenanceRef(
                                kind="feature",
                                ref_id=PAIRWISE_RETURN_CORRELATION.id,
                                ref_version=PAIRWISE_RETURN_CORRELATION.version,
                            ),
                        ],
                    ),
                )
            )
        return candidates


class FeatureDiscoveryEngine:
    """Runs every registered generator against one MarketState and persists the results."""

    def __init__(
        self,
        generators: list[FeatureGenerator],
        repository: FeatureCandidateRepository | None = None,
    ):
        self.generators = generators
        self.repository = repository or FeatureCandidateRepository()

    def discover(self, market_state: MarketState) -> list[FeatureCandidate]:
        candidates: list[FeatureCandidate] = []
        for generator in self.generators:
            for candidate in generator.generate(market_state):
                self.repository.add(candidate)
                candidates.append(candidate)
        return candidates
