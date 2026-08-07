"""Pydantic models for the Capital Allocation Intelligence engine.

Every model here is a derived view over `PositionAwareDecision` fields the
engine already received -- nothing is a fresh judgment call, only
bookkeeping/narrative over numbers `decision_service` already computed.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.decision_service.service import PositionAction
from agx_research.domain.provenance import Provenance
from agx_research.explainability import Explanation


class RankedOpportunity(BaseModel):
    """Where one ticker stands against every other ticker competing for the
    same capital -- the Global Opportunity Ranking. Includes every ticker
    `DecisionService` evaluated, not only the funded ones, so a real
    rejected opportunity is visible, not silently dropped."""

    rank: int
    ticker: str
    opportunity_score: float
    action: PositionAction
    target_weight: float
    current_weight: float
    confidence: float
    expected_return: float | None = None
    expected_risk: float | None = None
    sector: str | None = None
    is_new_position: bool


class CapitalSource(BaseModel):
    """One unit of capital funding a queue entry. `ticker=None` means
    unallocated cash rather than a displaced holding."""

    ticker: str | None = None
    amount: float


class CapitalFlow(BaseModel):
    """One matched movement of capital from a supplier to a demander.
    `from_ticker=None` means the capital came from idle cash;
    `to_ticker=None` means released capital returned to cash rather than
    funding anything today."""

    from_ticker: str | None = None
    to_ticker: str | None = None
    amount: float


class CapitalQueueEntry(BaseModel):
    """One proposal requesting capital, ranked against every other
    proposal -- the Capital Deployment Queue. `capital_sources` and
    `opportunity_cost_note` are what make the underlying action answer
    "better than what?" and "funded by what?" instead of a bare BUY/
    INCREASE label. `reasoning` (AD-66) is the full transparent
    explanation for this entry's rank and sizing -- expected return,
    marginal risk, confidence, and, when they applied, the exact
    liquidity/country/sector/correlation/macro overrides
    `DecisionService.decide_portfolio()` computed for this ticker --
    assembled entirely from that decision's own already-computed fields,
    never a fresh judgment made here."""

    ticker: str
    priority: int
    action: PositionAction
    target_weight: float
    current_weight: float
    capital_delta: float
    expected_contribution: float | None = None
    marginal_benefit: float
    marginal_risk: float | None = None
    confidence: float
    sector: str | None = None
    capital_sources: list[CapitalSource] = Field(default_factory=list)
    required_action: str
    opportunity_cost_note: str
    reasoning: list[str] = Field(default_factory=list)


class CapitalRelease(BaseModel):
    """One ticker whose allocation shrank today -- Capital Released Today.
    `destinations` names exactly which demander(s) (or cash) absorbed it,
    answering "replace with what?" for every REDUCE/EXIT."""

    ticker: str
    amount: float
    destinations: list[CapitalSource] = Field(default_factory=list)


class OpportunityCostHighlight(BaseModel):
    """A real, evidence-backed opportunity that received zero capital
    today because a higher-ranked idea claimed the budget first --
    Highest Opportunity Cost."""

    ticker: str
    opportunity_score: float
    reason: str


class AllocationChange(BaseModel):
    """Any ticker whose target weight differs from its current weight
    today -- the union of the queue and the releases, one flat list for
    an at-a-glance "what moved" view."""

    ticker: str
    action: PositionAction
    current_weight: float
    target_weight: float
    capital_delta: float


class CashWaiting(BaseModel):
    """Capital deliberately left unallocated rather than forced into a
    weaker idea -- Capital Waiting For Better Opportunities."""

    idle_cash_before: float
    idle_cash_after: float
    reason: str


class CapitalAllocationPlan(BaseModel):
    """The full institutional capital-allocation view for one `as_of`
    date: every opportunity ranked together, the deployment queue, the
    recycling ledger, and the honest leftover-cash accounting. Never
    constructed without an `Explanation` (Principle 3, same rule every
    other recommendation-like object in this codebase follows)."""

    as_of: date
    ranking: list[RankedOpportunity] = Field(default_factory=list)
    queue: list[CapitalQueueEntry] = Field(default_factory=list)
    capital_released_today: list[CapitalRelease] = Field(default_factory=list)
    capital_recycled: list[CapitalFlow] = Field(default_factory=list)
    best_new_opportunities: list[RankedOpportunity] = Field(default_factory=list)
    highest_opportunity_cost: list[OpportunityCostHighlight] = Field(default_factory=list)
    allocation_changes: list[AllocationChange] = Field(default_factory=list)
    cash_waiting: CashWaiting
    explanation: Explanation
    provenance: Provenance
