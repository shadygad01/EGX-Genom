from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.hypotheses.hypothesis import Hypothesis, HypothesisStage, StageResult
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import PerformanceRecord
from agx_research.knowledge.store import KnowledgeStore


def peer_validated_hypothesis() -> Hypothesis:
    hypothesis = Hypothesis(
        id="hyp-002",
        statement="Positive earnings surprises produce delayed drift in bank stocks",
        created_by="corporate_events_agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.SWING,
        affected_assets=["COMI"],
    )
    for stage in HypothesisStage:
        hypothesis.advance(StageResult(stage=stage, passed=True, evaluated_at=datetime.now()))
    return hypothesis


def test_promote_rejects_hypothesis_not_at_peer_validation():
    store = KnowledgeStore()
    hypothesis = Hypothesis(
        id="hyp-003",
        statement="unvalidated",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=["COMI"],
    )
    with pytest.raises(ValueError):
        store.promote(
            hypothesis,
            confidence=0.5,
            statistical_strength=0.01,
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
        statistical_strength=0.01,
        economic_explanation="Post-earnings-announcement drift in EGX banking sector",
        expected_return=0.03,
        expected_risk=0.02,
        supporting_evidence=["p_value=0.01", "backtest_sharpe=1.4"],
    )

    assert knowledge.id == hypothesis.id
    assert knowledge.version == 1
    assert knowledge.status == KnowledgeStatus.PROMOTED
    assert store.latest(hypothesis.id) == knowledge


def test_status_transitions_and_versioning():
    store = KnowledgeStore()
    hypothesis = peer_validated_hypothesis()
    store.promote(
        hypothesis,
        confidence=0.72,
        statistical_strength=0.01,
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
        statistical_strength=0.01,
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
        statistical_strength=0.01,
        economic_explanation="...",
        expected_return=0.03,
        expected_risk=0.02,
    )

    reloaded = KnowledgeStore(persist_path=persist_path)
    assert reloaded.latest(hypothesis.id) is not None
    assert reloaded.latest(hypothesis.id).id == hypothesis.id
