"""Point-in-time multi-model fair value, ported from Smartlist IVE V2.

The method is shared; no Smartlist result or database is consumed here.
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise
from statistics import median

from pydantic import BaseModel, Field

from agx_research.financials.provider import FinancialStatementProvider

MODEL_WEIGHTS = {
    "dcf": 0.30, "ddm": 0.10, "residual_income": 0.15,
    "earnings_power": 0.15, "ev_ebitda": 0.10, "pe": 0.10, "pb": 0.10,
}
SECTOR_MULTIPLES = {
    "Banks": (9.0, 7.0, 1.0), "Real Estate": (12.0, 9.0, 1.5),
    "Technology": (20.0, 14.0, 3.0), "Telecommunications": (10.0, 7.0, 1.5),
    "Materials": (9.0, 7.0, 1.2), "default": (11.0, 8.5, 1.3),
}


class ValuationAssumptions(BaseModel):
    version: str = "smartlist-ive-v2.1"
    risk_free_rate: float = 0.125
    equity_risk_premium: float = 0.07
    beta: float = 1.0
    wacc: float = 0.16
    terminal_growth: float = 0.04
    tax_rate: float = 0.225


class FairValueResult(BaseModel):
    ticker: str
    as_of: date
    weighted_fair_value: float = Field(gt=0)
    bear_case: float = Field(gt=0)
    base_case: float = Field(gt=0)
    bull_case: float = Field(gt=0)
    models: dict[str, float | None]
    included_models: list[str]
    latest_period: date
    assumptions_version: str


def _latest(rows, field):
    return next((row.get(field) for row in reversed(rows) if row.get(field) is not None), None)


def _growth(rows, field):
    values = [row.get(field) for row in rows]
    rates = []
    for previous, current in pairwise(values):
        if previous not in (None, 0) and current is not None:
            rates.append((current - previous) / abs(previous))
    return sum(rates[-3:]) / len(rates[-3:]) if rates else None


def _forecast(rows, assumptions):
    forecasts = []
    values = {name: _latest(rows, name) for name in ("revenue", "eps", "free_cash_flow", "dividend")}
    growth = {}
    for name in ("revenue", "eps", "free_cash_flow"):
        historical = _growth(rows, name)
        historical = assumptions.terminal_growth if historical is None else max(-0.20, min(0.20, historical))
        growth[name] = 0.5 * historical + 0.5 * assumptions.terminal_growth
    growth["dividend"] = 0.7 * growth["eps"]
    for _ in range(5):
        for name, value in list(values.items()):
            values[name] = value * (1 + growth[name]) if value is not None else None
        forecasts.append(dict(values))
    return forecasts


def _multiples(sector):
    for key, values in SECTOR_MULTIPLES.items():
        if key != "default" and sector and key.lower() in sector.lower():
            return values
    return SECTOR_MULTIPLES["default"]


def _build_rows(items):
    periods: dict[date, dict[str, float]] = {}
    period_types: dict[date, str] = {}
    for item in items:
        periods.setdefault(item.period_end_date, {})[item.line_item] = item.value
        period_types[item.period_end_date] = item.period_type.upper()
    rows = [dict(period=period, **values) for period, values in sorted(periods.items())]
    quarterly = [row for row in rows if period_types[row["period"]] == "QUARTERLY"]
    if len(quarterly) >= 4:
        quarters = quarterly[-4:]
        flow_fields = {
            "revenue", "cost_of_revenue", "gross_profit", "operating_income",
            "net_income", "operating_cash_flow", "free_cash_flow", "ebitda",
            "dividend_per_share", "eps_basic", "eps_diluted",
        }
        ttm = {"period": quarters[-1]["period"]}
        for field in {key for row in quarters for key in row if key != "period"}:
            values = [row.get(field) for row in quarters]
            if field in flow_fields and all(value is not None for value in values):
                ttm[field] = sum(values)
            elif field == "shares_outstanding":
                known = [value for value in values if value is not None]
                if known:
                    ttm[field] = sum(known) / len(known)
            else:
                ttm[field] = next((value for value in reversed(values) if value is not None), None)
        rows = [row for row in rows if period_types[row["period"]] == "ANNUAL"] + [ttm]
    return rows


class FairValueEngine:
    def __init__(self, provider: FinancialStatementProvider, assumptions=None):
        self.provider = provider
        self.assumptions = assumptions or ValuationAssumptions()

    def value(self, ticker: str, as_of: date, *, sector: str | None = None) -> FairValueResult | None:
        items = self.provider.get_line_items(ticker, as_of - timedelta(days=1100), as_of)
        if not items:
            return None
        rows = _build_rows(items)
        latest_period = rows[-1]["period"]
        if (as_of - latest_period).days > 550:
            return None
        # Canonical aliases keep the engine source-agnostic.
        for row in rows:
            row["eps"] = row.get("eps_diluted", row.get("eps_basic"))
            row["equity"] = row.get("total_equity")
            row["cash"] = row.get("cash_and_equivalents")
            row["debt"] = row.get("total_debt")
            row["shares"] = row.get("shares_outstanding")
            row["dividend"] = row.get("dividend_per_share")
        forecasts = _forecast(rows, self.assumptions)
        a = self.assumptions
        shares = _latest(rows, "shares")
        cash, debt = _latest(rows, "cash") or 0.0, _latest(rows, "debt")
        ke = a.risk_free_rate + a.beta * a.equity_risk_premium
        pe, ev_ebitda, pb = _multiples(sector)
        results: dict[str, float | None] = {name: None for name in MODEL_WEIGHTS}
        if shares and shares > 0:
            fcf = [row["free_cash_flow"] for row in forecasts]
            if all(value is not None for value in fcf) and a.wacc > a.terminal_growth:
                pv = sum(value / (1 + a.wacc) ** year for year, value in enumerate(fcf, 1))
                terminal = fcf[-1] * (1 + a.terminal_growth) / (a.wacc - a.terminal_growth)
                results["dcf"] = (pv + terminal / (1 + a.wacc) ** 5 + cash - (debt or 0)) / shares
            dividend = forecasts[0]["dividend"]
            if dividend and dividend > 0 and ke > a.terminal_growth:
                results["ddm"] = dividend / (ke - a.terminal_growth)
            equity = _latest(rows, "equity")
            if equity and forecasts[0]["eps"] is not None and ke > a.terminal_growth:
                bv = equity / shares
                pv_ri = 0.0
                for year, forecast in enumerate(forecasts, 1):
                    ri = forecast["eps"] - ke * bv
                    pv_ri += ri / (1 + ke) ** year
                    bv += forecast["eps"] - (_latest(rows, "dividend") or 0)
                terminal_ri = (forecasts[-1]["eps"] - ke * bv) * 0.5 / (ke - a.terminal_growth)
                results["residual_income"] = equity / shares + pv_ri + terminal_ri / (1 + ke) ** 5
            ebit_values = [row.get("operating_income") for row in rows[-3:] if row.get("operating_income") is not None]
            if ebit_values:
                epv = (sum(ebit_values) / len(ebit_values)) * (1 - a.tax_rate) / a.wacc
                results["earnings_power"] = (epv + cash - (debt or 0)) / shares
            ebitda = _latest(rows, "ebitda")
            if ebitda and ebitda > 0:
                results["ev_ebitda"] = (ebitda * ev_ebitda + cash - (debt or 0)) / shares
            eps = _latest(rows, "eps")
            if eps and eps > 0:
                results["pe"] = eps * pe
            if equity and equity > 0:
                results["pb"] = equity / shares * pb
        candidates = {name: value for name, value in results.items() if value and value > 0}
        if len(candidates) < 3:
            return None
        midpoint = median(candidates.values())
        included = {name: value for name, value in candidates.items() if midpoint / 3 <= value <= midpoint * 3}
        if len(included) < 3:
            return None
        weight = sum(MODEL_WEIGHTS[name] for name in included)
        fair = sum(MODEL_WEIGHTS[name] * value for name, value in included.items()) / weight
        bear = max(min(included.values()), fair * 0.60)
        bull = min(max(included.values()), fair * 1.60)
        rounded = {name: round(value, 4) if value else None for name, value in results.items()}
        return FairValueResult(
            ticker=ticker, as_of=as_of, weighted_fair_value=round(fair, 4),
            bear_case=round(bear, 4), base_case=round(fair, 4), bull_case=round(bull, 4),
            models=rounded, included_models=sorted(included), latest_period=latest_period,
            assumptions_version=a.version,
        )
