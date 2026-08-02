"""Decision Quality Gate: is *this specific* decision complete, evidenced,
and internally consistent enough to publish -- evaluated per ticker per
horizon, never as one system-wide switch.

This replaces `meta.publication_gate`'s old blocking role (project owner
direction, 2026-08-02): that gate required a human-authored legal-approval
file and 30+ benchmark-outperforming historical results *before any
decision, of any quality, could ever size a position* -- both conditions
this platform had never once satisfied in its history, so every decision
stayed `RESEARCH_ONLY` regardless of how complete or well-evidenced it
was. The project owner's explicit correction: publication should be
governed by decision quality, not by how much track record has
accumulated or whether a human has formally signed off. Those two other
concerns still matter, but as separate, non-blocking layers:

- `meta.system_maturity` reports historical track record as a visible,
  informational credibility indicator -- it never blocks anything here.
- `meta.publication_gate`'s `LegalPublicationApproval` remains available
  as an optional input to `system_maturity`'s highest tier and to a
  future regulated/officially-published distribution mode -- research-
  mode and personal-use output (this platform's only mode today) is
  never blocked on it.

A decision passes this gate when every one of the following, checkable
directly from data this platform already computes, holds:

1. Evidence is present and non-empty (`Explanation.supporting_evidence`/
   `evidence_refs`) -- every conclusion must be traceable to something.
2. The investment thesis is complete (`why_this_stock`/`why_now`/
   `why_not_others` all stated, not blank placeholders).
3. Confidence was actually calculated (a finite number in [0, 1], not a
   default or NaN slipping through).
4. Invalidation conditions are defined (`HorizonDecision
   .invalidation_conditions` non-empty) -- what would prove this wrong.
5. Monitoring/review conditions are defined (`entry_condition`/
   `review_condition` both real statements, not empty strings).
6. The decision is internally consistent -- a `BUY_CANDIDATE` must carry
   numeric entry and invalidation price levels (an executable decision
   with no executable levels is a contradiction, not a real buy).
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from agx_research.explainability import Explanation
from agx_research.meta.decision_engine import (
    DecisionAction,
    HorizonDecision,
    PublicationStatus,
    Recommendation,
)


class DecisionQualityCheck(BaseModel):
    id: str
    label: str
    passed: bool
    blocker: str | None = None


class DecisionQualityReport(BaseModel):
    ticker: str
    horizon: str
    passed: bool
    checks: list[DecisionQualityCheck] = Field(default_factory=list)


def evaluate_decision_quality(
    ticker: str, decision: HorizonDecision, explanation: Explanation
) -> DecisionQualityReport:
    checks: list[DecisionQualityCheck] = []

    evidence_ok = bool(explanation.supporting_evidence) and bool(explanation.evidence_refs)
    checks.append(DecisionQualityCheck(
        id="evidence_present",
        label="Supporting evidence is present and traceable",
        passed=evidence_ok,
        blocker=None if evidence_ok else "No supporting evidence or evidence references attached.",
    ))

    thesis_ok = bool(
        explanation.why_this_stock.strip()
        and explanation.why_now.strip()
        and explanation.why_not_others.strip()
    )
    checks.append(DecisionQualityCheck(
        id="thesis_complete",
        label="Investment thesis is complete",
        passed=thesis_ok,
        blocker=None if thesis_ok else "why_this_stock/why_now/why_not_others is blank.",
    ))

    confidence_ok = (
        isinstance(decision.confidence, (int, float))
        and math.isfinite(decision.confidence)
        and 0.0 <= decision.confidence <= 1.0
    )
    checks.append(DecisionQualityCheck(
        id="confidence_calculated",
        label="Confidence was calculated, not defaulted",
        passed=confidence_ok,
        blocker=None if confidence_ok else "Confidence is missing, NaN, or out of [0, 1].",
    ))

    invalidation_ok = bool(decision.invalidation_conditions)
    checks.append(DecisionQualityCheck(
        id="invalidation_defined",
        label="Invalidation conditions are defined",
        passed=invalidation_ok,
        blocker=None if invalidation_ok else "No invalidation condition states what would prove this wrong.",
    ))

    monitoring_ok = bool(decision.entry_condition.strip()) and bool(decision.review_condition.strip())
    checks.append(DecisionQualityCheck(
        id="monitoring_defined",
        label="Entry and review conditions are defined",
        passed=monitoring_ok,
        blocker=None if monitoring_ok else "Entry or review condition is blank.",
    ))

    executable_buy = (
        decision.action != DecisionAction.BUY_CANDIDATE
        or (decision.entry_value is not None and decision.invalidation_value is not None)
    )
    checks.append(DecisionQualityCheck(
        id="internal_consistency",
        label="Decision is internally consistent",
        passed=executable_buy,
        blocker=None if executable_buy else "Buy decision lacks numeric entry and invalidation levels.",
    ))

    return DecisionQualityReport(
        ticker=ticker,
        horizon=decision.horizon.value,
        passed=all(check.passed for check in checks),
        checks=checks,
    )


def apply_decision_quality_gate(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Evaluate and apply the quality gate per ticker per horizon -- the
    direct replacement for the old, system-wide `apply_publication_gate`.
    No external report is needed: each decision's own explanation and
    prediction already carry everything this gate checks.
    """
    output = [item.model_copy(deep=True) for item in recommendations]
    for recommendation in output:
        for horizon, decision in recommendation.horizon_decisions.items():
            prediction = recommendation.horizon_predictions.get(horizon)
            explanation = prediction.explanation if prediction is not None else recommendation.explanation
            report = evaluate_decision_quality(recommendation.ticker, decision, explanation)
            decision.publication_status = (
                PublicationStatus.PUBLICATION_READY
                if report.passed and decision.action != DecisionAction.ABSTAIN
                else PublicationStatus.RESEARCH_ONLY
            )
            decision.max_position_pct = (
                min(0.05, max(0.01, decision.confidence * 0.05))
                if decision.publication_status == PublicationStatus.PUBLICATION_READY
                and decision.action == DecisionAction.BUY_CANDIDATE
                else 0.0
            )
            if not report.passed:
                for check in report.checks:
                    if check.blocker and check.blocker not in decision.abstention_reasons:
                        decision.abstention_reasons.append(check.blocker)
    return output
