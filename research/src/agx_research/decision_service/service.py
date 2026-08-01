"""DecisionService: turns promoted knowledge plus position state into a
Buy / Increase Position / Hold / Reduce Position / Exit / No Action label.

Computes one continuous target portfolio weight per ticker (extending
`portfolio.constructor.PortfolioConstructor`'s existing risk-adjusted,
confidence-discounted scoring, not inventing a new formula) and derives
the six-way action by comparing that target to the ticker's current
weight. This is `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md` R5: the six-way
action is a *label* over a continuous number, never the computed
primitive itself -- a discrete lookup table over signal-strength buckets
was tried in `docs/DECISION_EVIDENCE_MATRIX.md` Part 3.4 and rejected
under adversarial review for exactly the combinatorial-growth risk this
design avoids.

Deliberately does **not** implement `docs/DECISION_EVIDENCE_MATRIX.md`'s
31-row Critical/High/Medium/Low evidence weight table (R1): every weight
in that table was an unfalsifiable declared judgment, and this platform's
own `meta.decision_ledger.DecisionLedger` already provides the correct
falsification path (real evaluated outcomes) once enough history exists.
Until then, this service reuses the existing, simple, transparent
`confidence * expected_return / risk`-style scoring `HorizonDecision`
already computes -- extended only by the two hard overrides below, not a
bespoke formula.

Only the INVESTMENT horizon drives an action here, never a blend across
horizons (`AD-35`'s existing rule, and this whole redesign's mission is
long-term EGX investing specifically).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.data.schemas import CorporateEvent
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.decision_service.position import PositionState
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability import Explanation
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_engine import DecisionAction, HorizonDecision, PublicationStatus, Recommendation

_EPS = 1e-9


class PositionAction(str, Enum):
    BUY = "buy"
    INCREASE_POSITION = "increase_position"
    HOLD = "hold"
    REDUCE_POSITION = "reduce_position"
    EXIT = "exit"
    NO_ACTION = "no_action"


class PositionAwareDecision(BaseModel):
    """One ticker's position-aware decision. Never constructed without an
    `Explanation` (Principle 3, same rule every other recommendation-like
    object in this codebase follows).

    Fields cover the full institutional decision memo the mission requires
    (decision, target weight, horizon, confidence, thesis, supporting and
    contradicting evidence, key risks, active catalysts, monitoring events,
    invalidation conditions -- on `explanation` -- and expected review
    date), each derived from data this service already computes or is
    handed, never fabricated.

    `opportunity_score`/`expected_return`/`expected_risk` (Capital
    Allocation Intelligence mission) expose the same
    `HorizonDecision.risk_adjusted_score`/`expected_return`/`expected_risk`
    this method already computes internally as first-class fields, not
    just prose -- `capital_allocation.CapitalAllocationEngine` (and any
    future consumer needing to rank tickers against each other) reads
    these directly instead of re-deriving the eligibility/scoring rule a
    second time. `opportunity_score` is the pre-cap, pre-normalization
    score (0.0 when ineligible/abstained/not publication-ready), exactly
    the `score` this method already used to compute `target_weight`.
    """

    ticker: str
    as_of: date
    action: PositionAction
    target_weight: float
    current_weight: float
    horizon: Horizon
    confidence: float
    opportunity_score: float = 0.0
    expected_return: float | None = None
    expected_risk: float | None = None
    investment_thesis: str
    key_risks: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    active_catalysts: list[str] = Field(default_factory=list)
    monitoring_events: list[str] = Field(default_factory=list)
    expected_review_date: date | None = None
    abstained: bool
    reasons: list[str] = Field(default_factory=list)
    explanation: Explanation
    provenance: Provenance


class DecisionService:
    """Stateless-per-call -- see `decision_service/__init__.py` for why
    this is deliberately not a stage inside the autonomous daily pipeline."""

    def __init__(self, *, max_position_weight: float = 0.25):
        if not 0 < max_position_weight <= 1:
            raise ValueError("max_position_weight must be in (0, 1]")
        self.max_position_weight = max_position_weight

    def decide_portfolio(
        self,
        recommendations: list[Recommendation],
        positions: dict[str, PositionState],
        as_of: date,
        *,
        country_risk: CountryRiskAssessment,
        illiquid_tickers: set[str] | None = None,
        corporate_events: dict[str, list[CorporateEvent]] | None = None,
        knowledge_store: KnowledgeStore | None = None,
    ) -> list[PositionAwareDecision]:
        """Evaluate every ticker with either a fresh recommendation or an
        existing position, together, since portfolio weights must be
        normalized jointly -- exactly the same reason
        `PortfolioConstructor.construct` takes the full recommendation
        list rather than one ticker at a time.

        `corporate_events` (real, already-collected `CorporateEvent`s per
        ticker) drives `active_catalysts`; `knowledge_store` (optional --
        this service stays queryable without one) drives
        `monitoring_events` by looking up which of a decision's own
        evidence references are currently `KnowledgeStatus.MONITORING`.
        Neither is fabricated if omitted -- the corresponding field is
        simply empty, an honest gap rather than an invented one.
        """
        illiquid_tickers = illiquid_tickers or set()
        corporate_events = corporate_events or {}

        scored: dict[str, tuple[float, HorizonDecision | None, Recommendation | None]] = {}
        for rec in recommendations:
            decision = rec.horizon_decisions.get(Horizon.INVESTMENT)
            if decision is None:
                continue
            eligible = (
                decision.action != DecisionAction.ABSTAIN
                and decision.publication_status == PublicationStatus.PUBLICATION_READY
            )
            score = decision.risk_adjusted_score if eligible else 0.0
            scored[rec.ticker] = (score, decision, rec)

        total_positive_score = sum(max(score, 0.0) for score, _, _ in scored.values())

        all_tickers = sorted(set(scored) | {t for t, p in positions.items() if p.held})
        decisions: list[PositionAwareDecision] = []
        for ticker in all_tickers:
            score, decision, rec = scored.get(ticker, (0.0, None, None))
            position = positions.get(ticker, PositionState(ticker=ticker, held=False))
            reasons: list[str] = []

            target_weight = (
                min(
                    max(score, 0.0) / total_positive_score,
                    self.max_position_weight,
                    decision.max_position_pct if decision is not None else self.max_position_weight,
                )
                if total_positive_score > 0 and score > 0
                else 0.0
            )

            if ticker in illiquid_tickers:
                target_weight = 0.0
                reasons.append(
                    "Liquidity floor: insufficient tradable size for this ticker "
                    "(hard override, not weighted evidence)."
                )

            if country_risk.severity == CountryRiskSeverity.CRISIS:
                target_weight = 0.0
                reasons.extend(
                    country_risk.reasons or ["Country-risk override: crisis severity."]
                )

            abstained = False
            if decision is None:
                if position.held:
                    abstained = True
                    reasons.append("No current INVESTMENT-horizon evidence for this held ticker.")
            elif decision.action == DecisionAction.ABSTAIN:
                abstained = True
                reasons.extend(decision.abstention_reasons)
            elif decision.publication_status != PublicationStatus.PUBLICATION_READY:
                # The model itself reached a real action (e.g. BUY_CANDIDATE),
                # but `meta.publication_gate` hasn't cleared it -- target_weight
                # is already zero from the eligibility check above; without this
                # branch the decision would silently report no_action/hold with
                # no reason naming the real cause (Principle 3/Rule 5).
                abstained = True
                reasons.extend(
                    decision.abstention_reasons
                    or ["Not publication-ready; see meta.publication_gate's blockers for the exact reason."]
                )

            action = self._resolve_action(
                position=position, target_weight=target_weight, abstained=abstained
            )
            confidence = decision.confidence if decision is not None else 0.0
            key_risks = self._key_risks(decision, rec, reasons)
            contradicting_evidence = self._contradicting_evidence(decision, rec, country_risk)
            active_catalysts = self._active_catalysts(ticker, as_of, corporate_events)
            monitoring_events = self._monitoring_events(decision, knowledge_store)

            decisions.append(
                PositionAwareDecision(
                    ticker=ticker,
                    as_of=as_of,
                    action=action,
                    target_weight=target_weight,
                    current_weight=position.current_weight,
                    horizon=Horizon.INVESTMENT,
                    confidence=confidence,
                    opportunity_score=max(score, 0.0),
                    expected_return=decision.expected_return if decision is not None else None,
                    expected_risk=decision.expected_risk if decision is not None else None,
                    investment_thesis=self._investment_thesis(
                        ticker, action, target_weight, position, decision
                    ),
                    key_risks=key_risks,
                    contradicting_evidence=contradicting_evidence,
                    active_catalysts=active_catalysts,
                    monitoring_events=monitoring_events,
                    expected_review_date=decision.valid_until if decision is not None else None,
                    abstained=abstained,
                    reasons=reasons,
                    explanation=self._explanation(
                        ticker, action, target_weight, position, reasons, decision
                    ),
                    provenance=Provenance(
                        produced_by="decision_service@1.0.0",
                        produced_at=datetime.now(),
                        inputs=(
                            [ProvenanceRef(kind="recommendation", ref_id=rec.ticker)]
                            if rec is not None
                            else []
                        ),
                    ),
                )
            )
        return decisions

    @staticmethod
    def _resolve_action(
        *, position: PositionState, target_weight: float, abstained: bool
    ) -> PositionAction:
        """The position-state x signal-direction resolution table from
        `docs/DECISION_EVIDENCE_MATRIX.md` Part 3.4, implemented as a
        direct comparison rather than a lookup table (R5)."""
        if abstained:
            return PositionAction.HOLD if position.held else PositionAction.NO_ACTION
        if position.held:
            if target_weight <= _EPS:
                return PositionAction.EXIT
            if target_weight > position.current_weight + _EPS:
                return PositionAction.INCREASE_POSITION
            if target_weight < position.current_weight - _EPS:
                return PositionAction.REDUCE_POSITION
            return PositionAction.HOLD
        return PositionAction.BUY if target_weight > _EPS else PositionAction.NO_ACTION

    @staticmethod
    def _explanation(
        ticker: str,
        action: PositionAction,
        target_weight: float,
        position: PositionState,
        reasons: list[str],
        decision: HorizonDecision | None,
    ) -> Explanation:
        supporting_evidence = list(reasons)
        if decision is not None:
            supporting_evidence.append(
                f"expected_return={decision.expected_return:.4f}, "
                f"expected_risk={decision.expected_risk:.4f}, "
                f"confidence={decision.confidence:.2f}"
            )
        return Explanation(
            why_this_stock=(
                f"{ticker}: {action.value.replace('_', ' ')} -- target weight "
                f"{target_weight:.3f} vs. current {position.current_weight:.3f}."
            ),
            why_now="Based on the latest INVESTMENT-horizon evidence and position state as of this query.",
            why_not_others=(
                "This service evaluates every ticker with evidence or an existing position "
                "together, since target weights are normalized jointly; a ticker with no "
                "positive risk-adjusted evidence and no existing position receives No Action, "
                "never a fabricated Buy."
            ),
            supporting_evidence=supporting_evidence,
            evidence_refs=list(decision.evidence_refs) if decision is not None else [],
            similar_historical_cases=[],
            invalidation_conditions=(
                list(decision.invalidation_conditions) if decision is not None else []
            ),
        )

    @staticmethod
    def _investment_thesis(
        ticker: str,
        action: PositionAction,
        target_weight: float,
        position: PositionState,
        decision: HorizonDecision | None,
    ) -> str:
        """One deterministic sentence built only from this decision's own
        already-computed numbers -- never a separately-fabricated summary."""
        if decision is None:
            return (
                f"{ticker}: {action.value.replace('_', ' ')} -- no current INVESTMENT-horizon "
                "evidence exists for this ticker."
            )
        return (
            f"{ticker}: {action.value.replace('_', ' ')} to target weight {target_weight:.2%} "
            f"(from {position.current_weight:.2%}). INVESTMENT-horizon model expects "
            f"{decision.expected_return:+.2%} return at {decision.expected_risk:.2%} risk over "
            f"{decision.horizon_window}, confidence {decision.confidence:.2f}, backed by "
            f"{len(decision.evidence_refs)} evidence reference(s)."
        )

    @staticmethod
    def _key_risks(
        decision: HorizonDecision | None,
        rec: Recommendation | None,
        reasons: list[str],
    ) -> list[str]:
        """Structural threats to this decision -- the risk this thesis is
        already known to carry, distinct from `contradicting_evidence`
        (evidence actively arguing against the thesis right now)."""
        risks: list[str] = []
        if decision is not None:
            risks.append(
                f"Model-estimated risk ({decision.risk_metric}) for this horizon: "
                f"{decision.expected_risk:.2%}."
            )
        if rec is not None:
            for horizon, sibling in rec.horizon_decisions.items():
                if horizon == Horizon.INVESTMENT:
                    continue
                if sibling.action == DecisionAction.AVOID:
                    risks.append(
                        f"{horizon.value.title()}-horizon model signals AVOID "
                        f"(expected_return={sibling.expected_return:+.2%})."
                    )
        for reason in reasons:
            if reason not in risks:
                risks.append(reason)
        return risks

    @staticmethod
    def _contradicting_evidence(
        decision: HorizonDecision | None,
        rec: Recommendation | None,
        country_risk: CountryRiskAssessment,
    ) -> list[str]:
        """Real evidence that disagrees with this thesis right now -- a
        disagreeing sibling horizon or an active country-risk finding --
        never a restatement of `invalidation_conditions` (hypothetical
        future conditions), which is a distinct field."""
        contradicting: list[str] = []
        if rec is not None:
            for horizon, sibling in rec.horizon_decisions.items():
                if horizon == Horizon.INVESTMENT:
                    continue
                if sibling.expected_return < 0 or sibling.action == DecisionAction.AVOID:
                    contradicting.append(
                        f"{horizon.value.title()}-horizon model expects "
                        f"{sibling.expected_return:+.2%} return (confidence "
                        f"{sibling.confidence:.2f}), disagreeing with the INVESTMENT-horizon "
                        "thesis."
                    )
        if country_risk.severity != CountryRiskSeverity.NORMAL:
            contradicting.extend(country_risk.reasons)
        return contradicting

    @staticmethod
    def _active_catalysts(
        ticker: str,
        as_of: date,
        corporate_events: dict[str, list[CorporateEvent]],
    ) -> list[str]:
        """Real, already-collected upcoming `CorporateEvent`s for this
        ticker -- the same event source `OpportunityCenter`'s "Upcoming
        Catalysts" panel already reads, never a separately-derived guess."""
        upcoming = sorted(
            (event for event in corporate_events.get(ticker, []) if event.event_date >= as_of),
            key=lambda event: event.event_date,
        )[:5]
        return [f"{event.event_date.isoformat()}: {event.event_type} -- {event.description}" for event in upcoming]

    @staticmethod
    def _monitoring_events(
        decision: HorizonDecision | None,
        knowledge_store: KnowledgeStore | None,
    ) -> list[str]:
        """Which of this decision's own supporting knowledge objects are
        currently in `KnowledgeStatus.MONITORING` -- real continuous-
        learning state, not a generic reminder to "keep watching"."""
        if decision is None or knowledge_store is None:
            return []
        monitoring: list[str] = []
        seen: set[str] = set()
        for ref in decision.evidence_refs:
            if ref.kind != "knowledge" or ref.ref_id in seen:
                continue
            seen.add(ref.ref_id)
            knowledge = knowledge_store.latest(ref.ref_id)
            if knowledge is not None and knowledge.status == KnowledgeStatus.MONITORING:
                monitoring.append(
                    f"{knowledge.id}: {knowledge.economic_explanation} "
                    f"(confidence={knowledge.confidence:.2f}, status=monitoring)."
                )
        return monitoring
