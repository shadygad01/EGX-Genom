from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.genome.gene import GeneStatus
from agx_research.genome.service import AlphaGenome
from agx_research.knowledge.schema import KnowledgeObject, PerformanceRecord
from agx_research.validation.statistical import StatisticalEvidence


def make_knowledge(knowledge_id: str, expected_return: float = 0.03) -> KnowledgeObject:
    return KnowledgeObject(
        id=knowledge_id,
        discovery_date=date(2026, 5, 12),
        creator_agent="corporate_events_agent",
        supporting_evidence=["backtest_sharpe=1.4"],
        confidence=0.7,
        statistical_evidence=StatisticalEvidence(
            method="SignificanceThresholdValidator", statistic=2.5, p_value=0.01, sample_size=40
        ),
        economic_explanation="test",
        affected_assets=["COMI"],
        horizon=Horizon.SWING,
        expected_return=expected_return,
        expected_risk=0.02,
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


def test_promote_to_gene_creates_generation_zero():
    genome = AlphaGenome()
    gene = genome.promote_to_gene(make_knowledge("know-1"))

    assert gene.generation == 0
    assert gene.parent_gene_ids == []
    assert gene.status == GeneStatus.PROMOTED
    assert gene.knowledge_id == "know-1"


def test_mutate_creates_a_new_gene_and_marks_parent_replaced():
    genome = AlphaGenome()
    parent = genome.promote_to_gene(make_knowledge("know-1", expected_return=0.03))

    child = genome.mutate(parent.id, make_knowledge("know-2", expected_return=0.045), "refined with more data")

    assert child.generation == 1
    assert child.parent_gene_ids == [parent.id]
    assert child.knowledge_id == "know-2"

    updated_parent = genome.repository.latest(parent.id)
    assert updated_parent.status == GeneStatus.REPLACED
    assert updated_parent.child_gene_ids == [child.id]

    # The parent's original revision is never overwritten -- it's still in history.
    history = genome.repository.history(parent.id)
    assert history[0].status == GeneStatus.PROMOTED
    assert history[-1].status == GeneStatus.REPLACED


def test_lineage_walks_back_to_the_root():
    genome = AlphaGenome()
    gen0 = genome.promote_to_gene(make_knowledge("know-1"))
    gen1 = genome.mutate(gen0.id, make_knowledge("know-2"), "mutation 1")
    gen2 = genome.mutate(gen1.id, make_knowledge("know-3"), "mutation 2")

    lineage = genome.lineage(gen2.id)

    assert [g.knowledge_id for g in lineage] == ["know-1", "know-2", "know-3"]
    assert [g.generation for g in lineage] == [0, 1, 2]


def test_status_transitions_are_validated():
    genome = AlphaGenome()
    gene = genome.promote_to_gene(make_knowledge("know-1"))

    monitored = genome.transition_status(gene.id, GeneStatus.MONITORING)
    assert monitored.status == GeneStatus.MONITORING

    with pytest.raises(ValueError):
        genome.transition_status(gene.id, GeneStatus.PROPOSED)


def test_record_performance_appends_history():
    genome = AlphaGenome()
    gene = genome.promote_to_gene(make_knowledge("know-1"))

    updated = genome.record_performance(
        gene.id, PerformanceRecord(as_of=date(2026, 7, 1), realized_return=0.02)
    )
    assert len(updated.performance_history) == 1


def test_mutate_unknown_parent_raises():
    genome = AlphaGenome()
    with pytest.raises(KeyError):
        genome.mutate("does-not-exist", make_knowledge("know-1"), "n/a")
