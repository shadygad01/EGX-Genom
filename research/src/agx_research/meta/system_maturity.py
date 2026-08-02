"""System Maturity: a visible, non-blocking credibility indicator.

Project owner direction (2026-08-02): historical performance should
continuously inform how much confidence the methodology has earned, but
must never gate whether a decision can publish -- that is
`meta.decision_quality`'s job, evaluated per decision. This module only
ever *labels* the system's track record; nothing here ever prevents a
`Recommendation` from reaching `PublicationStatus.PUBLICATION_READY`.

Five levels, each a strictly higher bar than the last, reusing exactly
the same `DecisionPerformanceSummary` fields the old (now-removed)
performance-based publication blocker used -- the math is the same real
math, only its consequence changed from "block everything" to "report
honestly":

- EARLY: fewer than 10 benchmark-evaluated decisions in any horizon --
  too little real outcome data to say anything about credibility yet.
- VALIDATING: at least 10 evaluated in some horizon, but fewer than the
  30-result floor `DecisionPerformanceSummary.sample_status` itself uses
  to call a sample "sufficient" for at least one horizon.
- DEVELOPING: every horizon has reached the 30-result floor, but not
  every horizon shows a statistically positive result (mean/median excess
  return and its 95%-lower-bound all above zero) -- real history exists,
  the verdict is still mixed.
- ESTABLISHED: every horizon has reached the 30-result floor *and* shows
  a statistically positive excess return at the 95% lower bound -- the
  exact bar the old publication gate demanded before allowing anything to
  publish; here it only earns a label.
- VERIFIED: ESTABLISHED, plus an optional human governance review
  (`meta.publication_gate.LegalPublicationApproval`, decoupled from
  publishing here) has been explicitly supplied and is currently valid.
  Never claimed without one -- "verified" implies a human actually
  checked, which nothing in this codebase may assert on its own.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel

from agx_research.config import Horizon
from agx_research.meta.decision_ledger import DecisionPerformanceSummary
from agx_research.meta.publication_gate import LegalPublicationApproval

MIN_EVALUATED_FOR_VALIDATING = 10
MIN_EVALUATED_FOR_SIGNIFICANCE = 30


class SystemMaturityLevel(str, Enum):
    EARLY = "early"
    VALIDATING = "validating"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    VERIFIED = "verified"


class SystemMaturityReport(BaseModel):
    as_of: date
    level: SystemMaturityLevel
    rationale: str
    horizons_meeting_significance_floor: int
    total_horizons: int
    min_evaluated_across_horizons: int
    governance_reviewed: bool = False


def _significant_and_positive(summary: DecisionPerformanceSummary | None) -> bool:
    return bool(
        summary
        and summary.benchmark_evaluated >= MIN_EVALUATED_FOR_SIGNIFICANCE
        and summary.mean_excess_return is not None and summary.mean_excess_return > 0
        and summary.median_excess_return is not None and summary.median_excess_return > 0
        and summary.excess_return_lower_95 is not None and summary.excess_return_lower_95 > 0
    )


def compute_system_maturity(
    performance: list[DecisionPerformanceSummary],
    *,
    as_of: date,
    governance: LegalPublicationApproval | None = None,
) -> SystemMaturityReport:
    by_horizon = {row.horizon: row for row in performance}
    evaluated_counts = [by_horizon.get(horizon).benchmark_evaluated if by_horizon.get(horizon) else 0
                         for horizon in Horizon]
    min_evaluated = min(evaluated_counts) if evaluated_counts else 0
    significant_horizons = sum(1 for horizon in Horizon if _significant_and_positive(by_horizon.get(horizon)))
    total_horizons = len(list(Horizon))

    governance_reviewed = bool(
        governance
        and governance.reviewer.strip()
        and governance.scope.strip()
        and governance.conflicts_disclosed
        and governance.methodology_approved
        and governance.approved_at.date() <= as_of <= governance.expires_at
    )

    if significant_horizons == total_horizons and governance_reviewed:
        level = SystemMaturityLevel.VERIFIED
        rationale = (
            f"All {total_horizons} horizons show a statistically positive track record "
            f"(30+ results, positive 95%-lower-bound excess return) and a valid human "
            f"governance review is on file."
        )
    elif significant_horizons == total_horizons:
        level = SystemMaturityLevel.ESTABLISHED
        rationale = (
            f"All {total_horizons} horizons show a statistically positive track record "
            f"(30+ results, positive 95%-lower-bound excess return); no governance review is on file yet."
        )
    elif min_evaluated >= MIN_EVALUATED_FOR_SIGNIFICANCE:
        level = SystemMaturityLevel.DEVELOPING
        rationale = (
            f"Every horizon has reached {MIN_EVALUATED_FOR_SIGNIFICANCE}+ benchmark-evaluated "
            f"decisions, but only {significant_horizons}/{total_horizons} show a statistically "
            "positive result -- real history exists, the verdict is still mixed."
        )
    elif min_evaluated >= MIN_EVALUATED_FOR_VALIDATING:
        level = SystemMaturityLevel.VALIDATING
        rationale = (
            f"At least {MIN_EVALUATED_FOR_VALIDATING} benchmark-evaluated decisions exist, but "
            f"fewer than {MIN_EVALUATED_FOR_SIGNIFICANCE} in at least one horizon -- too early "
            "for a statistically meaningful verdict."
        )
    else:
        level = SystemMaturityLevel.EARLY
        rationale = (
            f"Fewer than {MIN_EVALUATED_FOR_VALIDATING} benchmark-evaluated decisions exist in "
            "at least one horizon -- not enough real outcome history to assess credibility yet."
        )

    return SystemMaturityReport(
        as_of=as_of,
        level=level,
        rationale=rationale,
        horizons_meeting_significance_floor=significant_horizons,
        total_horizons=total_horizons,
        min_evaluated_across_horizons=min_evaluated,
        governance_reviewed=governance_reviewed,
    )
