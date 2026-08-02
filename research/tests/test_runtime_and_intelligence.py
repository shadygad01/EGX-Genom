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
from agx_research.financials.schema import FinancialStatementLineItem
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
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider
from agx_research.valuation import FairValueEngine
from agx_research.validation.statistical import StatisticalEvidence

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_memory() -> MarketMemory:
    return MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI", "MFPC": "MFPC"}),
        StaticSectorProvider(),
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


def test_future_knowledge_cannot_time_travel_into_prediction():
    from agx_research.horizons.knowledge_weighted import KnowledgeWeightedHorizonModel

    items = promoted_store().all_latest()
    future = items[0].model_copy(update={"discovery_date": date(2026, 7, 1)})
    model = KnowledgeWeightedHorizonModel(future.horizon)
    assert model.predict("COMI", date(2026, 6, 14), [future]) is None


def test_readiness_blocks_unready_horizons_before_recommendation():
    store = promoted_store()
    service = RecommendationService(store)
    assert service.recommend(
        ["COMI"], date(2026, 6, 14), ready_horizons_by_ticker={"COMI": set()}
    ) == []
    recommendations = service.recommend(
        ["COMI"], date(2026, 6, 14),
        ready_horizons_by_ticker={"COMI": {Horizon.MICRO}},
    )
    assert len(recommendations) == 1
    assert set(recommendations[0].horizon_decisions) == {Horizon.MICRO}


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


def test_recent_market_wide_event_reduces_every_egx_ticker_confidence():
    store = promoted_store()
    baseline = RecommendationService(store).recommend(["COMI"], date(2026, 6, 14))[0]
    events = EventPlatform()
    events.register(
        build_candidate_event(
            event_type=EventType.NEWS,
            subtype=EventSubtype.MACRO_NEWS,
            entities=[
                EntityRef(
                    kind=EntityKind.MARKET,
                    canonical_id="EGX",
                    raw_mention="market-wide headline",
                )
            ],
            event_date=date(2026, 6, 13),
            source="alborsa",
            confidence=0.6,
            severity=EventSeverity.MEDIUM,
            provenance=Provenance(produced_by="RssNewsCollector", produced_at=datetime.now()),
        )
    )

    adjusted = RecommendationService(store, event_platform=events).recommend(
        ["COMI"], date(2026, 6, 14)
    )[0]

    assert adjusted.confidence < baseline.confidence
    assert any("sources=alborsa" in item for item in adjusted.explanation.supporting_evidence)


def test_repeated_market_headlines_do_not_multiply_the_same_risk_channel():
    store = promoted_store()
    one_event = EventPlatform()
    many_events = EventPlatform()
    for index in range(6):
        candidate = build_candidate_event(
            event_type=EventType.NEWS,
            subtype=EventSubtype.MACRO_NEWS,
            entities=[EntityRef(
                kind=EntityKind.MARKET,
                canonical_id="EGX",
                raw_mention=f"market headline {index}",
            )],
            event_date=date(2026, 6, 9 + index),
            source=f"free-news-{index}",
            confidence=0.6,
            severity=EventSeverity.LOW,
            provenance=Provenance(
                produced_by="RssNewsCollector", produced_at=datetime.now()
            ),
        )
        many_events.register(candidate)
        if index == 5:
            one_event.register(candidate)

    one = RecommendationService(store, event_platform=one_event).recommend(
        ["COMI"], date(2026, 6, 14)
    )[0]
    many = RecommendationService(store, event_platform=many_events).recommend(
        ["COMI"], date(2026, 6, 14)
    )[0]

    assert many.confidence == one.confidence
    assert many.combined_expected_risk == one.combined_expected_risk
    assert sum(item.startswith("event ") for item in many.explanation.supporting_evidence) == 1


class _FairValueFinancialsProvider:
    """Enough real annual line items for `FairValueEngine` to compute a
    value; unscaled and without a sector hint (matching how
    `RecommendationService` calls `.value()`), this yields a weighted fair
    value of ~14.67 for any ticker, far below COMI's real mock close
    (68.40 on 2026-06-14)."""

    def __init__(self, ticker: str = "COMI"):
        values = {
            2023: {"revenue": 1000, "operating_income": 220, "net_income": 150, "free_cash_flow": 130, "ebitda": 260, "total_equity": 700, "cash_and_equivalents": 150, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.5, "dividend_per_share": .5},
            2024: {"revenue": 1100, "operating_income": 240, "net_income": 165, "free_cash_flow": 140, "ebitda": 280, "total_equity": 780, "cash_and_equivalents": 170, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.65, "dividend_per_share": .55},
            2025: {"revenue": 1200, "operating_income": 260, "net_income": 180, "free_cash_flow": 150, "ebitda": 300, "total_equity": 860, "cash_and_equivalents": 190, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.8, "dividend_per_share": .6},
        }
        self.items = [
            FinancialStatementLineItem(
                ticker=ticker, period_end_date=date(year, 12, 31),
                period_type="ANNUAL", statement_type="TEST", line_item=name, value=value,
            )
            for year, row in values.items() for name, value in row.items()
        ]

    def get_line_items(self, ticker, start, end, *, statement_type=None):
        return [item for item in self.items if start <= item.period_end_date <= end]


def test_fair_value_blends_into_investment_prediction_and_surfaces_as_evidence():
    # A hand-seeded promoted INVESTMENT-horizon knowledge object (bypassing
    # the promotion gate via `._repo.add`, same pattern test_dashboard.py
    # uses) isolates the fair-value blend from needing a full pipeline run
    # to happen to promote an INVESTMENT-horizon finding.
    store = KnowledgeStore()
    store._repo.add(KnowledgeObject(
        id="know-fv-test",
        discovery_date=date(2026, 5, 1),
        creator_agent="test",
        supporting_evidence=[],
        confidence=0.7,
        statistical_evidence=StatisticalEvidence(
            method="test", statistic=2.0, p_value=0.01, sample_size=40
        ),
        economic_explanation="test",
        affected_assets=["COMI"],
        horizon="investment",
        expected_return=0.03,
        expected_risk=0.05,
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    ))
    provider = _FairValueFinancialsProvider()
    provider.items.append(
        FinancialStatementLineItem(
            ticker="COMI",
            period_end_date=date(2026, 6, 14),
            period_type="SNAPSHOT",
            statement_type="MARKET_FUNDAMENTALS",
            line_item="market_pe",
            value=8.0,
        )
    )
    service = RecommendationService(store, fair_value_engine=FairValueEngine(provider))
    recommendations = service.recommend(
        ["COMI"], date(2026, 6, 14), latest_prices={"COMI": 68.40}
    )

    assert len(recommendations) == 1
    decision = recommendations[0].horizon_decisions[Horizon.INVESTMENT]
    # Fair value (~14.67) is far below the 68.40 mock price, so the 20%
    # fair-value weight must pull expected_return down from the raw
    # knowledge-only 0.03, not leave it untouched.
    assert decision.expected_return < 0.03
    evidence = " ".join(recommendations[0].explanation.supporting_evidence)
    assert "Calculated fair value=14.67" in evidence
    assert "vs. fair value" in evidence
    assert "Market P/E=8.00" in evidence
    assert any(ref.kind == "calculated_fair_value" for ref in recommendations[0].explanation.evidence_refs)
    assert any(
        ref.kind == "market_fundamental_snapshot"
        for ref in recommendations[0].explanation.evidence_refs
    )


def test_reliable_fair_value_can_issue_an_investment_prediction_without_promoted_knowledge():
    service = RecommendationService(
        KnowledgeStore(),
        fair_value_engine=FairValueEngine(_FairValueFinancialsProvider()),
    )

    [recommendation] = service.recommend(
        ["COMI"],
        date(2026, 6, 14),
        ready_horizons_by_ticker={"COMI": {Horizon.INVESTMENT}},
        latest_prices={"COMI": 10.0},
    )

    prediction = recommendation.horizon_predictions[Horizon.INVESTMENT]
    assert prediction.model_id == "multi_model_fair_value"
    assert prediction.expected_return > 0
    assert prediction.confidence >= 0.70
    assert recommendation.supporting_knowledge_ids == []
    assert any(
        ref.kind == "calculated_fair_value"
        for ref in recommendation.explanation.evidence_refs
    )


def test_portfolio_construction_allocates_and_explains():
    store = promoted_store()
    recommendations = RecommendationService(store).recommend(["COMI", "MFPC"], date(2026, 6, 14))
    portfolio = PortfolioConstructor(max_position_weight=0.25).construct(
        recommendations, date(2026, 6, 14)
    )

    total_weight = sum(p.weight for p in portfolio.positions) + portfolio.cash_weight
    assert abs(total_weight - 1.0) < 1e-9
    assert all(p.weight <= 0.25 + 1e-9 for p in portfolio.positions)
    assert portfolio.positions == []
    assert portfolio.cash_weight == 1.0
    assert portfolio.explanation.why_not_others


def test_portfolio_allocates_only_publication_ready_numeric_buy():
    recommendations = RecommendationService(promoted_store()).recommend(
        ["COMI"], date(2026, 6, 14), latest_prices={"COMI": 50.0}
    )
    decision = next(iter(recommendations[0].horizon_decisions.values()))
    decision.action = "buy_candidate"
    decision.publication_status = "publication_ready"
    decision.entry_value = 50.0
    decision.invalidation_value = 45.0
    decision.max_position_pct = 0.05
    portfolio = PortfolioConstructor().construct(recommendations, date(2026, 6, 14))
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].weight == 0.05
    assert portfolio.cash_weight == 0.95


def test_empty_recommendations_yield_all_cash_portfolio():
    portfolio = PortfolioConstructor().construct([], date(2026, 6, 14))
    assert portfolio.positions == []
    assert portfolio.cash_weight == 1.0
    assert "cash" in portfolio.explanation.why_this_stock.lower()


# --- 17 Continuous Learning ---


def _knowledge(
    knowledge_id: str, ticker: str, expected_return: float,
    horizon: Horizon = Horizon.SWING,
) -> KnowledgeObject:
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
        horizon=horizon,
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
        "know-wrong",
        knowledge.affected_assets[0],
        -0.05 if realized_positive else 0.05,
        knowledge.horizon,
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
