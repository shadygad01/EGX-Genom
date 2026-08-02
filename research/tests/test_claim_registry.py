from datetime import date, datetime

import pytest

from agx_research.claims import ClaimRegistry, ClaimStage
from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.hypothesis import Hypothesis


def hypothesis() -> Hypothesis:
    return Hypothesis(
        id="hyp-claim",
        statement="Low leverage predicts superior investment returns",
        created_by="financial_performance",
        created_at=date(2026, 8, 2),
        horizon=Horizon.INVESTMENT,
        affected_assets=["COMI"],
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


def test_claim_is_production_blocked_until_validation():
    registry = ClaimRegistry()
    claim = registry.register_hypothesis(hypothesis())
    assert registry.production_eligible() == []

    claim = registry.record(
        claim.id, stage=ClaimStage.EXPERIMENT, evidence_type="backtest", ref_id="exp-1", passed=True
    )
    assert not claim.is_experimentally_validated

    claim = registry.record(
        claim.id,
        stage=ClaimStage.VALIDATION,
        evidence_type="statistical",
        ref_id="val-1",
        passed=True,
    )
    assert registry.production_eligible() == [claim]


def test_claim_lifecycle_cannot_skip_or_use_a_paper_as_validation():
    registry = ClaimRegistry()
    claim = registry.register_hypothesis(hypothesis())
    with pytest.raises(ValueError, match="Papers are evidence containers"):
        registry.record(
            claim.id,
            stage=ClaimStage.VALIDATION,
            evidence_type="paper",
            ref_id="paper-1",
            passed=True,
        )

    attached = registry.attach_paper(claim.id, "paper-1")
    assert attached.source_paper_ids == ["paper-1"]
    assert not attached.is_experimentally_validated


def test_failed_stage_rejects_claim_and_makes_it_terminal():
    registry = ClaimRegistry()
    claim = registry.register_hypothesis(hypothesis())
    rejected = registry.record(
        claim.id,
        stage=ClaimStage.EXPERIMENT,
        evidence_type="backtest",
        ref_id="exp-1",
        passed=False,
        notes="Effect vanished out of sample",
    )
    assert rejected.stage == ClaimStage.REJECTED
    assert rejected.rejection_reason == "Effect vanished out of sample"
    with pytest.raises(ValueError, match="terminal"):
        registry.record(
            claim.id,
            stage=ClaimStage.EXPERIMENT,
            evidence_type="retry",
            ref_id="exp-2",
            passed=True,
        )


def test_paper_decomposition_creates_independent_claims():
    registry = ClaimRegistry()
    first = hypothesis()
    second = first.model_copy(
        update={"id": "hyp-claim-2", "statement": "Quality predicts resilience"}
    )
    claims = registry.decompose_paper("paper-academic-1", [first, second])

    assert [claim.id for claim in claims] == ["hyp-claim", "hyp-claim-2"]
    assert all(claim.source_paper_ids == ["paper-academic-1"] for claim in claims)
    assert all(not claim.is_experimentally_validated for claim in claims)

    with pytest.raises(ValueError, match="at least one"):
        registry.decompose_paper("paper-empty", [])
