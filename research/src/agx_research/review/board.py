"""The Scientific Review Board: no discovery enters production automatically.

`ScientificReviewBoard.review()` runs every configured reviewer and
approves only if every reviewer that actually ran passed. Reviewers still
raising `NotImplementedError` (see `reviewers.py`) are skipped rather than
treated as automatic failures or passes — "requires passing all reviewers"
means all reviewers actually run, not that unimplemented roles silently
count as passed. A board with zero working reviewers can never approve
anything, by construction.

This runs *before* `KnowledgeStore.promote()` in the intended production
flow. It does not change `promote()`'s signature — existing direct callers
and tests are unaffected; new code should call the board first and only
promote on `BoardDecision.approved`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agx_research.causal.assessment import CausalAssessment
from agx_research.hypotheses.experiment import ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis
from agx_research.review.candidate import PromotionCandidate
from agx_research.review.reviewer import Reviewer, ReviewReport


class BoardDecision(BaseModel):
    approved: bool
    reports: list[ReviewReport] = Field(default_factory=list)
    notes: str = ""


class ScientificReviewBoard:
    def __init__(self, reviewers: list[Reviewer]):
        self.reviewers = reviewers

    def review(
        self,
        *,
        hypothesis: Hypothesis,
        candidate: PromotionCandidate,
        experiment_results: dict[str, ExperimentResult],
        causal_assessment: CausalAssessment | None = None,
    ) -> BoardDecision:
        reports: list[ReviewReport] = []
        for reviewer in self.reviewers:
            try:
                reports.append(
                    reviewer.review(
                        hypothesis=hypothesis,
                        candidate=candidate,
                        experiment_results=experiment_results,
                        causal_assessment=causal_assessment,
                    )
                )
            except NotImplementedError:
                continue

        approved = bool(reports) and all(report.passed for report in reports)
        return BoardDecision(
            approved=approved,
            reports=reports,
            notes=(
                ""
                if approved
                else "No reviewers ran." if not reports else "One or more reviewers rejected the candidate."
            ),
        )
