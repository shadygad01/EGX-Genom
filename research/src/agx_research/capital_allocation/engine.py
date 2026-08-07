"""CapitalAllocationEngine: turns a list of independently-labeled
`PositionAwareDecision`s into one explicit, relative capital-allocation
plan.

The matching algorithm (`_match_capital_flows`) is deterministic
bookkeeping, not a fresh optimization: it never changes any
`target_weight`/`current_weight` `DecisionService` already computed, it
only *attributes* each unit of requested capital to a source (idle cash,
or a specific lower-ranked holding being reduced/exited) and each unit of
released capital to a destination (a specific higher-ranked demander, or
back to cash). Demand is walked best-ranked first; supply is walked
weakest-ranked first -- capital funds the strongest ideas before touching
the weakest ones, and the weakest holdings are displaced before the
strongest ones. Idle cash is drawn before any holding is displaced, so a
holding is only ever named as a capital source when idle cash genuinely
was not enough -- this engine never fabricates a "should this replace
another investment" conflict where none exists.
"""

from __future__ import annotations

from datetime import date, datetime

from agx_research.capital_allocation.models import (
    AllocationChange,
    CapitalAllocationPlan,
    CapitalFlow,
    CapitalQueueEntry,
    CapitalRelease,
    CapitalSource,
    CashWaiting,
    OpportunityCostHighlight,
    RankedOpportunity,
)
from agx_research.decision_service.service import PositionAwareDecision
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability import Explanation

_EPS = 1e-9
_HIGHLIGHT_LIMIT = 5


def _effective_target(decision: PositionAwareDecision) -> float:
    """The target weight to use for every capital-flow computation.

    `DecisionService.decide_portfolio()` deliberately labels an abstained
    held ticker `hold` (not `exit`) precisely so an evidence *gap* is never
    read as a call to sell -- but it still reports `target_weight=0.0` for
    that ticker (the score behind it is 0, since there's no fresh evidence
    to score). Treating that raw 0.0 as a real capital release would
    fabricate a "sell to fund something better" movement nothing actually
    recommends. This engine follows the same discipline `decide_portfolio`
    already applies: an abstention leaves capital exactly where it is.
    """
    return decision.current_weight if decision.abstained else decision.target_weight


class CapitalAllocationEngine:
    """Stateless -- see `capital_allocation/__init__.py` for why this is
    deliberately not a stage inside the autonomous daily pipeline."""

    def build(self, decisions: list[PositionAwareDecision], as_of: date) -> CapitalAllocationPlan:
        ranking = self._rank(decisions)
        rank_by_ticker = {r.ticker: r.rank for r in ranking}
        flows = self._match_capital_flows(decisions, rank_by_ticker)

        demanders = sorted(
            (d for d in decisions if _effective_target(d) - d.current_weight > _EPS),
            key=lambda d: rank_by_ticker[d.ticker],
        )
        rejected = [r for r in ranking if r.opportunity_score > _EPS and r.target_weight <= _EPS]

        queue = [self._queue_entry(d, rank_by_ticker[d.ticker], flows, rejected) for d in demanders]
        releases = self._releases(decisions, flows)
        recycled = [f for f in flows if f.from_ticker is not None and f.to_ticker is not None]
        best_new = [r for r in ranking if r.is_new_position][:_HIGHLIGHT_LIMIT]
        highest_cost = [
            OpportunityCostHighlight(
                ticker=r.ticker,
                opportunity_score=r.opportunity_score,
                reason=(
                    "Positive, publication-ready risk-adjusted evidence exists but no capital "
                    "was allocated -- outranked by higher-scoring ideas under today's capital "
                    "budget."
                ),
            )
            for r in rejected[:_HIGHLIGHT_LIMIT]
        ]
        allocation_changes = self._allocation_changes(decisions)
        cash_waiting = self._cash_waiting(decisions)

        explanation = Explanation(
            why_this_stock=(
                f"{len(ranking)} ticker(s) evaluated together for the same capital budget: "
                f"{len(queue)} funded (buy/increase), {len(releases)} releasing capital "
                f"(reduce/exit), {cash_waiting.idle_cash_after:.2%} of the portfolio left in cash."
            ),
            why_now=(
                f"Computed as of {as_of.isoformat()} from the same jointly-normalized, "
                "position-aware decisions DecisionService already produced -- no independent "
                "scoring happens here."
            ),
            why_not_others=(
                "Every ticker with a Recommendation or an existing position competes for the "
                "same capital in one pass; a ticker is funded only if it outranks every "
                "lower-scoring alternative and idle cash under the current budget."
            ),
            supporting_evidence=[
                f"{r.ticker}: rank {r.rank}/{len(ranking)}, opportunity_score={r.opportunity_score:.4f}"
                for r in ranking[:10]
            ],
            evidence_refs=[ProvenanceRef(kind="decision", ref_id=d.ticker) for d in decisions],
            invalidation_conditions=[
                "Any underlying PositionAwareDecision changes (new evidence, publication gate "
                "status, or position state).",
            ],
        )

        return CapitalAllocationPlan(
            as_of=as_of,
            ranking=ranking,
            queue=queue,
            capital_released_today=releases,
            capital_recycled=recycled,
            best_new_opportunities=best_new,
            highest_opportunity_cost=highest_cost,
            allocation_changes=allocation_changes,
            cash_waiting=cash_waiting,
            explanation=explanation,
            provenance=Provenance(
                produced_by="capital_allocation_engine@1.0.0",
                produced_at=datetime.now(),
                inputs=[ProvenanceRef(kind="decision", ref_id=d.ticker) for d in decisions],
            ),
        )

    @staticmethod
    def _rank(decisions: list[PositionAwareDecision]) -> list[RankedOpportunity]:
        ordered = sorted(decisions, key=lambda d: (-d.opportunity_score, d.ticker))
        return [
            RankedOpportunity(
                rank=i,
                ticker=d.ticker,
                opportunity_score=d.opportunity_score,
                action=d.action,
                target_weight=d.target_weight,
                current_weight=d.current_weight,
                confidence=d.confidence,
                expected_return=d.expected_return,
                expected_risk=d.expected_risk,
                sector=d.sector,
                is_new_position=d.current_weight <= _EPS and d.target_weight > _EPS,
            )
            for i, d in enumerate(ordered, start=1)
        ]

    @staticmethod
    def _match_capital_flows(
        decisions: list[PositionAwareDecision], rank_by_ticker: dict[str, int]
    ) -> list[CapitalFlow]:
        demanders = sorted(
            (d for d in decisions if _effective_target(d) - d.current_weight > _EPS),
            key=lambda d: rank_by_ticker[d.ticker],
        )
        # Weakest-ranked releaser first: the least attractive holding is
        # displaced before a stronger one ever would be.
        suppliers = sorted(
            (
                {"ticker": d.ticker, "remaining": d.current_weight - _effective_target(d)}
                for d in decisions
                if d.current_weight - _effective_target(d) > _EPS
            ),
            key=lambda s: -rank_by_ticker[s["ticker"]],
        )
        cash_pool = max(0.0, 1.0 - sum(d.current_weight for d in decisions))

        flows: list[CapitalFlow] = []
        supplier_idx = 0
        for demander in demanders:
            need = _effective_target(demander) - demander.current_weight
            if need > _EPS and cash_pool > _EPS:
                draw = min(need, cash_pool)
                flows.append(CapitalFlow(from_ticker=None, to_ticker=demander.ticker, amount=draw))
                cash_pool -= draw
                need -= draw
            while need > _EPS and supplier_idx < len(suppliers):
                supplier = suppliers[supplier_idx]
                if supplier["remaining"] <= _EPS:
                    supplier_idx += 1
                    continue
                draw = min(need, supplier["remaining"])
                flows.append(
                    CapitalFlow(from_ticker=supplier["ticker"], to_ticker=demander.ticker, amount=draw)
                )
                supplier["remaining"] -= draw
                need -= draw
                if supplier["remaining"] <= _EPS:
                    supplier_idx += 1
            # Any `need` still unmet here is a rounding/consistency gap that
            # should not occur -- DecisionService's own joint normalization
            # guarantees total demand never exceeds idle cash plus released
            # supply. Left unattributed rather than inventing a source.

        for supplier in suppliers[supplier_idx:]:
            if supplier["remaining"] > _EPS:
                flows.append(CapitalFlow(from_ticker=supplier["ticker"], to_ticker=None, amount=supplier["remaining"]))

        return flows

    @staticmethod
    def _queue_entry(
        decision: PositionAwareDecision,
        rank: int,
        flows: list[CapitalFlow],
        rejected: list[RankedOpportunity],
    ) -> CapitalQueueEntry:
        sources = [
            CapitalSource(ticker=f.from_ticker, amount=f.amount)
            for f in flows
            if f.to_ticker == decision.ticker
        ]
        target = _effective_target(decision)
        capital_delta = target - decision.current_weight
        expected_contribution = (
            capital_delta * decision.expected_return if decision.expected_return is not None else None
        )
        best_rejected = next((r for r in rejected if r.ticker != decision.ticker), None)
        source_text = (
            ", ".join(
                f"{'idle cash' if s.ticker is None else s.ticker}: {s.amount:.2%}" for s in sources
            )
            or "no capital drawn"
        )
        opportunity_cost_note = (
            f"Next-best-ranked idea currently without capital: {best_rejected.ticker} "
            f"(opportunity_score={best_rejected.opportunity_score:.3f})."
            if best_rejected is not None
            else "Every ticker with a positive opportunity score is already funded; no rejected alternative exists today."
        )
        required_action = (
            f"{decision.action.value.replace('_', ' ').title()} {decision.ticker} to "
            f"{target:.2%} (from {decision.current_weight:.2%}), funded by {source_text}."
        )
        return CapitalQueueEntry(
            ticker=decision.ticker,
            priority=rank,
            action=decision.action,
            target_weight=target,
            current_weight=decision.current_weight,
            capital_delta=capital_delta,
            expected_contribution=expected_contribution,
            marginal_benefit=decision.opportunity_score,
            marginal_risk=decision.expected_risk,
            confidence=decision.confidence,
            sector=decision.sector,
            capital_sources=sources,
            required_action=required_action,
            opportunity_cost_note=opportunity_cost_note,
            reasoning=CapitalAllocationEngine._reasoning(decision, rank, sources),
        )

    @staticmethod
    def _reasoning(
        decision: PositionAwareDecision, rank: int, sources: list[CapitalSource]
    ) -> list[str]:
        """Full transparent explanation for one queue entry -- built only
        from fields `DecisionService.decide_portfolio()` already computed
        (expected return/risk/confidence, and any liquidity/country/
        sector/correlation/macro override reason it recorded), never a
        fresh scoring judgment made in this engine."""
        parts = [
            f"Rank {rank}: opportunity_score={decision.opportunity_score:.4f}, "
            f"confidence={decision.confidence:.2f}.",
        ]
        if decision.expected_return is not None:
            parts.append(f"Expected return: {decision.expected_return:+.2%}.")
        if decision.expected_risk is not None:
            parts.append(f"Expected risk: {decision.expected_risk:.2%}.")
        if decision.sector is not None:
            parts.append(f"Sector: {decision.sector}.")
        parts.extend(decision.reasons)
        if not sources and decision.target_weight - decision.current_weight > _EPS:
            parts.append("No capital was drawn despite a positive target -- see reasons above.")
        return parts

    @staticmethod
    def _releases(
        decisions: list[PositionAwareDecision], flows: list[CapitalFlow]
    ) -> list[CapitalRelease]:
        releases: list[CapitalRelease] = []
        for d in decisions:
            amount = d.current_weight - _effective_target(d)
            if amount <= _EPS:
                continue
            destinations = [
                CapitalSource(ticker=f.to_ticker, amount=f.amount)
                for f in flows
                if f.from_ticker == d.ticker
            ]
            releases.append(CapitalRelease(ticker=d.ticker, amount=amount, destinations=destinations))
        return releases

    @staticmethod
    def _allocation_changes(decisions: list[PositionAwareDecision]) -> list[AllocationChange]:
        changes = [
            AllocationChange(
                ticker=d.ticker,
                action=d.action,
                current_weight=d.current_weight,
                target_weight=_effective_target(d),
                capital_delta=_effective_target(d) - d.current_weight,
            )
            for d in decisions
            if abs(_effective_target(d) - d.current_weight) > _EPS
        ]
        changes.sort(key=lambda c: -abs(c.capital_delta))
        return changes

    @staticmethod
    def _cash_waiting(decisions: list[PositionAwareDecision]) -> CashWaiting:
        idle_before = max(0.0, 1.0 - sum(d.current_weight for d in decisions))
        idle_after = max(0.0, 1.0 - sum(_effective_target(d) for d in decisions))
        reason = (
            "All available capital is deployed to the highest-ranked opportunities."
            if idle_after <= _EPS
            else (
                "No additional ticker currently clears a positive, publication-ready "
                "risk-adjusted score large enough to absorb this capital -- it stays in cash "
                "rather than being forced into a weaker idea."
            )
        )
        return CashWaiting(idle_cash_before=idle_before, idle_cash_after=idle_after, reason=reason)
