"""Coverage for `patterns.community_price_seed.materialize_community_price_seed`
-- the idempotent-merge-into-data-dir contract it shares with
`universe.bootstrap.materialize_universe_seed()`."""

from __future__ import annotations

import csv
import json

import pytest

from agx_research.patterns.community_price_seed import (
    REQUIRED_PRICE_COLUMNS,
    materialize_community_price_seed,
)


def _write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _make_seed(tmp_path, *, prices=None, events=None, sectors=None, provenance=None):
    seed_dir = tmp_path / "seed"
    normalized = seed_dir / "normalized"
    prices = prices or {
        "T": [
            {"date": "2024-01-02", "open": "10", "high": "11", "low": "9", "close": "10.5", "volume": "1000"},
            {"date": "2024-01-03", "open": "10.5", "high": "11", "low": "10", "close": "10.8", "volume": "1100"},
        ]
    }
    for ticker, rows in prices.items():
        _write_csv(normalized / "prices" / f"{ticker}.csv", REQUIRED_PRICE_COLUMNS, rows)

    if events is not None:
        _write_csv(
            normalized / "corporate_events.csv",
            ["ticker", "date", "event_type", "description", "details_json"],
            events,
        )
    if sectors is not None:
        _write_csv(normalized / "sector_membership.csv", ["ticker", "sector"], sectors)
    if provenance is not None:
        (seed_dir / "PROVENANCE.json").write_text(json.dumps(provenance), encoding="utf-8")
    return seed_dir


def test_raises_when_seed_directory_does_not_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        materialize_community_price_seed(tmp_path / "does_not_exist", tmp_path / "data")


def test_materializes_prices_into_a_fresh_data_dir(tmp_path):
    seed_dir = _make_seed(tmp_path)
    data_dir = tmp_path / "data"

    summary = materialize_community_price_seed(seed_dir, data_dir)

    assert summary["tickers_written"] == 1
    target = data_dir / "prices" / "T.csv"
    assert target.exists()
    with target.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["date"] for r in rows] == ["2024-01-02", "2024-01-03"]
    assert rows[0]["close"] == "10.5"


def test_merge_is_idempotent_and_preserves_pre_existing_rows_not_in_the_seed(tmp_path):
    seed_dir = _make_seed(tmp_path)
    data_dir = tmp_path / "data"

    # A pre-existing row for a date the seed does NOT cover must survive
    # the merge -- this is a merge, not an overwrite.
    _write_csv(
        data_dir / "prices" / "T.csv", REQUIRED_PRICE_COLUMNS,
        [{"date": "2023-12-29", "open": "9", "high": "9.5", "low": "8.8", "close": "9.2", "volume": "500"}],
    )

    materialize_community_price_seed(seed_dir, data_dir)
    materialize_community_price_seed(seed_dir, data_dir)  # running twice must not duplicate rows

    with (data_dir / "prices" / "T.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["date"] for r in rows] == ["2023-12-29", "2024-01-02", "2024-01-03"]


def test_seed_values_overwrite_pre_existing_rows_for_the_same_date(tmp_path):
    seed_dir = _make_seed(tmp_path)
    data_dir = tmp_path / "data"
    _write_csv(
        data_dir / "prices" / "T.csv", REQUIRED_PRICE_COLUMNS,
        [{"date": "2024-01-02", "open": "1", "high": "1", "low": "1", "close": "1", "volume": "1"}],
    )

    materialize_community_price_seed(seed_dir, data_dir)

    with (data_dir / "prices" / "T.csv").open(newline="", encoding="utf-8") as handle:
        rows = {r["date"]: r for r in csv.DictReader(handle)}
    assert rows["2024-01-02"]["close"] == "10.5"


def test_corporate_events_and_sector_membership_are_merged(tmp_path):
    seed_dir = _make_seed(
        tmp_path,
        events=[{"ticker": "T", "date": "2024-01-02", "event_type": "dividend", "description": "d", "details_json": "{}"}],
        sectors=[{"ticker": "T", "sector": "Banks"}],
    )
    data_dir = tmp_path / "data"

    summary = materialize_community_price_seed(seed_dir, data_dir)

    assert summary["corporate_events_written"] == 1
    assert summary["sectors_written"] == 1
    with (data_dir / "corporate_events.csv").open(newline="", encoding="utf-8") as handle:
        events = list(csv.DictReader(handle))
    assert events[0]["ticker"] == "T"
    with (data_dir / "sectors" / "sector_membership.csv").open(newline="", encoding="utf-8") as handle:
        sectors = list(csv.DictReader(handle))
    assert sectors[0] == {"ticker": "T", "sector": "Banks"}


def test_sector_merge_preserves_a_ticker_not_present_in_the_seed(tmp_path):
    seed_dir = _make_seed(tmp_path, sectors=[{"ticker": "T", "sector": "Banks"}])
    data_dir = tmp_path / "data"
    _write_csv(data_dir / "sectors" / "sector_membership.csv", ["ticker", "sector"], [{"ticker": "OTHER", "sector": "Retail"}])

    materialize_community_price_seed(seed_dir, data_dir)

    with (data_dir / "sectors" / "sector_membership.csv").open(newline="", encoding="utf-8") as handle:
        sectors = {r["ticker"]: r["sector"] for r in csv.DictReader(handle)}
    assert sectors == {"T": "Banks", "OTHER": "Retail"}


def test_provenance_manifest_is_copied_through_when_present(tmp_path):
    seed_dir = _make_seed(tmp_path, provenance={"source_repo_url": "https://example.invalid/repo"})
    data_dir = tmp_path / "data"

    materialize_community_price_seed(seed_dir, data_dir)

    written = json.loads((data_dir / "community_price_seed_provenance.json").read_text(encoding="utf-8"))
    assert written["source_repo_url"] == "https://example.invalid/repo"


def test_no_provenance_file_written_when_seed_has_none(tmp_path):
    seed_dir = _make_seed(tmp_path)
    data_dir = tmp_path / "data"

    materialize_community_price_seed(seed_dir, data_dir)

    assert not (data_dir / "community_price_seed_provenance.json").exists()


def test_price_csv_with_wrong_columns_raises_value_error(tmp_path):
    seed_dir = tmp_path / "seed"
    _write_csv(seed_dir / "normalized" / "prices" / "T.csv", ["date", "close"], [{"date": "2024-01-02", "close": "10"}])
    data_dir = tmp_path / "data"

    with pytest.raises(ValueError, match="expected columns"):
        materialize_community_price_seed(seed_dir, data_dir)
