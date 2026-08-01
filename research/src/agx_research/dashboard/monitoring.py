"""Monitoring Warnings: "what changed since my last decision, and what
needs attention right now?" -- the CIO Desk/Monitoring product law's
single question, answered by one mechanically-derived list.

Every warning is derived from an existing, already-computed engine --
never a new judgment call invented for this artifact:

- `broken_thesis`: a knowledge object behind a currently-recommended
  ticker's position was `RETIRED` recently (`learning.monitor.
  ContinuousLearningMonitor`'s real mechanism, not a guess).
- `macro_risk_increased`: `decision_service.country_risk.assess_country_risk()`
  reports anything other than `NORMAL`.
- `catalyst_expired`: a corporate event for a currently-recommended ticker
  fell inside the recent lookback window -- the catalyst the position was
  tracking has now passed and the thesis is due for a look.
- `liquidity_deterioration`: a currently-recommended ticker falls below
  `decision_service.liquidity_floor.compute_illiquid_tickers()`'s floor.
- `portfolio_concentration`: `investment_proof.portfolio_validation.
  PortfolioValidationEngine`'s own concentration/sector-concentration
  verdict.
- `review_required`: a currently-recommended ticker's INVESTMENT-horizon
  `valid_until` has passed, or its supporting knowledge is in
  `KnowledgeStatus.MONITORING` -- both already-real signals, not new ones.

This is deliberately position-unaware (built from the same autonomous,
position-unaware model portfolio `investment_cases.json` already exports)
so it can be produced as a static artifact -- the same "decision_service
needs real positions, so it stays on-demand" boundary this codebase
already draws elsewhere is untouched; a live, position-aware caller can
layer its own broken/exited positions on top via `POST /decisions`
separately.
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.data.schemas import CorporateEvent
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.investment_proof.portfolio_validation import PortfolioValidationResult
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_engine import Recommendation
from agx_research.portfolio.constructor import PortfolioRecommendation

#: How many calendar days back a corporate event still counts as "just
#: expired" rather than ordinary history -- declared, uncalibrated, same
#: posture as every other declared-not-measured constant in this codebase
#: (see docs/TECHNICAL_DEBT.md).
CATALYST_RECENTLY_EXPIRED_DAYS = 7
#: How many calendar days back a retirement still counts as a fresh
#: "broken thesis" warning rather than old history.
THESIS_RECENTLY_BROKEN_DAYS = 14


class WarningCategory(str, Enum):
    BROKEN_THESIS = "broken_thesis"
    MACRO_RISK_INCREASED = "macro_risk_increased"
    CATALYST_EXPIRED = "catalyst_expired"
    LIQUIDITY_DETERIORATION = "liquidity_deterioration"
    PORTFOLIO_CONCENTRATION = "portfolio_concentration"
    REVIEW_REQUIRED = "review_required"


class WarningSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MonitoringWarning(BaseModel):
    category: WarningCategory
    severity: WarningSeverity
    ticker: str | None = None
    title: str
    detail: str


class MonitoringWarningsReport(BaseModel):
    as_of: date
    warnings: list[MonitoringWarning] = Field(default_factory=list)


def build_warnings(
    *,
    as_of: date,
    portfolio: PortfolioRecommendation | None,
    recommendations: list[Recommendation],
    knowledge_store: KnowledgeStore,
    corporate_events: dict[str, list[CorporateEvent]],
    country_risk: CountryRiskAssessment,
    illiquid_tickers: set[str],
    portfolio_validation: PortfolioValidationResult | None,
) -> MonitoringWarningsReport:
    tickers = sorted({p.ticker for p in (portfolio.positions if portfolio else [])})
    recommendation_by_ticker = {r.ticker: r for r in recommendations}
    warnings: list[MonitoringWarning] = []

    if country_risk.severity != CountryRiskSeverity.NORMAL:
        warnings.append(
            MonitoringWarning(
                category=WarningCategory.MACRO_RISK_INCREASED,
                severity=WarningSeverity.CRITICAL
                if country_risk.severity == CountryRiskSeverity.CRISIS
                else WarningSeverity.WARNING,
                title=f"Country & macro risk: {country_risk.severity.value}",
                detail="; ".join(country_risk.reasons) or "See decision_service.country_risk for the triggering series.",
            )
        )

    if portfolio_validation is not None:
        if portfolio_validation.concentration.status == "concentrated":
            warnings.append(
                MonitoringWarning(
                    category=WarningCategory.PORTFOLIO_CONCENTRATION,
                    severity=WarningSeverity.WARNING,
                    ticker=portfolio_validation.concentration.max_position_ticker,
                    title="Portfolio concentration above the diversification floor",
                    detail=(
                        f"Herfindahl index {portfolio_validation.concentration.herfindahl_index:.3f} "
                        f"(largest position {portfolio_validation.concentration.max_position_weight:.1%})."
                    ),
                )
            )
        if portfolio_validation.sector_concentration_status == "concentrated":
            warnings.append(
                MonitoringWarning(
                    category=WarningCategory.PORTFOLIO_CONCENTRATION,
                    severity=WarningSeverity.WARNING,
                    title="Sector concentration above the diversification floor",
                    detail=f"Largest single-sector weight {portfolio_validation.max_sector_weight:.1%}.",
                )
            )

    # Scanned across the whole store, not just today's surviving positions:
    # a thesis breaking is exactly what can make a ticker drop out of the
    # model portfolio entirely (KnowledgeWeightedHorizonModel.predict()
    # excludes RETIRED knowledge), so gating this on "still held today"
    # would silently hide the single clearest broken-thesis signal there is.
    for knowledge in knowledge_store.all_latest():
        if knowledge.status != KnowledgeStatus.RETIRED:
            continue
        if knowledge.retired_at is not None and (as_of - knowledge.retired_at) > timedelta(days=THESIS_RECENTLY_BROKEN_DAYS):
            continue
        for ticker in knowledge.affected_assets:
            warnings.append(
                MonitoringWarning(
                    category=WarningCategory.BROKEN_THESIS,
                    severity=WarningSeverity.CRITICAL,
                    ticker=ticker,
                    title=f"{ticker}: supporting thesis was retired",
                    detail=knowledge.retirement_reason or f"{knowledge.id} retired; realized outcomes disagreed with expectation.",
                )
            )

    for ticker in tickers:
        for event in corporate_events.get(ticker, []):
            days_since = (as_of - event.event_date).days
            if 0 <= days_since <= CATALYST_RECENTLY_EXPIRED_DAYS:
                warnings.append(
                    MonitoringWarning(
                        category=WarningCategory.CATALYST_EXPIRED,
                        severity=WarningSeverity.INFO,
                        ticker=ticker,
                        title=f"{ticker}: tracked catalyst has passed",
                        detail=f"{event.event_date.isoformat()}: {event.event_type} -- {event.description}",
                    )
                )

        if ticker in illiquid_tickers:
            warnings.append(
                MonitoringWarning(
                    category=WarningCategory.LIQUIDITY_DETERIORATION,
                    severity=WarningSeverity.WARNING,
                    ticker=ticker,
                    title=f"{ticker}: below the liquidity floor",
                    detail="Average daily traded value has fallen below decision_service's liquidity floor; sizing is capped to zero regardless of thesis strength.",
                )
            )

        rec = recommendation_by_ticker.get(ticker)
        decision = rec.horizon_decisions.get(Horizon.INVESTMENT) if rec else None
        if decision is not None and decision.valid_until <= as_of:
            warnings.append(
                MonitoringWarning(
                    category=WarningCategory.REVIEW_REQUIRED,
                    severity=WarningSeverity.WARNING,
                    ticker=ticker,
                    title=f"{ticker}: decision review date has passed",
                    detail=f"INVESTMENT-horizon decision was valid until {decision.valid_until.isoformat()}.",
                )
            )
        for knowledge_id in (rec.supporting_knowledge_ids if rec else []):
            knowledge = knowledge_store.latest(knowledge_id)
            if knowledge is not None and knowledge.status == KnowledgeStatus.MONITORING:
                warnings.append(
                    MonitoringWarning(
                        category=WarningCategory.REVIEW_REQUIRED,
                        severity=WarningSeverity.INFO,
                        ticker=ticker,
                        title=f"{ticker}: supporting knowledge under active monitoring",
                        detail=f"{knowledge.id}: {knowledge.economic_explanation}",
                    )
                )

    return MonitoringWarningsReport(as_of=as_of, warnings=warnings)


__all__ = [
    "CATALYST_RECENTLY_EXPIRED_DAYS",
    "MonitoringWarning",
    "MonitoringWarningsReport",
    "THESIS_RECENTLY_BROKEN_DAYS",
    "WarningCategory",
    "WarningSeverity",
    "build_warnings",
]
