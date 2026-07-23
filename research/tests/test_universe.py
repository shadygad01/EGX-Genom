from datetime import date

from agx_research.universe.static import EGX30_UNIVERSE_PLACEHOLDER, StaticUniverseProvider


def test_static_provider_returns_placeholder_by_default():
    provider = StaticUniverseProvider()
    assert provider.constituents(date(2026, 6, 14)) == EGX30_UNIVERSE_PLACEHOLDER


def test_static_provider_accepts_custom_constituents():
    provider = StaticUniverseProvider({"COMI": "Commercial International Bank"})
    assert provider.constituents(date(2026, 6, 14)) == {"COMI": "Commercial International Bank"}


def test_returned_dict_is_a_copy():
    provider = StaticUniverseProvider()
    result = provider.constituents(date(2026, 6, 14))
    result["FAKE"] = "Not real"
    assert "FAKE" not in provider.constituents(date(2026, 6, 14))
