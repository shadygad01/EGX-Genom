import csv
from datetime import date
from pathlib import Path

from agx_research.universe.collected import CollectedUniverseProvider
from agx_research.universe.provider import MappingUniverseProvider
from agx_research.universe.sector import CollectedSectorProvider


def test_mapping_provider_requires_explicit_constituents_and_returns_a_copy():
    provider = MappingUniverseProvider({"COMI": "Commercial International Bank"})
    result = provider.constituents(date(2026, 6, 14))
    result["FAKE"] = "Not real"
    assert provider.constituents(date(2026, 6, 14)) == {"COMI": "Commercial International Bank"}


def _write_constituent_csv(data_dir, index: str, rows: list[tuple[str, str, str]]) -> None:
    path = data_dir / "universe" / f"{index}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "company_name", "as_of_date"])
        writer.writerows(rows)


def test_collected_provider_returns_empty_when_nothing_collected(tmp_path):
    assert CollectedUniverseProvider(tmp_path).constituents(date(2026, 6, 14)) == {}


def test_collected_provider_returns_latest_snapshot_at_or_before_as_of(tmp_path):
    _write_constituent_csv(
        tmp_path,
        "EGX30",
        [
            ("COMI", "Commercial International Bank", "2026-01-01"),
            ("COMI", "Commercial International Bank", "2026-06-01"),
            ("ETEL", "Telecom Egypt", "2026-06-01"),
        ],
    )
    assert CollectedUniverseProvider(tmp_path).constituents(date(2026, 6, 14)) == {
        "COMI": "Commercial International Bank",
        "ETEL": "Telecom Egypt",
    }


def test_collected_provider_never_looks_ahead_of_as_of(tmp_path):
    _write_constituent_csv(
        tmp_path,
        "EGX30",
        [
            ("COMI", "Commercial International Bank", "2026-01-01"),
            ("NEWCO", "New Constituent Added Later", "2026-12-01"),
        ],
    )
    assert CollectedUniverseProvider(tmp_path).constituents(date(2026, 6, 14)) == {
        "COMI": "Commercial International Bank"
    }


def test_default_provider_combines_all_collected_indexes(tmp_path):
    _write_constituent_csv(
        tmp_path, "EGX30", [("COMI", "Commercial International Bank", "2026-06-01")]
    )
    _write_constituent_csv(tmp_path, "EGX70", [("ORAS", "Orascom", "2026-06-01")])
    assert CollectedUniverseProvider(tmp_path).constituents(date(2026, 6, 14)) == {
        "COMI": "Commercial International Bank",
        "ORAS": "Orascom",
    }


def _write_sector_csv(data_dir, rows: list[tuple[str, str, str, str]]) -> None:
    path = data_dir / "universe" / "sector_membership.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticker", "sector", "source_id", "observed_date"])
        writer.writerows(rows)


def test_collected_sector_provider_falls_back_to_placeholder_when_nothing_collected(tmp_path):
    provider = CollectedSectorProvider(tmp_path)
    # COMI is in the static placeholder -- never worse than before this
    # provider existed, even before any real sector data is collected.
    assert provider.sector_of("COMI", date(2026, 6, 14)) == "Banks"
    assert provider.sector_of("NOT_A_REAL_TICKER", date(2026, 6, 14)) is None


def test_collected_sector_provider_prefers_real_collected_data_over_placeholder(tmp_path):
    _write_sector_csv(
        tmp_path,
        [("ARCC", "Building Materials", "chief_egx_financials", "2026-08-02")],
    )
    provider = CollectedSectorProvider(tmp_path)
    assert provider.sector_of("ARCC", date(2026, 6, 14)) == "Building Materials"
    # A ticker only the placeholder knows about is still covered.
    assert provider.sector_of("COMI", date(2026, 6, 14)) == "Banks"


def test_collected_sector_provider_custom_fallback_never_used_when_collected():
    provider = CollectedSectorProvider(
        Path("/nonexistent-data-dir-for-this-test"), fallback={"COMI": "Custom Sector"}
    )
    assert provider.sector_of("COMI", date(2026, 6, 14)) == "Custom Sector"
    assert provider.sector_of("HRHO", date(2026, 6, 14)) is None
