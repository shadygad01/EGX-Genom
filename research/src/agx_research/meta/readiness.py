"""Per-ticker evidence readiness and explicit abstention decisions."""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.config import Horizon
from agx_research.financials.provider import FinancialStatementProvider
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.market_memory.state import MarketState


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
    price_observations: int = 0
    latest_price_date: date | None = None
    news_items: int = 0
    corporate_events: int = 0
    financial_periods: int = 0
    macro_series: int = 0
    active_knowledge: int = 0
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


def assess_decision_readiness(
    market_state: MarketState,
    financials: FinancialStatementProvider,
    knowledge: list[KnowledgeObject],
) -> list[DecisionReadiness]:
    snapshot = market_state.dataset_snapshot
    macro_series = sum(1 for values in snapshot.macro_series.values() if values)
    rows: list[DecisionReadiness] = []
    for ticker in sorted(snapshot.tickers):
        prices = snapshot.price_history.get(ticker, [])
        latest_price = max((bar.trade_date for bar in prices), default=None)
        price_is_fresh = latest_price is not None and (market_state.as_of - latest_price).days <= 7
        news = [item for item in snapshot.news if ticker in item.tickers]
        events = snapshot.corporate_events.get(ticker, [])
        items = financials.get_line_items(
            ticker, market_state.as_of - timedelta(days=730), market_state.as_of
        )
        financial_periods = len({item.period_end_date for item in items})
        active_knowledge = [
            item
            for item in knowledge
            if ticker in item.affected_assets and item.status.value != "retired"
        ]

        ready_horizons: list[Horizon] = []
        if len(prices) >= 15 and price_is_fresh:
            ready_horizons.append(Horizon.MICRO)
        if len(prices) >= 20 and price_is_fresh and (news or events):
            ready_horizons.append(Horizon.SWING)
        if len(prices) >= 20 and price_is_fresh and financial_periods >= 2 and macro_series >= 3:
            ready_horizons.append(Horizon.INVESTMENT)

        blockers: list[str] = []
        next_actions: list[str] = []
        if not prices:
            blockers.append("No trustworthy price history is available.")
            next_actions.append("Connect a working EGX OHLCV source.")
        elif not price_is_fresh:
            blockers.append("Latest price observation is stale.")
            next_actions.append("Refresh the price collector and verify market-date coverage.")
        if financial_periods < 2:
            blockers.append("Fewer than two financial reporting periods are available.")
            next_actions.append("Collect two comparable financial-statement periods.")
        if not news and not events:
            blockers.append("No ticker-linked news or corporate event is available in the window.")
            next_actions.append("Improve company-name and ticker entity resolution for news.")
        if macro_series < 3:
            blockers.append("Macroeconomic context has fewer than three populated series.")
            next_actions.append("Restore at least three current macro series.")
        if not active_knowledge:
            blockers.append("No validated, active knowledge object covers this ticker.")
            next_actions.append("Run hypotheses through validation before issuing a recommendation.")

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
                price_observations=len(prices),
                latest_price_date=latest_price,
                news_items=len(news),
                corporate_events=len(events),
                financial_periods=financial_periods,
                macro_series=macro_series,
                active_knowledge=len(active_knowledge),
                blockers=blockers,
                next_actions=next_actions,
            )
        )
    return rows
