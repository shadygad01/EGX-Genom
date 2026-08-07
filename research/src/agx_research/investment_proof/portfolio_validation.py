"""Phase 7: Portfolio Validation.

No concentration/diversification/portfolio-level-downside metric existed
anywhere in this codebase before (confirmed by direct search -- see
`docs/PHASE_STATUS.md`'s Investment Proof Framework entry). This module
adds them, computed only from real `PortfolioPosition`/`PositionAwareDecision`
weights -- never a fabricated covariance or historical-performance number.
`expected_downside_proxy` is explicitly named a *proxy*, not a true VaR:
a true portfolio VaR needs a covariance matrix this platform's own
`portfolio/constructor.py` docstring already defers ("needs real data
depth") -- this module doesn't fabricate one either.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.decision_service.service import PositionAwareDecision
from agx_research.portfolio.concentration_limits import (
    HERFINDAHL_CONCENTRATED_THRESHOLD,
    MAX_SECTOR_CONCENTRATION,
)
from agx_research.portfolio.constructor import PortfolioPosition

WEIGHT_CONSISTENCY_TOLERANCE = 0.01


class ConcentrationCheck(BaseModel):
    herfindahl_index: float
    status: str  # "diversified" | "concentrated"
    max_position_weight: float
    max_position_ticker: str | None = None
    top_3_weight: float


class SectorExposure(BaseModel):
    sector: str
    weight: float
    tickers: list[str] = Field(default_factory=list)


class PortfolioValidationResult(BaseModel):
    as_of: date
    cash_weight: float
    invested_weight: float
    weights_reconcile: bool  # invested_weight + cash_weight == 1.0, within tolerance
    concentration: ConcentrationCheck
    sector_exposures: list[SectorExposure] = Field(default_factory=list)
    max_sector_weight: float | None = None
    sector_concentration_status: str = "not_evaluated"  # "diversified" | "concentrated" | "not_evaluated"
    liquidity_violations: list[str] = Field(default_factory=list)
    expected_downside_proxy: float | None = None
    decision_conflicts: list[str] = Field(default_factory=list)


class PortfolioValidationEngine:
    def validate(
        self,
        positions: list[PortfolioPosition],
        cash_weight: float,
        as_of: date,
        *,
        sectors: dict[str, str] | None = None,
        illiquid_tickers: set[str] | None = None,
        position_aware_decisions: list[PositionAwareDecision] | None = None,
    ) -> PortfolioValidationResult:
        illiquid_tickers = illiquid_tickers or set()
        invested_weight = sum(p.weight for p in positions)

        herfindahl = sum(p.weight**2 for p in positions)
        sorted_by_weight = sorted(positions, key=lambda p: p.weight, reverse=True)
        concentration = ConcentrationCheck(
            herfindahl_index=herfindahl,
            status="concentrated" if herfindahl > HERFINDAHL_CONCENTRATED_THRESHOLD else "diversified",
            max_position_weight=sorted_by_weight[0].weight if sorted_by_weight else 0.0,
            max_position_ticker=sorted_by_weight[0].ticker if sorted_by_weight else None,
            top_3_weight=sum(p.weight for p in sorted_by_weight[:3]),
        )

        result = PortfolioValidationResult(
            as_of=as_of,
            cash_weight=cash_weight,
            invested_weight=invested_weight,
            weights_reconcile=abs(invested_weight + cash_weight - 1.0) < WEIGHT_CONSISTENCY_TOLERANCE,
            concentration=concentration,
            liquidity_violations=[p.ticker for p in positions if p.ticker in illiquid_tickers and p.weight > 0],
            expected_downside_proxy=(
                sum(p.weight * p.expected_risk for p in positions) / invested_weight if invested_weight > 0 else None
            ),
        )

        if sectors:
            by_sector: dict[str, list[PortfolioPosition]] = {}
            for p in positions:
                sector = sectors.get(p.ticker, "unknown")
                by_sector.setdefault(sector, []).append(p)
            result.sector_exposures = sorted(
                (
                    SectorExposure(sector=sector, weight=sum(p.weight for p in group), tickers=[p.ticker for p in group])
                    for sector, group in by_sector.items()
                ),
                key=lambda e: e.weight,
                reverse=True,
            )
            result.max_sector_weight = result.sector_exposures[0].weight if result.sector_exposures else 0.0
            result.sector_concentration_status = (
                "concentrated" if (result.max_sector_weight or 0.0) > MAX_SECTOR_CONCENTRATION else "diversified"
            )

        if position_aware_decisions is not None:
            by_ticker = {p.ticker: p.weight for p in positions}
            for decision in position_aware_decisions:
                autonomous_weight = by_ticker.get(decision.ticker, 0.0)
                if abs(autonomous_weight - decision.target_weight) > WEIGHT_CONSISTENCY_TOLERANCE:
                    result.decision_conflicts.append(
                        f"{decision.ticker}: PortfolioConstructor weight {autonomous_weight:.2%} vs. "
                        f"DecisionService target weight {decision.target_weight:.2%} -- position-unaware and "
                        "position-aware construction disagree by more than the reconciliation tolerance."
                    )

        return result


__all__ = [
    "ConcentrationCheck",
    "HERFINDAHL_CONCENTRATED_THRESHOLD",
    "MAX_SECTOR_CONCENTRATION",
    "PortfolioValidationEngine",
    "PortfolioValidationResult",
    "SectorExposure",
]
