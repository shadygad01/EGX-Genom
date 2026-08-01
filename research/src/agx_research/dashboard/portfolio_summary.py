"""Portfolio Summary: "is my capital allocated correctly?" -- the CIO
Desk/Portfolio page's single question, answered from one already-real
computation.

Wraps `investment_proof.portfolio_validation.PortfolioValidationEngine`
(concentration, sector exposure, liquidity, weight reconciliation,
downside proxy) and adds the one number that engine doesn't compute
(portfolio-level expected return, a plain confidence-free weighted average
of `PortfolioPosition.expected_return` -- not a new engine, just a
sum/divide over fields the positions already carry) -- never a second,
parallel concentration/risk calculation.

`is_live_portfolio` names honestly which of two real things this summary
describes: the autonomous, position-unaware model portfolio
`PortfolioConstructor` already builds (what the CIO Desk shows by
default, no investor holdings assumed), or a real investor's own holdings
once supplied via `POST /decisions` (`decision_service.DecisionService`,
on demand only -- see CLAUDE.md). Never presented as the same thing.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.decision_service.service import PositionAwareDecision
from agx_research.investment_proof.portfolio_validation import (
    ConcentrationCheck,
    PortfolioValidationEngine,
    SectorExposure,
)
from agx_research.portfolio.constructor import PortfolioRecommendation


class PortfolioSummaryReport(BaseModel):
    as_of: date
    is_live_portfolio: bool
    position_count: int
    cash_weight: float
    invested_weight: float
    weights_reconcile: bool
    expected_return: float | None = None
    expected_risk: float | None = None
    concentration: ConcentrationCheck
    sector_exposures: list[SectorExposure] = Field(default_factory=list)
    max_sector_weight: float | None = None
    sector_concentration_status: str = "not_evaluated"
    liquidity_violations: list[str] = Field(default_factory=list)
    decision_conflicts: list[str] = Field(default_factory=list)


def build_portfolio_summary(
    portfolio: PortfolioRecommendation,
    as_of: date,
    *,
    is_live_portfolio: bool = False,
    sectors: dict[str, str] | None = None,
    illiquid_tickers: set[str] | None = None,
    position_aware_decisions: list[PositionAwareDecision] | None = None,
) -> PortfolioSummaryReport:
    validation = PortfolioValidationEngine().validate(
        portfolio.positions,
        portfolio.cash_weight,
        as_of,
        sectors=sectors,
        illiquid_tickers=illiquid_tickers,
        position_aware_decisions=position_aware_decisions,
    )
    invested_weight = sum(p.weight for p in portfolio.positions)
    expected_return = (
        sum(p.weight * p.expected_return for p in portfolio.positions) / invested_weight
        if invested_weight > 0
        else None
    )

    return PortfolioSummaryReport(
        as_of=as_of,
        is_live_portfolio=is_live_portfolio,
        position_count=len(portfolio.positions),
        cash_weight=validation.cash_weight,
        invested_weight=validation.invested_weight,
        weights_reconcile=validation.weights_reconcile,
        expected_return=expected_return,
        expected_risk=validation.expected_downside_proxy,
        concentration=validation.concentration,
        sector_exposures=validation.sector_exposures,
        max_sector_weight=validation.max_sector_weight,
        sector_concentration_status=validation.sector_concentration_status,
        liquidity_violations=validation.liquidity_violations,
        decision_conflicts=validation.decision_conflicts,
    )


__all__ = ["PortfolioSummaryReport", "build_portfolio_summary"]
