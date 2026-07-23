from datetime import date, datetime

from agx_research.causal.assessment import CandidateCause
from agx_research.causal.reasoner import EconomicRationaleGate
from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.hypothesis import Hypothesis


def hypothesis() -> Hypothesis:
    return Hypothesis(
        id="hyp-causal",
        statement="test",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=["COMI"],
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )


def test_rejects_correlation_alone():
    gate = EconomicRationaleGate()
    assessment = gate.assess(hypothesis())

    assert assessment.confidence == 0.0
    assert "correlation alone" in assessment.notes.lower()


def test_rejects_rationale_without_candidate_cause():
    gate = EconomicRationaleGate()
    assessment = gate.assess(hypothesis(), economic_rationale="Banks benefit from higher rates.")
    assert assessment.confidence == 0.0


def test_rejects_candidate_cause_without_rationale():
    gate = EconomicRationaleGate()
    assessment = gate.assess(
        hypothesis(),
        candidate_causes=[CandidateCause(description="rate hike", mechanism="net interest margin")],
    )
    assert assessment.confidence == 0.0


def test_passes_with_both_cause_and_rationale_but_caps_confidence():
    gate = EconomicRationaleGate()
    assessment = gate.assess(
        hypothesis(),
        candidate_causes=[CandidateCause(description="rate hike", mechanism="net interest margin")],
        economic_rationale="Banks benefit from higher rates via wider net interest margins.",
    )
    assert assessment.confidence == 0.5  # necessary, not sufficient -- capped, not full confidence
    assert assessment.hypothesis_id == "hyp-causal"
