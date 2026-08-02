"""Decision-facing valuation metrics derived only from reported inputs."""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, Field

from agx_research.financials.provider import FinancialStatementProvider
from agx_research.valuation.engine import FairValueEngine, FairValueResult


class ValuationMetrics(BaseModel):
    ticker: str
    as_of: date
    latest_financial_period: date | None = None
    latest_market_snapshot_date: date | None = None
    current_price: float | None = None
    market_cap: float | None = None
    market_pe: float | None = None
    market_eps: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    enterprise_value: float | None = None
    ebitda: float | None = None
    ev_to_ebitda: float | None = None
    price_to_book: float | None = None
    dcf_per_share: float | None = None
    weighted_fair_value: float | None = None
    bear_case: float | None = None
    bull_case: float | None = None
    included_models: list[str] = Field(default_factory=list)
    unavailable_reasons: list[str] = Field(default_factory=list)


def _latest(items, line_item: str):
    matches = [item for item in items if item.line_item == line_item]
    return max(matches, key=lambda item: item.period_end_date, default=None)


def compute_valuation_metrics(
    ticker: str,
    as_of: date,
    current_price: float | None,
    provider: FinancialStatementProvider,
    fair_value_engine: FairValueEngine,
    *,
    sector: str | None = None,
) -> ValuationMetrics:
    items = provider.get_line_items(ticker, as_of - timedelta(days=3000), as_of)
    reported_items = [
        item for item in items if item.period_type.upper() in {"ANNUAL", "QUARTERLY"}
    ]
    snapshot_items = [item for item in items if item.period_type.upper() == "SNAPSHOT"]
    latest_period = max((item.period_end_date for item in reported_items), default=None)
    latest_snapshot = max((item.period_end_date for item in snapshot_items), default=None)
    values = {
        name: (_latest(items, name).value if _latest(items, name) is not None else None)
        for name in (
            "shares_outstanding",
            "total_equity",
            "total_debt",
            "cash_and_equivalents",
            "ebitda",
            "market_cap",
            "market_pe",
            "market_eps",
            "market_dividend_yield",
            "market_beta",
        )
    }
    shares = values["shares_outstanding"]
    equity = values["total_equity"]
    debt = values["total_debt"]
    cash = values["cash_and_equivalents"]
    ebitda = values["ebitda"]
    market_cap = values["market_cap"]
    if market_cap is None and current_price and shares and shares > 0:
        market_cap = current_price * shares
    enterprise_value = (
        market_cap + debt - cash
        if market_cap is not None and debt is not None and cash is not None
        else None
    )
    fair: FairValueResult | None = fair_value_engine.value(ticker, as_of, sector=sector)
    reasons: list[str] = []
    if shares is None:
        reasons.append("shares_outstanding")
    if equity is None:
        reasons.append("total_equity")
    if debt is None:
        reasons.append("total_debt")
    if cash is None:
        reasons.append("cash_and_equivalents")
    if ebitda is None:
        reasons.append("ebitda")
    if current_price is None:
        reasons.append("current_price")
    return ValuationMetrics(
        ticker=ticker,
        as_of=as_of,
        latest_financial_period=latest_period,
        latest_market_snapshot_date=latest_snapshot,
        current_price=current_price,
        market_cap=market_cap,
        market_pe=values["market_pe"],
        market_eps=values["market_eps"],
        dividend_yield=values["market_dividend_yield"],
        beta=values["market_beta"],
        enterprise_value=enterprise_value,
        ebitda=ebitda,
        ev_to_ebitda=(enterprise_value / ebitda if enterprise_value is not None and ebitda and ebitda > 0 else None),
        price_to_book=(market_cap / equity if market_cap is not None and equity and equity > 0 else None),
        dcf_per_share=(fair.models.get("dcf") if fair else None),
        weighted_fair_value=(fair.weighted_fair_value if fair else None),
        bear_case=(fair.bear_case if fair else None),
        bull_case=(fair.bull_case if fair else None),
        included_models=(fair.included_models if fair else []),
        unavailable_reasons=sorted(set(reasons)),
    )
