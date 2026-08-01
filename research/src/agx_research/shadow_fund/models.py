"""Pydantic models for the Shadow Fund -- the canonical, persistent state
of a continuously managed virtual institutional portfolio that owns the
evolving result of following this platform's own autonomous INVESTMENT-
horizon recommendations, day over day, since inception.

Division of responsibility (do not blur these):

- `meta.decision_ledger.DecisionLedger` records *why* each decision was
  made and whether it was later right (per-ticker, per-horizon).
- `investment_cases` / the recommendation pipeline explain each decision's
  thesis.
- `investment_proof` validates the decision *process* (calibration,
  stability, counterfactual, committee agreement).
- The Shadow Fund is none of those. It owns *portfolio state*: what is
  currently held, at what weight, funded by how much cash, worth what NAV
  today, and how all of that got here -- one transaction at a time.

Every field here is derived from data `decision_service`/`capital_allocation`
already compute; nothing here is a new judgment call or a new source of
truth for *why* a decision was made.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.capital_allocation.models import CapitalAllocationPlan
from agx_research.decision_service.service import PositionAction
from agx_research.domain.provenance import Provenance


class ShadowFundPosition(BaseModel):
    """One position the Shadow Fund currently holds (or held, for a
    position closed on this exact date -- see `ShadowFundSnapshot.
    closed_positions_today`). `average_cost`/`entry_date` track a single
    weighted-average cost basis across every buy/increase into this
    ticker, the same single-aggregate-position simplification
    `decision_service.position.PositionState` already uses for a real
    investor -- not a multi-lot model."""

    ticker: str
    entry_date: date
    average_cost: float
    weight: float
    target_weight: float
    market_price: float
    market_value: float
    unrealized_pnl_pct: float | None = None
    horizon: str
    confidence: float
    investment_thesis: str


class ShadowFundClosedPosition(BaseModel):
    """A position fully exited -- realized P/L is fixed once this exists,
    never recomputed against a later price."""

    ticker: str
    entry_date: date
    exit_date: date
    average_cost: float
    exit_price: float
    realized_pnl_pct: float


class ShadowFundTransaction(BaseModel):
    """One executed change to the Shadow Fund's holdings on one date --
    the position-sizing/rebalancing/capital-deployment history. Only
    `buy`/`increase_position`/`reduce_position`/`exit` ever appear here;
    `hold`/`no_action` are not transactions (nothing changed)."""

    id: str
    date: date
    ticker: str
    action: PositionAction
    weight_before: float
    weight_after: float
    weight_delta: float
    price: float
    cash_delta: float
    transaction_cost: float
    investment_thesis: str
    confidence: float
    provenance: Provenance


class ShadowFundRiskMetrics(BaseModel):
    """Portfolio-level risk statistics computed from the Shadow Fund's own
    daily NAV series -- honestly gated by sample size, same
    `sample_status` pattern `meta.decision_ledger.DecisionPerformanceSummary`
    already uses, rather than reporting a noisy number from 3 data points."""

    volatility_annualized_pct: float | None = None
    max_drawdown_pct: float | None = None
    sharpe_like_ratio: float | None = None
    herfindahl_index: float | None = None
    largest_position_pct: float | None = None
    sample_days: int
    sample_status: str


class ShadowFundAttributionEntry(BaseModel):
    """One ticker's share of the Shadow Fund's total NAV gain/loss since
    inception -- a real contribution-to-return decomposition (daily
    weight x daily ticker return, compounded in NAV terms), not a
    cost-basis snapshot."""

    ticker: str
    contribution_pct_of_total_gain: float | None
    status: str


class ShadowFundNavPoint(BaseModel):
    """One day's NAV/cash/benchmark point -- the daily NAV history."""

    date: date
    nav: float
    cash: float
    cash_pct: float
    invested_pct: float
    daily_return_pct: float | None
    cumulative_return_pct: float
    benchmark_nav: float
    benchmark_cumulative_return_pct: float


class ShadowFundSnapshot(BaseModel):
    """The Shadow Fund's complete persisted state as of one trading day --
    one version per trading day under a single ledger entity id (see
    `repository.ShadowFundLedger`), so `history()` on that entity is
    already the full daily state/NAV time series with no separate,
    unboundedly-growing per-day store (the exact TD-63 mistake this
    package deliberately avoids)."""

    id: str = "shadow_fund"
    version: int = 1
    date: date
    inception_date: date
    nav: float
    cash: float
    cash_pct: float
    invested_pct: float
    daily_return_pct: float | None
    cumulative_return_pct: float
    benchmark_ticker: str
    benchmark_nav: float
    benchmark_cumulative_return_pct: float
    open_positions: list[ShadowFundPosition] = Field(default_factory=list)
    closed_positions_today: list[ShadowFundClosedPosition] = Field(default_factory=list)
    transactions: list[ShadowFundTransaction] = Field(default_factory=list)
    capital_allocation_plan: CapitalAllocationPlan | None = None
    risk: ShadowFundRiskMetrics
    attribution: list[ShadowFundAttributionEntry] = Field(default_factory=list)
    # ticker -> cumulative NAV-currency contribution to gain/loss since
    # inception. Small (bounded by universe size, not by elapsed days) and
    # carried forward so `attribution` above never needs to replay the
    # entire NAV history to recompute -- the one piece of rolling state
    # this snapshot accumulates rather than derives fresh each day.
    attribution_state: dict[str, float] = Field(default_factory=dict)
    provenance: Provenance


class ShadowFundPublicState(BaseModel):
    """The dashboard/API-facing view of `ShadowFundSnapshot` -- current
    state only, `closed_positions` widened to the all-time list (derived
    from the full ledger by `export.export_shadow_fund`, not just today's
    closures), `attribution_state` (internal rolling bookkeeping) dropped.
    This, not `ShadowFundSnapshot`, is the one contract `contracts/
    shadow_fund.schema.json` and `api/src/types.ts`/`web/src/types.ts`
    mirror -- see `export.py`."""

    date: date
    inception_date: date
    nav: float
    cash: float
    cash_pct: float
    invested_pct: float
    daily_return_pct: float | None
    cumulative_return_pct: float
    benchmark_ticker: str
    benchmark_nav: float
    benchmark_cumulative_return_pct: float
    excess_return_pct: float
    open_positions: list[ShadowFundPosition] = Field(default_factory=list)
    closed_positions: list[ShadowFundClosedPosition] = Field(default_factory=list)
    transactions: list[ShadowFundTransaction] = Field(default_factory=list)
    capital_allocation_plan: CapitalAllocationPlan | None = None
    risk: ShadowFundRiskMetrics
    attribution: list[ShadowFundAttributionEntry] = Field(default_factory=list)
    provenance: Provenance


class ShadowFundHistory(BaseModel):
    """The dashboard/API-facing NAV time series + all-time transaction
    log -- `shadow_fund_history.json` / `GET /shadow-fund-history`."""

    nav_series: list[ShadowFundNavPoint] = Field(default_factory=list)
    transactions: list[ShadowFundTransaction] = Field(default_factory=list)
