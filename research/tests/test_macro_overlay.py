from datetime import date

from agx_research.data.schemas import MacroObservation
from agx_research.decision_service.macro_overlay import assess_macro_overlay


def obs(series_id, values):
    return [
        MacroObservation(series_id=series_id, observation_date=date(year, 12, 31), value=value)
        for year, value in values
    ]


def test_weighted_macro_overlay_is_defensive_and_explainable():
    overlay = assess_macro_overlay(
        {
            "egypt_official_fx_egp_per_usd": obs("fx", [(2024, 30), (2025, 50)]),
            "egypt_total_cpi_yoy": obs("cpi", [(2024, 10), (2025, 15)]),
            "egypt_external_debt_usd": obs("debt", [(2024, 155), (2025, 164)]),
            "egypt_real_gdp_growth": obs("gdp", [(2024, 2), (2025, 4)]),
        },
        date(2026, 8, 2),
    )
    assert overlay.decision == "defensive"
    assert overlay.exposure_multiplier == 0.5
    assert overlay.available_weight == 0.60
    assert sum(row.effective_weight for row in overlay.contributions) == 1.0
    assert {row.factor: row.impact for row in overlay.contributions} == {
        "currency": "adverse",
        "inflation": "adverse",
        "external_debt": "adverse",
        "real_growth": "supportive",
    }


def test_insufficient_history_does_not_invent_a_portfolio_adjustment():
    overlay = assess_macro_overlay(
        {"egypt_external_debt_usd": obs("debt", [(2025, 164)])}, date(2026, 8, 2)
    )
    assert overlay.decision == "insufficient_data"
    assert overlay.exposure_multiplier == 1.0
    assert overlay.contributions == []
