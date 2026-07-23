from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.hypothesis import Hypothesis, StageResult
from agx_research.hypotheses.pipeline import StageName
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import PerformanceRecord
from agx_research.knowledge.store import KnowledgeStore
from agx_research.validation.statistical import StatisticalEvidence


def peer_validated_hypothesis() -> Hypothesis:
    hypothesis = Hypothesis(
        id="hyp-002",
        statement="Positive earnings surprises produce delayed drift in bank stocks",
        created_by="corporate_events_agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.SWING,
        affected_assets=["COMI"],
        provenance=Provenance(produced_by="corporate_events_agent@0.1.0", produced_at=datetime.now()),
    )
    for stage in StageName:
        hypothesis = hypothesis.advance(
            StageResult(stage_name=stage.value, passed=True, evaluated_at=datetime.now())
        )
    return hypothesis


def evidence() -> StatisticalEvidence:
    return StatisticalEvidence(
        method="SignificanceThresholdValidator", statistic=2.6, p_value=0.01, sample_size=42
    )


def test_promote_rejects_hypothesis_not_at_final_gate():
    store = KnowledgeStore()
    hypothesis = Hypothesis(
        id="hyp-003",
        statement="unvalidated",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=["COMI"],
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )
    with pytest.raises(ValueError):
        store.promote(
            hypothesis,
            confidence=0.5,
            statistical_evidence=evidence(),
            economic_explanation="n/a",
            expected_return=0.0,
            expected_risk=0.0,
        )


def test_promote_creates_knowledge_object():
    store = KnowledgeStore()
    hypothesis = peer_validated_hypothesis()

    knowledge = store.promote(
        hypothesis,
        confidence=0.72,
        statistical_evidence=evidence(),
        economic_explanation="Post-earnings-announcement drift in EGX banking sector",
        expected_return=0.03,
        expected_risk=0.02,
        supporting_evidence=["backtest_sharpe=1.4"],
    )

    assert knowledge.id == hypothesis.id
    assert knowledge.version == 1
    assert knowledge.status == KnowledgeStatus.PROMOTED
    assert knowledge.provenance.inputs[0].kind == "hypothesis"
    assert knowledge.provenance.inputs[0].ref_id == hypothesis.id
    assert store.latest(hypothesis.id) == knowledge


def test_status_transitions_and_versioning():
    store = KnowledgeStore()
    hypothesis = peer_validated_hypothesis()
    store.promote(
        hypothesis,
        confidence=0.72,
        statistical_evidence=evidence(),
        economic_explanation="...",
        expected_return=0.03,
        expected_risk=0.02,
    )

    monitored = store.transition_status(hypothesis.id, KnowledgeStatus.MONITORING)
    assert monitored.version == 2
    assert monitored.status == KnowledgeStatus.MONITORING

    retired = store.transition_status(
        hypothesis.id, KnowledgeStatus.RETIRED, reason="performance degraded below threshold"
    )
    assert retired.version == 3
    assert retired.status == KnowledgeStatus.RETIRED
    assert retired.retirement_reason == "performance degraded below threshold"

    with pytest.raises(ValueError):
        store.transition_status(hypothesis.id, KnowledgeStatus.MONITORING)

    assert len(store.revisions_for(hypothesis.id)) == 3


def test_record_performance_appends_history():
    store = KnowledgeStore()
    hypothesis = peer_validated_hypothesis()
    store.promote(
        hypothesis,
        confidence=0.72,
        statistical_evidence=evidence(),
        economic_explanation="...",
        expected_return=0.03,
        expected_risk=0.02,
    )

    updated = store.record_performance(
        hypothesis.id, PerformanceRecord(as_of=date(2026, 7, 1), realized_return=0.025)
    )
    assert len(updated.performance_history) == 1
    assert updated.performance_history[0].realized_return == 0.025


def test_persistence_roundtrip(tmp_path):
    persist_path = tmp_path / "knowledge.json"
    store = KnowledgeStore(persist_path=persist_path)
    hypothesis = peer_validated_hypothesis()
    store.promote(
        hypothesis,
        confidence=0.72,
        statistical_evidence=evidence(),
        economic_explanation="...",
        expected_return=0.03,
        expected_risk=0.02,
    )

    reloaded = KnowledgeStore(persist_path=persist_path)
    assert reloaded.latest(hypothesis.id) is not None
    assert reloaded.latest(hypothesis.id).id == hypothesis.id
