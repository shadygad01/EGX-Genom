from datetime import date

from agx_research.data.point_in_time import is_knowable, known_as_of


def test_unmapped_source_defaults_to_zero_lag():
    assert known_as_of(date(2026, 6, 14)) == date(2026, 6, 14)
    assert is_knowable(date(2026, 6, 14), date(2026, 6, 14)) is True


def test_worldbank_lag_is_applied():
    obs = date(2025, 12, 31)
    assert known_as_of(obs, source="worldbank") == date(2026, 1, 30)
    assert is_knowable(obs, date(2026, 1, 29), source="worldbank") is False
    assert is_knowable(obs, date(2026, 1, 30), source="worldbank") is True


def test_fred_has_no_assumed_lag():
    obs = date(2026, 6, 14)
    assert is_knowable(obs, date(2026, 6, 14), source="fred") is True


def test_unrecognized_source_falls_back_to_default():
    assert known_as_of(date(2026, 1, 1), source="some_new_source") == date(2026, 1, 1)
