from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance
from agx_research.hypotheses.hypothesis import Hypothesis, StageResult
from agx_research.hypotheses.pipeline import StageName
from agx_research.hypotheses.repository import HypothesisRepository


def make_hypothesis(hyp_id: str) -> Hypothesis:
    return Hypothesis(
        id=hyp_id,
        statement="test",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.MICRO,
        affected_assets=["COMI"],
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )


def test_persists_a_hypothesis_that_never_gets_promoted():
    """A hypothesis that fails its first gate must still be remembered,
    so the same falsified idea isn't silently re-researched later.
    """
    repo = HypothesisRepository()
    hypothesis = make_hypothesis("hyp-fail")
    failed = hypothesis.advance(
        StageResult(stage_name=StageName.OBSERVATION.value, passed=False, evaluated_at=datetime.now())
    )
    repo.add(failed)

    stored = repo.latest("hyp-fail")
    assert stored is not None
    assert not stored.is_ready_for_promotion
    assert stored.stage_history[-1].passed is False


def test_history_tracks_every_gate_transition():
    repo = HypothesisRepository()
    hypothesis = make_hypothesis("hyp-progress")
    repo.add(hypothesis)

    advanced = hypothesis.advance(
        StageResult(stage_name=StageName.OBSERVATION.value, passed=True, evaluated_at=datetime.now())
    )
    repo.add(advanced)

    assert len(repo.history("hyp-progress")) == 2
    assert repo.latest("hyp-progress").version == 2
