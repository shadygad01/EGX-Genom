from datetime import date

from agx_research.data.schemas import MacroObservation
from agx_research.decision_service.country_risk import (
    REAL_CURRENCY_SERIES_ID,
    CountryRiskSeverity,
    SovereignRatingAction,
    assess_country_risk,
    has_sufficient_currency_data,
)


def _obs(series_id: str, d: date, value: float) -> MacroObservation:
    return MacroObservation(series_id=series_id, observation_date=d, value=value)


def test_normal_when_currency_stable_and_no_rating_actions():
    macro_series = {
        "EGP_USD": [
            _obs("EGP_USD", date(2026, 1, 1), 49.0),
            _obs("EGP_USD", date(2026, 6, 1), 49.5),
        ]
    }
    result = assess_country_risk(macro_series, as_of=date(2026, 6, 14))
    assert result.severity == CountryRiskSeverity.NORMAL
    assert result.reasons == []


def test_deteriorating_on_sharp_currency_move():
    macro_series = {
        "EGP_USD": [
            _obs("EGP_USD", date(2026, 1, 1), 49.0),
            _obs("EGP_USD", date(2026, 6, 1), 55.0),  # ~12% depreciation
        ]
    }
    result = assess_country_risk(macro_series, as_of=date(2026, 6, 14))
    assert result.severity == CountryRiskSeverity.DETERIORATING
    assert any("EGP_USD" in reason for reason in result.reasons)


def test_currency_move_alone_never_reaches_crisis():
    macro_series = {
        "EGP_USD": [
            _obs("EGP_USD", date(2026, 1, 1), 40.0),
            _obs("EGP_USD", date(2026, 6, 1), 80.0),  # 100% depreciation, no rating action
        ]
    }
    result = assess_country_risk(macro_series, as_of=date(2026, 6, 14))
    assert result.severity == CountryRiskSeverity.DETERIORATING  # never CRISIS without a rating action


def test_crisis_requires_a_real_downgrade():
    result = assess_country_risk(
        {},
        as_of=date(2026, 6, 14),
        rating_actions=[
            SovereignRatingAction(
                agency="Moody's", action="downgrade", announced_at=date(2026, 5, 1)
            )
        ],
    )
    assert result.severity == CountryRiskSeverity.CRISIS
    assert any("downgrade" in reason.lower() for reason in result.reasons)


def test_negative_outlook_without_downgrade_is_only_deteriorating():
    result = assess_country_risk(
        {},
        as_of=date(2026, 6, 14),
        rating_actions=[
            SovereignRatingAction(
                agency="Fitch", action="affirm", outlook="negative", announced_at=date(2026, 5, 1)
            )
        ],
    )
    assert result.severity == CountryRiskSeverity.DETERIORATING


def test_stale_rating_action_outside_lookback_is_ignored():
    result = assess_country_risk(
        {},
        as_of=date(2026, 6, 14),
        rating_actions=[
            SovereignRatingAction(
                agency="S&P", action="downgrade", announced_at=date(2020, 1, 1)
            )
        ],
    )
    assert result.severity == CountryRiskSeverity.NORMAL


def test_empty_series_is_normal_not_fabricated():
    result = assess_country_risk({}, as_of=date(2026, 6, 14))
    assert result.severity == CountryRiskSeverity.NORMAL
    assert result.reasons == []


def test_real_production_series_id_is_recognized_not_just_mock_id():
    # Regression test (2026-07-31): real LIVE runs collect EGP/USD from
    # World Bank under `egypt_official_fx_egp_per_usd`
    # (production/collector_plan.py's LIVE_WORLDBANK_INDICATORS), never the
    # mock fixture's `EGP_USD` -- this used to mean a real run's own,
    # successfully-collected FX data was invisible to this assessment.
    macro_series = {
        REAL_CURRENCY_SERIES_ID: [
            _obs(REAL_CURRENCY_SERIES_ID, date(2026, 1, 1), 49.0),
            _obs(REAL_CURRENCY_SERIES_ID, date(2026, 6, 1), 55.0),  # ~12% depreciation
        ]
    }
    result = assess_country_risk(macro_series, as_of=date(2026, 6, 14))
    assert result.severity == CountryRiskSeverity.DETERIORATING
    assert any(REAL_CURRENCY_SERIES_ID in reason for reason in result.reasons)
    assert has_sufficient_currency_data(macro_series) is True


def test_has_sufficient_currency_data_false_when_neither_alias_present():
    assert has_sufficient_currency_data({"some_other_series": []}) is False
    assert has_sufficient_currency_data({}) is False


def test_explicit_currency_series_id_override_still_wins():
    macro_series = {
        "custom_fx_series": [
            _obs("custom_fx_series", date(2026, 1, 1), 10.0),
            _obs("custom_fx_series", date(2026, 6, 1), 20.0),
        ],
        "EGP_USD": [
            _obs("EGP_USD", date(2026, 1, 1), 49.0),
            _obs("EGP_USD", date(2026, 6, 1), 49.1),
        ],
    }
    result = assess_country_risk(
        macro_series, as_of=date(2026, 6, 14), currency_series_id="custom_fx_series"
    )
    assert result.severity == CountryRiskSeverity.DETERIORATING
    assert any("custom_fx_series" in reason for reason in result.reasons)
