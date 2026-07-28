"""Explainable non-estimated financial-data coverage for the universe."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from pydantic import BaseModel, Field, model_validator

from agx_research.financials.schema import FinancialStatementLineItem

ANY_REPORTED_FINANCIAL_ITEM = "any_reported_financial_item"


class TickerFinancialCoverage(BaseModel):
    ticker: str
    covered: bool
    latest_period_end_date: date | None = None
    present_items: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)


class FinancialCoverageReport(BaseModel):
    as_of: date
    universe_count: int = Field(ge=0)
    covered_count: int = Field(ge=0)
    coverage_percent: float = Field(ge=0, le=100)
    complete: bool
    required_latest_items: list[str]
    tickers: list[TickerFinancialCoverage]

    @model_validator(mode="after")
    def totals_are_consistent(self):
        if self.universe_count != len(self.tickers):
            raise ValueError("universe_count must equal ticker row count")
        if self.covered_count != sum(row.covered for row in self.tickers):
            raise ValueError("covered_count must equal covered ticker row count")
        if self.complete != (self.covered_count == self.universe_count):
            raise ValueError("complete must reflect covered_count/universe_count")
        return self


def build_financial_coverage_report(
    *,
    tickers: list[str],
    items: list[FinancialStatementLineItem],
    as_of: date,
) -> FinancialCoverageReport:
    """Count a ticker when its latest reported period has any financial item."""

    by_ticker_period: dict[str, dict[date, set[str]]] = defaultdict(lambda: defaultdict(set))
    universe = set(tickers)
    for item in items:
        if item.ticker in universe and item.period_end_date <= as_of:
            by_ticker_period[item.ticker][item.period_end_date].add(item.line_item)

    rows: list[TickerFinancialCoverage] = []
    for ticker in sorted(universe):
        periods = by_ticker_period.get(ticker, {})
        latest = max(periods) if periods else None
        present = periods[latest] if latest is not None else set()
        missing = [] if present else [ANY_REPORTED_FINANCIAL_ITEM]
        rows.append(
            TickerFinancialCoverage(
                ticker=ticker,
                covered=not missing,
                latest_period_end_date=latest,
                present_items=sorted(present),
                missing_items=missing,
            )
        )

    covered_count = sum(row.covered for row in rows)
    universe_count = len(rows)
    return FinancialCoverageReport(
        as_of=as_of,
        universe_count=universe_count,
        covered_count=covered_count,
        coverage_percent=(covered_count / universe_count * 100 if universe_count else 100.0),
        complete=covered_count == universe_count,
        required_latest_items=[ANY_REPORTED_FINANCIAL_ITEM],
        tickers=rows,
    )
