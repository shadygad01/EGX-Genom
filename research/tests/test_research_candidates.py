from datetime import date

from agx_research.meta.readiness import DecisionReadiness
from agx_research.meta.research_candidates import build_research_candidates
from agx_research.valuation import ValuationMetrics


def _row(ticker: str, price: float, fair_value: float | None, gap: float | None, blockers: list[str] | None = None) -> DecisionReadiness:
    valuation = None
    if fair_value is not None:
        valuation = ValuationMetrics(
            ticker=ticker,
            as_of=date(2026, 8, 13),
            current_price=price,
            weighted_fair_value=fair_value,
            included_models=["pe", "pb", "residual_income"],
            market_pe=5.0,
        )
    return DecisionReadiness(
        ticker=ticker,
        as_of=date(2026, 8, 13),
        status="degraded",
        decision="abstain",
        price_observations=120,
        latest_price_date=date(2026, 8, 12),
        financial_periods=4,
        fair_value_available=fair_value is not None,
        valuation=valuation,
        price_vs_fair_value_pct=gap,
        macro_series=0,
        blockers=blockers or ["Missing macro series"],
    )


def test_builds_only_undervalued_multi_model_candidates():
    rows = [
        _row("CHEAP", 90.0, 100.0, -0.10),
        _row("EXPENSIVE", 110.0, 100.0, 0.10),
        _row("MISSING", 90.0, None, None),
    ]
    candidates = build_research_candidates(rows)
    assert [candidate.ticker for candidate in candidates] == ["CHEAP"]
    assert candidates[0].expected_return == 0.1111
    assert candidates[0].decision == "watchlist"
    assert candidates[0].status == "research_candidate"
    assert candidates[0].primary_blockers == ["Missing macro series"]


def test_candidate_does_not_discard_execution_blockers():
    candidate = build_research_candidates([_row("CHEAP", 90.0, 100.0, -0.10, ["No FX", "No news"])])[0]
    assert candidate.primary_blockers == ["No FX", "No news"]
    assert candidate.next_actions == []
