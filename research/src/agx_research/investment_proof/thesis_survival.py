"""Phase 6: Investment Thesis Survival.

A thesis is not proven by being issued -- it's proven by surviving. This
engine compares the `PositionAwareDecision` a thesis was originally formed
from against a later re-evaluation of the *same* ticker and reports,
mechanically (never fabricated):

- **Broken assumptions**: knowledge objects the original thesis cited as
  evidence (`explanation.evidence_refs`, `kind == "knowledge"`) that
  `KnowledgeStore` now reports `RETIRED` -- looked up for real via
  `KnowledgeStore.latest()`, never assumed.
- **New contradicting evidence**: entries in the current decision's
  `contradicting_evidence` that weren't present originally.
- **Catalyst status**: which of the original `active_catalysts` are still
  active now (`remaining_catalysts`) versus fired or expired
  (`lapsed_catalysts`).
- **Review-date discipline**: whether `as_of` has passed the original
  `expected_review_date` without a re-evaluation happening.

`thesis_health` is a plain, mechanical label derived from these facts --
never a learned or historically-calibrated score, since no real multi-year
EGX decision history exists yet to calibrate one against (see
`docs/PHASE_STATUS.md`'s Investment Proof Framework entry).
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.decision_service.service import PositionAction, PositionAwareDecision
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.store import KnowledgeStore


class ThesisStatus(str, Enum):
    ALIVE = "alive"
    WEAKENING = "weakening"
    BROKEN = "broken"
    EXPIRED = "expired"


class BrokenAssumption(BaseModel):
    knowledge_id: str
    retirement_reason: str | None = None


class ThesisSurvivalReport(BaseModel):
    ticker: str
    formed_at: date
    as_of: date
    days_elapsed: int
    status: ThesisStatus
    thesis_health: str
    original_thesis: str
    current_thesis: str | None = None
    current_action: PositionAction | None = None
    broken_assumptions: list[BrokenAssumption] = Field(default_factory=list)
    new_contradicting_evidence: list[str] = Field(default_factory=list)
    remaining_catalysts: list[str] = Field(default_factory=list)
    lapsed_catalysts: list[str] = Field(default_factory=list)
    review_date_passed: bool = False
    notes: list[str] = Field(default_factory=list)


class ThesisSurvivalEngine:
    def assess(
        self,
        original: PositionAwareDecision,
        current: PositionAwareDecision | None,
        knowledge_store: KnowledgeStore,
        as_of: date,
    ) -> ThesisSurvivalReport:
        """`current` is the same ticker's freshly recomputed decision as of
        `as_of` -- `None` if the ticker is no longer eligible for evaluation
        at all (e.g. delisted from the universe), which is itself a real
        thesis-survival fact, not an error.
        """
        knowledge_ids = {
            ref.ref_id for ref in original.explanation.evidence_refs if ref.kind == "knowledge"
        }
        broken_assumptions = []
        for knowledge_id in sorted(knowledge_ids):
            knowledge = knowledge_store.latest(knowledge_id)
            if knowledge is not None and knowledge.status == KnowledgeStatus.RETIRED:
                broken_assumptions.append(
                    BrokenAssumption(knowledge_id=knowledge_id, retirement_reason=knowledge.retirement_reason)
                )

        review_date_passed = original.expected_review_date is not None and as_of > original.expected_review_date

        if current is None:
            return ThesisSurvivalReport(
                ticker=original.ticker,
                formed_at=original.as_of,
                as_of=as_of,
                days_elapsed=(as_of - original.as_of).days,
                status=ThesisStatus.EXPIRED,
                thesis_health="no_longer_evaluated",
                original_thesis=original.investment_thesis,
                broken_assumptions=broken_assumptions,
                review_date_passed=review_date_passed,
                notes=[f"{original.ticker} is no longer produced by a fresh re-evaluation as of {as_of.isoformat()}."],
            )

        new_contradicting = sorted(set(current.contradicting_evidence) - set(original.contradicting_evidence))
        remaining_catalysts = sorted(set(original.active_catalysts) & set(current.active_catalysts))
        lapsed_catalysts = sorted(set(original.active_catalysts) - set(current.active_catalysts))

        if broken_assumptions and current.action in (PositionAction.EXIT, PositionAction.REDUCE_POSITION):
            status = ThesisStatus.BROKEN
            health = "failed"
        elif broken_assumptions or new_contradicting:
            status = ThesisStatus.WEAKENING
            health = "deteriorating"
        elif review_date_passed:
            status = ThesisStatus.WEAKENING
            health = "overdue_for_review"
        else:
            status = ThesisStatus.ALIVE
            health = "healthy"

        return ThesisSurvivalReport(
            ticker=original.ticker,
            formed_at=original.as_of,
            as_of=as_of,
            days_elapsed=(as_of - original.as_of).days,
            status=status,
            thesis_health=health,
            original_thesis=original.investment_thesis,
            current_thesis=current.investment_thesis,
            current_action=current.action,
            broken_assumptions=broken_assumptions,
            new_contradicting_evidence=new_contradicting,
            remaining_catalysts=remaining_catalysts,
            lapsed_catalysts=lapsed_catalysts,
            review_date_passed=review_date_passed,
        )


__all__ = ["BrokenAssumption", "ThesisStatus", "ThesisSurvivalEngine", "ThesisSurvivalReport"]
