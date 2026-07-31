"""Per-ticker evidence readiness and explicit abstention decisions."""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.decision_service.country_risk import has_sufficient_currency_data
from agx_research.decision_service.liquidity_floor import (
    DEFAULT_MIN_AVERAGE_TRADED_VALUE as _LIQUIDITY_FLOOR_MIN_AVG_TRADED_VALUE,
)
from agx_research.decision_service.liquidity_floor import compute_illiquid_tickers
from agx_research.financials.provider import FinancialStatementProvider
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.market_memory.state import MarketState
from agx_research.valuation import FairValueEngine

# Added per docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md R2 (extend this
# existing gate rather than build a second, parallel one) and R4 (a
# liquidity floor deserves the same hard-gate treatment as every other
# mandatory-evidence check here, not a separate mechanism). The
# thresholds themselves are declared, uncalibrated, and owned by
# `decision_service` (TD-45/TD-46) -- imported above, not redeclared, so
# this gate and `DecisionService` can never silently drift apart.


class ReadinessStatus(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class DecisionReadiness(BaseModel):
    ticker: str
    as_of: date
    status: ReadinessStatus
    decision: str
    ready_horizons: list[Horizon] = Field(default_factory=list)
    horizon_blockers: dict[Horizon, list[str]] = Field(default_factory=dict)
    price_observations: int = 0
    latest_price_date: date | None = None
    news_items: int = 0
    corporate_events: int = 0
    financial_periods: int = 0
    fair_value_available: bool = False
    # (current_price - weighted_fair_value) / weighted_fair_value: positive
    # means the current price sits above the calculated fair value
    # (expensive), negative means below it (a margin of safety). `None`
    # whenever no fair value could be computed (see `fair_value_available`).
    price_vs_fair_value_pct: float | None = None
    macro_series: int = 0
    active_knowledge: int = 0
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


# Declared, uncalibrated threshold (same posture as the liquidity floor /
# country-risk thresholds this module already imports from
# `decision_service` -- see TD-6/17/20/33/44/45/46): how far above the
# calculated fair value the current price can sit before the price-quality
# criterion below flags it as a weak entry and blocks INVESTMENT
# readiness. Not derived from real EGX outcome history -- see TD-51.
MAX_PRICE_ABOVE_FAIR_VALUE_PCT = 0.20

_GAP_LAYER_THRESHOLDS: dict[str, int] = {
    "valuation": 1,
    "disclosures": 1,
    "news": 1,
    "macro": 3,
    "knowledge": 1,
}


class DataLayerGap(BaseModel):
    layer: str
    count: int
    threshold: int
    complete: bool
    completeness_pct: float


class TickerDataGapReport(BaseModel):
    ticker: str
    as_of: date
    status: ReadinessStatus
    decision: str
    ready_horizons: list[Horizon] = Field(default_factory=list)
    swing_ready: bool
    investment_ready: bool
    price_observations: int
    latest_price_date: date | None
    layers: list[DataLayerGap]
    overall_completeness_pct: float
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


def build_ticker_data_gap_report(
    readiness_rows: list[DecisionReadiness],
) -> list[TickerDataGapReport]:
    """Decompose each `DecisionReadiness` row into the five named data
    layers (Valuation/Disclosures/News/Macro/Knowledge) with an explicit
    completeness percentage per layer, so it's visible at a glance exactly
    which layer blocks a given ticker's Swing/Investment readiness.

    This is a pure re-derivation of `assess_decision_readiness`'s own
    counts and thresholds -- it introduces no second set of gates that
    could ever disagree with the readiness this report is describing.
    """
    reports: list[TickerDataGapReport] = []
    for row in readiness_rows:
        layer_counts = {
            "valuation": int(row.fair_value_available),
            "disclosures": row.corporate_events,
            "news": row.news_items,
            "macro": row.macro_series,
            "knowledge": row.active_knowledge,
        }
        layers = [
            DataLayerGap(
                layer=layer,
                count=count,
                threshold=_GAP_LAYER_THRESHOLDS[layer],
                complete=count >= _GAP_LAYER_THRESHOLDS[layer],
                completeness_pct=round(
                    min(count / _GAP_LAYER_THRESHOLDS[layer], 1.0) * 100, 1
                ),
            )
            for layer, count in layer_counts.items()
        ]
        overall_pct = round(sum(layer.completeness_pct for layer in layers) / len(layers), 1)
        reports.append(
            TickerDataGapReport(
                ticker=row.ticker,
                as_of=row.as_of,
                status=row.status,
                decision=row.decision,
                ready_horizons=row.ready_horizons,
                swing_ready=Horizon.SWING in row.ready_horizons,
                investment_ready=Horizon.INVESTMENT in row.ready_horizons,
                price_observations=row.price_observations,
                latest_price_date=row.latest_price_date,
                layers=layers,
                overall_completeness_pct=overall_pct,
                blockers=row.blockers,
                next_actions=row.next_actions,
            )
        )
    return reports


def assess_decision_readiness(
    market_state: MarketState,
    financials: FinancialStatementProvider,
    knowledge: list[KnowledgeObject],
    fair_value_engine: FairValueEngine | None = None,
) -> list[DecisionReadiness]:
    snapshot = market_state.dataset_snapshot
    macro_series = sum(1 for values in snapshot.macro_series.values() if values)
    illiquid_tickers = compute_illiquid_tickers(
        snapshot, min_average_traded_value=_LIQUIDITY_FLOOR_MIN_AVG_TRADED_VALUE
    )
    country_risk_data_present = has_sufficient_currency_data(snapshot.macro_series)
    rows: list[DecisionReadiness] = []
    for ticker in sorted(snapshot.tickers):
        prices = snapshot.price_history.get(ticker, [])
        latest_bar = max(prices, key=lambda bar: bar.trade_date, default=None)
        latest_price = latest_bar.trade_date if latest_bar else None
        price_is_fresh = latest_price is not None and (market_state.as_of - latest_price).days <= 7
        news = [item for item in snapshot.news if ticker in item.tickers]
        events = snapshot.corporate_events.get(ticker, [])
        items = financials.get_line_items(
            ticker, market_state.as_of - timedelta(days=730), market_state.as_of
        )
        financial_periods = len({item.period_end_date for item in items})
        fair_value_result = (
            fair_value_engine.value(
                ticker, market_state.as_of, sector=market_state.sectors.get(ticker)
            )
            if fair_value_engine else None
        )
        fair_value_available = bool(fair_value_result)
        price_vs_fair_value_pct = (
            round(
                (latest_bar.close - fair_value_result.weighted_fair_value)
                / fair_value_result.weighted_fair_value,
                4,
            )
            if fair_value_result and latest_bar
            else None
        )
        price_overvalued = (
            price_vs_fair_value_pct is not None
            and price_vs_fair_value_pct > MAX_PRICE_ABOVE_FAIR_VALUE_PCT
        )
        active_knowledge = [
            item
            for item in knowledge
            if ticker in item.affected_assets and item.status.value != "retired"
        ]

        knowledge_by_horizon = {
            horizon: [item for item in active_knowledge if item.horizon == horizon]
            for horizon in Horizon
        }
        horizon_blockers: dict[Horizon, list[str]] = {
            Horizon.MICRO: [],
            Horizon.SWING: [],
            Horizon.INVESTMENT: [],
        }
        is_illiquid = ticker in illiquid_tickers

        if len(prices) < 60:
            horizon_blockers[Horizon.MICRO].append("Fewer than 60 price observations.")
        if not price_is_fresh:
            horizon_blockers[Horizon.MICRO].append("Price data is stale.")
        if not knowledge_by_horizon[Horizon.MICRO]:
            horizon_blockers[Horizon.MICRO].append("No active knowledge for the Micro horizon.")
        if is_illiquid:
            horizon_blockers[Horizon.MICRO].append(
                "Liquidity is below the executable minimum."
            )

        if len(prices) < 120:
            horizon_blockers[Horizon.SWING].append("Fewer than 120 price observations.")
        if not price_is_fresh:
            horizon_blockers[Horizon.SWING].append("Price data is stale.")
        if not (news or events):
            horizon_blockers[Horizon.SWING].append("No recent news or corporate event for the company.")
        if not knowledge_by_horizon[Horizon.SWING]:
            horizon_blockers[Horizon.SWING].append("No active knowledge for the Swing horizon.")
        if is_illiquid:
            horizon_blockers[Horizon.SWING].append(
                "Liquidity is below the executable minimum."
            )

        if len(prices) < 252:
            horizon_blockers[Horizon.INVESTMENT].append("Fewer than 252 price observations.")
        if not price_is_fresh:
            horizon_blockers[Horizon.INVESTMENT].append("Price data is stale.")
        if not fair_value_available:
            horizon_blockers[Horizon.INVESTMENT].append(
                "No reliable fair value from at least three valid models."
            )
        elif price_overvalued:
            horizon_blockers[Horizon.INVESTMENT].append(
                f"Current price is {price_vs_fair_value_pct:+.0%} vs. the calculated fair "
                "value (weak entry quality)."
            )
        if macro_series < 3:
            horizon_blockers[Horizon.INVESTMENT].append("Fewer than three macro series.")
        if not country_risk_data_present:
            horizon_blockers[Horizon.INVESTMENT].append(
                "Insufficient exchange-rate data to assess country risk."
            )
        if not knowledge_by_horizon[Horizon.INVESTMENT]:
            horizon_blockers[Horizon.INVESTMENT].append(
                "No active knowledge for the Investment horizon."
            )
        if is_illiquid:
            horizon_blockers[Horizon.INVESTMENT].append(
                "Liquidity is below the executable minimum."
            )

        ready_horizons = [
            horizon for horizon, reasons in horizon_blockers.items() if not reasons
        ]

        blockers: list[str] = []
        next_actions: list[str] = []
        if not prices:
            blockers.append("No reliable price history available.")
            next_actions.append("Connect a working EGX price and trading-volume source.")
        elif not price_is_fresh:
            blockers.append("The latest price observation is stale.")
            next_actions.append("Refresh the price collector and verify trading-day coverage.")
        if not fair_value_available:
            blockers.append("A reliable fair value cannot be computed from current inputs.")
            next_actions.append("Supply shares outstanding and the fields needed for at least three valuation models.")
        elif price_overvalued:
            blockers.append(
                f"Current price is {price_vs_fair_value_pct:+.0%} above the calculated fair value."
            )
            next_actions.append(
                "Wait for the price to retrace toward fair value, or for fair value to rise via reported earnings growth."
            )
        if not news and not events:
            blockers.append("No news or corporate event linked to the ticker within the window.")
            next_actions.append("Improve company-name/ticker matching against news.")
        if macro_series < 3:
            blockers.append("The macro context has fewer than three complete series.")
            next_actions.append("Restore at least three recent macro series.")
        if not country_risk_data_present:
            blockers.append("Insufficient exchange-rate data to assess country risk.")
            next_actions.append("Connect an exchange-rate series (e.g. EGP_USD) with sufficient coverage for assessment.")
        if is_illiquid:
            blockers.append("Liquidity is below the executable minimum for any decision.")
            next_actions.append("Do not force a decision on an illiquid ticker; wait for liquidity to improve or exclude it.")
        if not active_knowledge:
            blockers.append("No active, validated knowledge object covers this ticker.")
            next_actions.append("Run hypotheses through validation before issuing any decision.")

        decision_allowed = bool(ready_horizons and active_knowledge)
        status = (
            ReadinessStatus.READY
            if decision_allowed
            else ReadinessStatus.DEGRADED
            if prices
            else ReadinessStatus.BLOCKED
        )
        rows.append(
            DecisionReadiness(
                ticker=ticker,
                as_of=market_state.as_of,
                status=status,
                decision="researchable" if decision_allowed else "abstain",
                ready_horizons=ready_horizons,
                horizon_blockers=horizon_blockers,
                price_observations=len(prices),
                latest_price_date=latest_price,
                news_items=len(news),
                corporate_events=len(events),
                financial_periods=financial_periods,
                fair_value_available=fair_value_available,
                price_vs_fair_value_pct=price_vs_fair_value_pct,
                macro_series=macro_series,
                active_knowledge=len(active_knowledge),
                blockers=blockers,
                next_actions=next_actions,
            )
        )
    return rows
