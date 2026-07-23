import csv
from datetime import date

from agx_research.financials.collected import CollectedFinancialStatementProvider


def _write_line_items_csv(data_dir, ticker: str, rows: list[tuple[str, str, str, str, str, str]]) -> None:
    path = data_dir / "financial_statements" / f"{ticker}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["period_end_date", "period_type", "statement_type", "line_item", "value", "currency"]
        )
        writer.writerows(rows)


def test_returns_empty_when_nothing_collected(tmp_path):
    provider = CollectedFinancialStatementProvider(tmp_path)
    assert provider.get_line_items("COMI", date(2026, 1, 1), date(2026, 12, 31)) == []


def test_returns_items_in_date_range_sorted(tmp_path):
    _write_line_items_csv(
        tmp_path, "COMI",
        [
            ("2026-06-30", "QUARTERLY", "INCOME_STATEMENT", "net_income", "150000", "EGP"),
            ("2026-06-30", "QUARTERLY", "INCOME_STATEMENT", "revenue", "1000000", "EGP"),
            ("2025-12-31", "ANNUAL", "INCOME_STATEMENT", "revenue", "3800000", "EGP"),
        ],
    )
    provider = CollectedFinancialStatementProvider(tmp_path)
    items = provider.get_line_items("COMI", date(2026, 1, 1), date(2026, 12, 31))
    assert len(items) == 2
    assert [i.period_end_date for i in items] == [date(2026, 6, 30), date(2026, 6, 30)]
    assert [i.line_item for i in items] == ["net_income", "revenue"]  # sorted by line_item too


def test_filters_by_statement_type(tmp_path):
    _write_line_items_csv(
        tmp_path, "COMI",
        [
            ("2026-06-30", "QUARTERLY", "INCOME_STATEMENT", "revenue", "1000000", "EGP"),
            ("2026-06-30", "QUARTERLY", "BALANCE_SHEET", "total_assets", "5000000", "EGP"),
        ],
    )
    provider = CollectedFinancialStatementProvider(tmp_path)
    items = provider.get_line_items(
        "COMI", date(2026, 1, 1), date(2026, 12, 31), statement_type="BALANCE_SHEET"
    )
    assert len(items) == 1
    assert items[0].line_item == "total_assets"


def test_never_looks_outside_requested_date_range(tmp_path):
    _write_line_items_csv(
        tmp_path, "COMI",
        [("2025-01-01", "ANNUAL", "INCOME_STATEMENT", "revenue", "3000000", "EGP")],
    )
    provider = CollectedFinancialStatementProvider(tmp_path)
    assert provider.get_line_items("COMI", date(2026, 1, 1), date(2026, 12, 31)) == []


def test_missing_currency_column_defaults_to_egp(tmp_path):
    path = tmp_path / "financial_statements" / "COMI.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["period_end_date", "period_type", "statement_type", "line_item", "value"])
        writer.writerow(["2026-06-30", "QUARTERLY", "INCOME_STATEMENT", "revenue", "1000000"])
    provider = CollectedFinancialStatementProvider(tmp_path)
    items = provider.get_line_items("COMI", date(2026, 1, 1), date(2026, 12, 31))
    assert items[0].currency == "EGP"
