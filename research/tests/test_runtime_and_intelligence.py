"""Systems 13-17 integration: the runtime engine drives the pipeline over a
date range; promoted knowledge feeds knowledge-weighted predictions,
recommendations, portfolio construction, and continuous-learning
monitoring/retirement."""

from datetime import date, datetime
from pathlib import Path

from agx_research.agents.market_structure import MarketStructureAgent
from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.domain.provenance import Provenance
from agx_research.events.entity import EntityKind, EntityRef
from agx_research.events.event import EventSeverity, EventType
from agx_research.events.service import EventPlatform, build_candidate_event
from agx_research.events.taxonomy import EventSubtype
from agx_research.genome.gene import GeneStatus
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.knowledge.store import KnowledgeStore
from agx_research.learning.monitor import ContinuousLearningMonitor
from agx_research.market_memory.calendar import StaticEGXCalendar
from agx_research.market_memory.memory import MarketMemory
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.orchestration.pipeline import DailyResearchPipeline, PipelineConfig
from agx_research.portfolio.constructor import PortfolioConstructor
from agx_research.runtime.engine import RunStatus, RuntimeEngine
from agx_research.universe.sector import StaticSectorProvider
from agx_research.universe.static import StaticUniverseProvider
from agx_research.validation.statistical import StatisticalEvidence

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_memory() -> MarketMemory:
    return MarketMemory(
        MockDataProvider(MOCK_ROOT),
        StaticUniverseProvider(),
        StaticSectorProvider(),
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )


def permissive_pipeline() -> DailyResearchPipeline:
    config = PipelineConfig(
        alpha=1.01,
        min_observations=5,
        min_sample_size_for_review=5,
        max_expected_risk=1.0,
        min_hit_rate=0.0,
        min_sharpe=-100.0,
        adversarial_min_sample_size=2,
    )
    agent = MarketStructureAgent(ticker_pairs=[("COMI", "MFPC")], correlation_threshold=0.0)
    return DailyResearchPipeline(make_memory(), [agent], config=config)


# --- 13 Runtime Engine ---


def test_runtime_engine_runs_a_range_with_skips_and_isolation():
    engine = RuntimeEngine(permissive_pipeline(), calendar=StaticEGXCalendar(movable_holidays={}))
    # Thu 2026-06-11 .. Sun 2026-06-14: Thu trades, Fri+Sat weekend, Sun trades.
    records = engine.run_range(date(2026, 6, 11), date(2026, 6, 14))

    assert [r.status for r in records] == [
        RunStatus.SUCCEEDED,
        RunStatus.SKIPPED_NON_TRADING,
        RunStatus.SKIPPED_NON_TRADING,
        RunStatus.SUCCEEDED,
    ]
    assert all(r.session_id for r in records if r.status == RunStatus.SUCCEEDED)
    assert len(engine.run_records.all_latest()) == 4


def test_runtime_engine_records_failures_instead_of_halting():
    class ExplodingPipeline:
        def run(self, as_of):
            raise RuntimeError("data feed exploded")

    engine = RuntimeEngine(ExplodingPipeline(), calendar=StaticEGXCalendar(movable_holidays={}))
    records = engine.run_range(date(2026, 6, 14), date(2026, 6, 15))

    assert all(r.status == RunStatus.FAILED for r in records)
    assert "data feed exploded" in records[0].error
    assert len(records) == 2  # the second day still ran


# --- 14/15/16: prediction -> recommendation -> portfolio ---


def promoted_store() -> KnowledgeStore:
    """A knowledge store holding one genuinely promoted object, produced by
    the real pipeline (not hand-built)."""
    pipeline = permissive_pipeline()
    result = pipeline.run(date(2026, 6, 14))
    assert result.outcomes[0].promoted
    return pipeline.knowledge


def test_knowledge_weighted_prediction_and_recommendation_flow():
    store = promoted_store()
    service = RecommendationService(store)
    recommendations = service.recommend(["COMI", "MFPC", "SWDY"], date(2026, 6, 14))

    # Knowledge covers COMI and MFPC (the pair); SWDY has none -> no recommendation.
    assert {r.ticker for r in recommendations} == {"COMI", "MFPC"}
    for rec in recommendations:
        assert rec.explanation.evidence_refs  # structured, not just prose
        assert rec.supporting_knowledge_ids
        assert 0.0 <= rec.confidence <= 0.9


def test_no_knowledge_means_no_prediction():
    from agx_research.horizons.knowledge_weighted import KnowledgeWeightedHorizonModel

    model = KnowledgeWeightedHorizonModel(Horizon.MICRO)
    assert model.predict("COMI", date(2026, 6, 14), []) is None


def test_recent_source_event_reduces_confidence_and_is_in_decision_provenance():
    store = promoted_store()
    baseline = RecommendationService(store).recommend(["COMI"], date(2026, 6, 14))[0]
    events = EventPlatform()
    event = events.register(
        build_candidate_event(
            event_type=EventType.NEWS,
            subtype=EventSubtype.COMPANY_NEWS,
            entities=[EntityRef(kind=EntityKind.COMPANY, canonical_id="COMI", raw_mention="COMI")],
            event_date=date(2026, 6, 13),
            source="gdelt",
            confidence=0.8,
            severity=EventSeverity.HIGH,
            provenance=Provenance(produced_by="GdeltDocCollector", produced_at=datetime.now()),
        )
    )
    adjusted = RecommendationService(store, event_platform=events).recommend(
        ["COMI"], date(2026, 6, 14)
    )[0]
    assert adjusted.confidence < baseline.confidence
    assert adjusted.combined_expected_risk > baseline.combined_expected_risk
    assert any(
        ref.kind == "event" and ref.ref_id == event.id for ref in adjusted.explanation.evidence_refs
    )
    assert any("sources=gdelt" in item for item in adjusted.explanation.supporting_evidence)


def test_portfolio_construction_allocates_and_explains():
    store = promoted_store()
    recommendations = RecommendationService(store).recommend(["COMI", "MFPC"], date(2026, 6, 14))
    portfolio = PortfolioConstructor(max_position_weight=0.25).construct(
        recommendations, date(2026, 6, 14)
    )

    total_weight = sum(p.weight for p in portfolio.positions) + portfolio.cash_weight
    assert abs(total_weight - 1.0) < 1e-9
    assert all(p.weight <= 0.25 + 1e-9 for p in portfolio.positions)
    assert portfolio.explanation.why_not_others


def test_empty_recommendations_yield_all_cash_portfolio():
    portfolio = PortfolioConstructor().construct([], date(2026, 6, 14))
    assert portfolio.positions == []
    assert portfolio.cash_weight == 1.0
    assert "cash" in portfolio.explanation.why_this_stock.lower()


# --- 17 Continuous Learning ---


def _knowledge(knowledge_id: str, ticker: str, expected_return: float) -> KnowledgeObject:
    return KnowledgeObject(
        id=knowledge_id,
        discovery_date=date(2026, 5, 1),
        creator_agent="test",
        supporting_evidence=[],
        confidence=0.7,
        statistical_evidence=StatisticalEvidence(
            method="test", statistic=2.0, p_value=0.01, sample_size=40
        ),
        economic_explanation="test",
        affected_assets=[ticker],
        horizon=Horizon.SWING,
        expected_return=expected_return,
        expected_risk=0.02,
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


def test_monitor_records_performance_and_retires_wrong_sign_knowledge():
    store = promoted_store()  # COMI/MFPC knowledge, expected_return from real data
    from agx_research.genome.service import AlphaGenome

    genome = AlphaGenome()
    knowledge = store.all_latest()[0]
    gene = genome.promote_to_gene(knowledge)

    # Force a wrong-sign expectation so the retirement branch is exercised
    # honestly: the realized data is real; only the expectation is inverted.
    realized_positive = knowledge.expected_return > 0
    wrong = _knowledge(
        "know-wrong", knowledge.affected_assets[0], -0.05 if realized_positive else 0.05
    )
    store._repo.add(wrong)  # test-only injection of a pre-existing object
    wrong_gene = genome.promote_to_gene(wrong)

    monitor = ContinuousLearningMonitor(store, genome, make_memory(), min_records=1)
    outcomes = monitor.evaluate(date(2026, 6, 14))

    by_id = {o.knowledge_id: o for o in outcomes}
    assert by_id["know-wrong"].retired is True
    assert "disagreed" in by_id["know-wrong"].reason
    assert store.latest("know-wrong").status == KnowledgeStatus.RETIRED
    assert genome.repository.latest(wrong_gene.id).status == GeneStatus.RETIRED

    # The correctly-signed knowledge moved to MONITORING with a record, not retired.
    survivor = store.latest(knowledge.id)
    assert survivor.status == KnowledgeStatus.MONITORING
    assert len(survivor.performance_history) == 1
    assert genome.repository.latest(gene.id).status == GeneStatus.MONITORING
