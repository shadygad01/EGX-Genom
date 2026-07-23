from datetime import date

from agx_research.data.quality import QualityIssueSeverity, validate_price_bars
from agx_research.data.schemas import PriceBar


def bar(trade_date, open_=10.0, high=11.0, low=9.0, close=10.5, volume=100) -> PriceBar:
    return PriceBar(
        ticker="TEST", trade_date=trade_date, open=open_, high=high, low=low, close=close, volume=volume
    )


def test_clean_series_has_no_issues():
    bars = [bar(date(2026, 6, 1)), bar(date(2026, 6, 2))]
    assert validate_price_bars("TEST", bars) == []


def test_non_positive_price_is_an_error():
    issues = validate_price_bars("TEST", [bar(date(2026, 6, 1), open_=0.0)])
    assert any(i.severity == QualityIssueSeverity.ERROR for i in issues)


def test_high_below_low_is_an_error():
    issues = validate_price_bars("TEST", [bar(date(2026, 6, 1), high=8.0, low=9.0)])
    assert any("below low" in i.description for i in issues)


def test_high_below_open_close_is_an_error():
    issues = validate_price_bars("TEST", [bar(date(2026, 6, 1), high=10.0, open_=10.0, close=10.5)])
    assert any("greater of open/close" in i.description for i in issues)


def test_low_above_open_close_is_an_error():
    issues = validate_price_bars("TEST", [bar(date(2026, 6, 1), low=10.0, open_=10.0, close=9.5)])
    assert any("lesser of open/close" in i.description for i in issues)


def test_negative_volume_is_an_error():
    issues = validate_price_bars("TEST", [bar(date(2026, 6, 1), volume=-5)])
    assert any("Negative volume" in i.description for i in issues)


def test_zero_volume_is_a_warning_not_an_error():
    issues = validate_price_bars("TEST", [bar(date(2026, 6, 1), volume=0)])
    assert len(issues) == 1
    assert issues[0].severity == QualityIssueSeverity.WARNING


def test_duplicate_trade_date_is_an_error():
    issues = validate_price_bars("TEST", [bar(date(2026, 6, 1)), bar(date(2026, 6, 1))])
    assert any("Duplicate" in i.description for i in issues)


def test_out_of_order_dates_is_an_error():
    issues = validate_price_bars("TEST", [bar(date(2026, 6, 2)), bar(date(2026, 6, 1))])
    assert any("Out of order" in i.description for i in issues)
