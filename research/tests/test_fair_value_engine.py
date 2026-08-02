from datetime import date

from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.valuation import FairValueEngine, compute_valuation_metrics


class Provider:
    def __init__(self, items):
        self.items = items

    def get_line_items(self, ticker, start, end, *, statement_type=None):
        return [item for item in self.items if start <= item.period_end_date <= end]


def _items():
    values = {
        2023: {"revenue": 1000, "operating_income": 220, "net_income": 150, "free_cash_flow": 130, "ebitda": 260, "total_equity": 700, "cash_and_equivalents": 150, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.5, "dividend_per_share": .5},
        2024: {"revenue": 1100, "operating_income": 240, "net_income": 165, "free_cash_flow": 140, "ebitda": 280, "total_equity": 780, "cash_and_equivalents": 170, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.65, "dividend_per_share": .55},
        2025: {"revenue": 1200, "operating_income": 260, "net_income": 180, "free_cash_flow": 150, "ebitda": 300, "total_equity": 860, "cash_and_equivalents": 190, "total_debt": 100, "shares_outstanding": 100, "eps_diluted": 1.8, "dividend_per_share": .6},
    }
    return [
        FinancialStatementLineItem(ticker="TEST", period_end_date=date(year, 12, 31), period_type="ANNUAL", statement_type="TEST", line_item=name, value=value)
        for year, row in values.items() for name, value in row.items()
    ]


def test_ported_engine_runs_seven_models_and_robustly_blends_at_least_three():
    result = FairValueEngine(Provider(_items())).value("TEST", date(2026, 6, 30), sector="Banks")
    assert result is not None
    assert len(result.included_models) >= 3
    assert result.bear_case <= result.base_case <= result.bull_case
    assert result.assumptions_version == "smartlist-ive-v2.2"
    assert result.models["dcf"] is None
    assert result.models["earnings_power"] is None
    assert result.models["ev_ebitda"] is None


def test_engine_refuses_to_fabricate_value_without_share_count():
    items = [item for item in _items() if item.line_item != "shares_outstanding"]
    assert FairValueEngine(Provider(items)).value("TEST", date(2026, 6, 30)) is None


def test_engine_is_point_in_time_and_cannot_read_future_periods():
    future = FinancialStatementLineItem(ticker="TEST", period_end_date=date(2027, 12, 31), period_type="ANNUAL", statement_type="TEST", line_item="eps_diluted", value=999)
    baseline = FairValueEngine(Provider(_items())).value("TEST", date(2026, 6, 30))
    with_future = FairValueEngine(Provider([*_items(), future])).value("TEST", date(2026, 6, 30))
    assert with_future == baseline


def test_latest_four_quarters_are_aggregated_as_ttm_not_treated_as_one_quarter():
    quarterly = []
    for month in (3, 6, 9, 12):
        for name, value in {
            "revenue": 300, "operating_income": 65, "free_cash_flow": 37.5,
            "ebitda": 75, "total_equity": 860, "cash_and_equivalents": 190,
            "total_debt": 100, "shares_outstanding": 100, "eps_diluted": .45,
        }.items():
            quarterly.append(FinancialStatementLineItem(
                ticker="TEST", period_end_date=date(2025, month, 30 if month != 12 else 31),
                period_type="QUARTERLY", statement_type="TEST", line_item=name, value=value,
            ))
    result = FairValueEngine(Provider(quarterly)).value("TEST", date(2026, 6, 30))
    assert result is not None
    assert result.models["pe"] == 1.8 * 11.0


def test_decision_metrics_expose_dcf_ev_ebitda_and_price_to_book_without_estimation():
    provider = Provider(_items())
    engine = FairValueEngine(provider)
    result = compute_valuation_metrics(
        "TEST", date(2026, 6, 30), 10.0, provider, engine, sector="Materials"
    )
    assert result.dcf_per_share is not None
    assert result.enterprise_value == 910.0
    assert result.ebitda == 300
    assert result.ev_to_ebitda == 910 / 300
    assert result.price_to_book == 1000 / 860
    assert result.weighted_fair_value is not None


def test_market_snapshot_does_not_make_financial_statements_look_fresh():
    stale = [item.model_copy(update={"period_end_date": date(2023, 12, 31)}) for item in _items()]
    snapshot = FinancialStatementLineItem(
        ticker="TEST",
        period_end_date=date(2026, 6, 30),
        period_type="SNAPSHOT",
        statement_type="MARKET_FUNDAMENTALS",
        line_item="market_pe",
        value=8.0,
    )
    provider = Provider([*stale, snapshot])
    engine = FairValueEngine(provider)

    assert engine.value("TEST", date(2026, 6, 30)) is None
    metrics = compute_valuation_metrics("TEST", date(2026, 6, 30), 10.0, provider, engine)
    assert metrics.latest_financial_period == date(2023, 12, 31)
    assert metrics.latest_market_snapshot_date == date(2026, 6, 30)
    assert metrics.market_pe == 8.0
