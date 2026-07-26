from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.features.discovery import (
    FeatureCandidateRepository,
    FeatureDiscoveryEngine,
    PairwiseCorrelationGenerator,
)
from agx_research.market_memory.memory import MarketMemory
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_market_state():
    memory = MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI", "MFPC": "MFPC"}),
        StaticSectorProvider(),
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


def test_momentum_generator_proposes_scored_candidates():
    from agx_research.features.generators import MomentumGenerator

    candidates = MomentumGenerator(score_threshold=0.0).generate(make_market_state())
    assert len(candidates) == 2  # one per ticker
    for candidate in candidates:
        assert candidate.feature_id.startswith("trailing_mean_return:")
        assert candidate.importance is not None
        assert any(e.startswith("t_like_score=") for e in candidate.evidence)


def test_momentum_generator_respects_threshold():
    from agx_research.features.generators import MomentumGenerator

    assert MomentumGenerator(score_threshold=1e9).generate(make_market_state()) == []


def test_volatility_generator_flags_outliers_vs_median():
    from agx_research.features.generators import VolatilityGenerator

    # Threshold 1.0 means every ticker qualifies (ratio >= 1 or <= 1 always).
    candidates = VolatilityGenerator(ratio_threshold=1.0).generate(make_market_state())
    assert len(candidates) == 2
    # A high threshold with a 2-ticker universe should flag none (both near median).
    assert VolatilityGenerator(ratio_threshold=100.0).generate(make_market_state()) == []


def test_default_registry_now_carries_three_features():
    from agx_research.features.correlation import default_feature_registry

    registry = default_feature_registry()
    assert registry.get("pairwise_return_correlation", 1)
    assert registry.get("trailing_mean_return", 1)
    assert registry.get("trailing_volatility", 1)
