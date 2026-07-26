import csv
from datetime import date

from agx_research.universe.collected import CollectedUniverseProvider
from agx_research.universe.provider import MappingUniverseProvider


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
