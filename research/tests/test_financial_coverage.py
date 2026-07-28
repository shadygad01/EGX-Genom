from datetime import date

from agx_research.financials.coverage import build_financial_coverage_report
from agx_research.financials.schema import FinancialStatementLineItem


def item(ticker: str, period: date, line_item: str) -> FinancialStatementLineItem:
    return FinancialStatementLineItem(
        ticker=ticker,
        period_end_date=period,
        period_type="QUARTERLY",
        statement_type="BALANCE_SHEET",
        line_item=line_item,
        value=1,
        currency="EGP",
    )


def test_report_accepts_any_financial_item_in_latest_period():
    old = date(2025, 12, 31)
    latest = date(2026, 3, 31)
    rows = [
        *(
            item("COMI", old, name)
            for name in (
                "net_income",
                "total_assets",
                "total_liabilities",
                "total_equity",
            )
        ),
        item("COMI", latest, "net_income"),
    ]

    report = build_financial_coverage_report(
        tickers=["COMI", "MFPC"], items=rows, as_of=date(2026, 6, 30)
    )

    assert report.covered_count == 1
    assert report.coverage_percent == 50
    assert report.complete is False
    assert report.tickers[0].latest_period_end_date == latest
    assert report.tickers[0].missing_items == []
    assert report.tickers[1].latest_period_end_date is None
    assert report.tickers[1].missing_items == ["any_reported_financial_item"]


def test_report_is_complete_only_when_every_ticker_is_covered():
    period = date(2026, 3, 31)
    rows = [item(ticker, period, "net_income") for ticker in ("COMI", "MFPC")]

    report = build_financial_coverage_report(
        tickers=["MFPC", "COMI"], items=rows, as_of=date(2026, 6, 30)
    )

    assert report.covered_count == 2
    assert report.coverage_percent == 100
    assert report.complete is True
    assert [row.ticker for row in report.tickers] == ["COMI", "MFPC"]
