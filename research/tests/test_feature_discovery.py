from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.features.discovery import (
    FeatureCandidateRepository,
    FeatureDiscoveryEngine,
    PairwiseCorrelationGenerator,
)
from agx_research.market_memory.memory import MarketMemory
from agx_research.universe.sector import StaticSectorProvider
from agx_research.universe.static import StaticUniverseProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_market_state():
    memory = MarketMemory(
        MockDataProvider(MOCK_ROOT),
        StaticUniverseProvider(),
        StaticSectorProvider(),
        tickers=["COMI", "MFPC"],
        macro_series_ids=[],
        lookback_days=30,
    )
    return memory.reconstruct(date(2026, 6, 14))


def test_generator_proposes_candidates_across_the_whole_universe():
    generator = PairwiseCorrelationGenerator(correlation_threshold=0.0)
    candidates = generator.generate(make_market_state())

    assert len(candidates) == 1  # only one pair possible with a 2-ticker universe
    candidate = candidates[0]
    assert candidate.creator == "pairwise_correlation_generator"
    assert candidate.dependencies == ["price_history:COMI", "price_history:MFPC"]
    assert candidate.importance is not None


def test_generator_respects_threshold():
    generator = PairwiseCorrelationGenerator(correlation_threshold=1.01)
    assert generator.generate(make_market_state()) == []


def test_engine_runs_every_generator_and_persists_candidates():
    repo = FeatureCandidateRepository()
    engine = FeatureDiscoveryEngine(
        generators=[PairwiseCorrelationGenerator(correlation_threshold=0.0)], repository=repo
    )

    candidates = engine.discover(make_market_state())

    assert len(candidates) == 1
    assert len(repo.all_latest()) == 1
