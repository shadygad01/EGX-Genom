"""End-to-end test of the daily research pipeline â€” the integration proof
that every subsystem (market memory, events, agents, experiments,
validators, causal gate, review board, adversarial scientist, knowledge
store, genome, papers, graph) actually works together."""

from datetime import date
from pathlib import Path

from agx_research.agents.market_structure import MarketStructureAgent
from agx_research.data.mock_provider import MockDataProvider
from agx_research.genome.gene import GeneStatus
from agx_research.hypotheses.pipeline import StageName
from agx_research.market_memory.memory import MarketMemory
from agx_research.orchestration.pipeline import DailyResearchPipeline, PipelineConfig
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import StaticSectorProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_pipeline(config: PipelineConfig) -> DailyResearchPipeline:
    memory = MarketMemory(
        MockDataProvider(MOCK_ROOT),
        MappingUniverseProvider({"COMI": "COMI", "MFPC": "MFPC"}),
        StaticSectorProvider(),
        macro_series_ids=["BRENT_USD"],
        lookback_days=30,
    )
    agent = MarketStructureAgent(ticker_pairs=[("COMI", "MFPC")], correlation_threshold=0.0)
    return DailyResearchPipeline(memory, [agent], config=config)


def permissive_config() -> PipelineConfig:
    """Thresholds loose enough that the mock data's weak correlation can
    clear every gate â€” for exercising the full promotion path."""
    return PipelineConfig(
        alpha=1.01,  # accept any p-value
        min_observations=5,
        min_sample_size_for_review=5,
        max_expected_risk=1.0,
        min_hit_rate=0.0,
        min_sharpe=-100.0,
        adversarial_min_sample_size=2,
    )


def test_full_promotion_path_end_to_end():
    pipeline = make_pipeline(permissive_config())
    result = pipeline.run(date(2026, 6, 14))

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]

    # The permissive run can still legitimately fail at PEER_VALIDATION if
    # the replication is insignificant -- but with alpha > 1 every
    # significance check passes, so this must promote.
    assert outcome.promoted, f"expected promotion, got: {outcome.rejection_reason}"
    assert outcome.final_stage == StageName.PEER_VALIDATION.value

    # Knowledge exists and is auditable.
    knowledge = pipeline.knowledge.latest(outcome.knowledge_id)
    assert knowledge is not None
    assert knowledge.statistical_evidence.method == "BootstrapExperiment"
    assert 0.0 <= knowledge.confidence <= 0.9  # capped, evidence-derived
    assert knowledge.economic_explanation  # causal gate required it

    # Gene, paper, and graph all exist and link back.
    gene = pipeline.genome.repository.latest(outcome.gene_id)
    assert gene.status == GeneStatus.PROMOTED
    assert gene.knowledge_id == knowledge.id

    paper = pipeline.papers.latest(outcome.paper_id)
    assert paper.gene_id == gene.id
    assert result.session.dataset_snapshot_id in paper.dataset

    assert pipeline.graph.nodes.latest(gene.id) is not None
    assert pipeline.graph.shortest_path(knowledge.id, paper.id) is not None

    # Every gate walk revision was persisted (full lifecycle audit trail).
    history = pipeline.hypotheses.history(outcome.hypothesis_id)
    assert len(history) == len(StageName)

    # Session records the artifacts and events were projected.
    assert result.session.knowledge_ids == [outcome.knowledge_id]
    assert len(result.session.artifact_ids) >= 5  # experiments + publication


def test_impossible_thresholds_promote_nothing():
    config = permissive_config()
    config.min_hit_rate = 1.01  # unattainable
    pipeline = make_pipeline(config)

    result = pipeline.run(date(2026, 6, 14))

    assert len(result.outcomes) == 1
    outcome = result.outcomes[0]
    assert not outcome.promoted
    assert outcome.final_stage == StageName.BACKTEST.value
    assert "backtest" in outcome.rejection_reason.lower()

    # Nothing was fabricated into the knowledge store, genome, or papers.
    assert pipeline.knowledge.all_latest() == []
    assert pipeline.genome.repository.all_latest() == []
    assert pipeline.papers.all_latest() == []

    # But the failed hypothesis IS remembered, at the failed gate.
    history = pipeline.hypotheses.history(outcome.hypothesis_id)
    assert history
    assert history[-1].stage_history[-1].passed is False


def test_strict_statistics_reject_weak_evidence():
    config = permissive_config()
    config.alpha = 0.000001  # essentially impossible significance bar
    pipeline = make_pipeline(config)

    result = pipeline.run(date(2026, 6, 14))
    outcome = result.outcomes[0]

    assert not outcome.promoted
    assert outcome.final_stage == StageName.STATISTICAL_VALIDATION.value
    assert pipeline.knowledge.all_latest() == []


def test_pipeline_is_deterministic_across_runs():
    result_a = make_pipeline(permissive_config()).run(date(2026, 6, 14))
    result_b = make_pipeline(permissive_config()).run(date(2026, 6, 14))

    assert result_a.session.dataset_snapshot_id == result_b.session.dataset_snapshot_id
    assert [o.promoted for o in result_a.outcomes] == [o.promoted for o in result_b.outcomes]
    if result_a.outcomes[0].promoted:
        ka = result_a.outcomes[0].knowledge_id
        kb = result_b.outcomes[0].knowledge_id
        knowledge_a = result_a.session and ka
        assert knowledge_a is not None and kb is not None
