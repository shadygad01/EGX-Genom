from datetime import date

from agx_research.data.schemas import MacroObservation
from agx_research.decision_service.country_risk import (
    CountryRiskSeverity,
    SovereignRatingAction,
    assess_country_risk,
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
