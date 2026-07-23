import csv
from datetime import date

from agx_research.universe.collected import CollectedUniverseProvider, FallbackUniverseProvider
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


def _write_constituent_csv(data_dir, index: str, rows: list[tuple[str, str, str]]) -> None:
    path = data_dir / "universe" / f"{index}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "company_name", "as_of_date"])
        writer.writerows(rows)


def test_collected_provider_returns_empty_when_nothing_collected(tmp_path):
    provider = CollectedUniverseProvider(tmp_path, index="EGX30")
    assert provider.constituents(date(2026, 6, 14)) == {}


def test_collected_provider_returns_latest_snapshot_at_or_before_as_of(tmp_path):
    _write_constituent_csv(
        tmp_path, "EGX30",
        [
            ("COMI", "Commercial International Bank", "2026-01-01"),
            ("COMI", "Commercial International Bank", "2026-06-01"),
            ("ETEL", "Telecom Egypt", "2026-06-01"),
        ],
    )
    provider = CollectedUniverseProvider(tmp_path, index="EGX30")
    assert provider.constituents(date(2026, 6, 14)) == {
        "COMI": "Commercial International Bank",
        "ETEL": "Telecom Egypt",
    }


def test_collected_provider_never_looks_ahead_of_as_of(tmp_path):
    _write_constituent_csv(
        tmp_path, "EGX30",
        [
            ("COMI", "Commercial International Bank", "2026-01-01"),
            ("NEWCO", "New Constituent Added Later", "2026-12-01"),
        ],
    )
    provider = CollectedUniverseProvider(tmp_path, index="EGX30")
    result = provider.constituents(date(2026, 6, 14))
    assert result == {"COMI": "Commercial International Bank"}
    assert "NEWCO" not in result


def test_collected_provider_empty_when_every_snapshot_postdates_as_of(tmp_path):
    _write_constituent_csv(tmp_path, "EGX30", [("COMI", "Commercial International Bank", "2027-01-01")])
    provider = CollectedUniverseProvider(tmp_path, index="EGX30")
    assert provider.constituents(date(2026, 6, 14)) == {}


def test_fallback_provider_prefers_first_non_empty_result(tmp_path):
    _write_constituent_csv(tmp_path, "EGX30", [("COMI", "Commercial International Bank", "2026-01-01")])
    fallback = FallbackUniverseProvider(
        [CollectedUniverseProvider(tmp_path, index="EGX30"), StaticUniverseProvider()]
    )
    assert fallback.constituents(date(2026, 6, 14)) == {"COMI": "Commercial International Bank"}


def test_fallback_provider_falls_back_when_collected_is_empty(tmp_path):
    fallback = FallbackUniverseProvider(
        [CollectedUniverseProvider(tmp_path, index="EGX30"), StaticUniverseProvider()]
    )
    assert fallback.constituents(date(2026, 6, 14)) == EGX30_UNIVERSE_PLACEHOLDER
