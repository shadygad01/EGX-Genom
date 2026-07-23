from datetime import date, datetime
from pathlib import Path

from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.domain.provenance import Provenance
from agx_research.genome.service import AlphaGenome
from agx_research.hypotheses.experiment_factory import ExperimentFactory
from agx_research.hypotheses.hypothesis import Hypothesis, StageResult
from agx_research.hypotheses.pipeline import StageName
from agx_research.knowledge.store import KnowledgeStore
from agx_research.papers.generator import generate_paper
from agx_research.papers.repository import PaperRepository
from agx_research.validation.statistical import StatisticalEvidence

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def build_promoted_gene():
    hypothesis = Hypothesis(
        id="hyp-paper",
        statement="COMI and MFPC returns co-move beyond chance",
        created_by="market_structure_agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=["COMI", "MFPC"],
        provenance=Provenance(produced_by="market_structure_agent@0.1.0", produced_at=datetime.now()),
    )
    for stage in StageName:
        hypothesis = hypothesis.advance(
            StageResult(stage_name=stage.value, passed=True, evaluated_at=datetime.now())
        )

    store = KnowledgeStore()
    knowledge = store.promote(
        hypothesis,
        confidence=0.65,
        statistical_evidence=StatisticalEvidence(
            method="SignificanceThresholdValidator", statistic=2.1, p_value=0.03, sample_size=9
        ),
        economic_explanation="Both are large-cap EGX30 names subject to similar market-wide flows.",
        expected_return=0.015,
        expected_risk=0.01,
        supporting_evidence=["pearson_correlation=0.62"],
    )

    genome = AlphaGenome()
    gene = genome.promote_to_gene(knowledge)
    return hypothesis, knowledge, gene


def test_generate_paper_populates_every_section_from_real_evidence():
    hypothesis, knowledge, gene = build_promoted_gene()

    provider = MockDataProvider(MOCK_ROOT)
    snapshot = build_snapshot(
        provider, tickers=["COMI", "MFPC"], macro_series_ids=[], as_of=date(2026, 6, 14), lookback_days=30
    )
    experiment_results = ExperimentFactory().run_all(hypothesis, snapshot)

    paper = generate_paper(
        gene=gene,
        hypothesis=hypothesis,
        knowledge=knowledge,
        experiment_results=experiment_results,
        dataset_snapshot_id=snapshot.id,
    )

    assert paper.title == hypothesis.statement
    assert "COMI" in paper.problem and "MFPC" in paper.problem
    assert hypothesis.created_by in paper.observation
    assert "PEER_VALIDATION" in paper.methodology
    assert snapshot.id in paper.dataset
    assert "CrossValidationExperiment" in paper.experiments
    assert "pearson_correlation=0.62" in paper.evidence
    assert str(gene.generation) in paper.results
    assert paper.conclusion == knowledge.economic_explanation
    assert paper.gene_id == gene.id
    assert paper.knowledge_id == knowledge.id
    assert paper.hypothesis_id == hypothesis.id


def test_generate_paper_without_dataset_id_or_causal_assessment_still_works():
    hypothesis, knowledge, gene = build_promoted_gene()
    paper = generate_paper(gene=gene, hypothesis=hypothesis, knowledge=knowledge, experiment_results={})

    assert "not provided" in paper.dataset
    assert "No causal assessment" in paper.limitations
    assert paper.experiments == "No experiments were run."


def test_paper_repository_persists_and_versions():
    hypothesis, knowledge, gene = build_promoted_gene()
    paper = generate_paper(gene=gene, hypothesis=hypothesis, knowledge=knowledge, experiment_results={})

    repo = PaperRepository()
    repo.add(paper)
    assert repo.latest(paper.id) == paper
