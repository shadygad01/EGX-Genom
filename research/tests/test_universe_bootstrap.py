import csv
import json
from datetime import date
from pathlib import Path

import pytest

from agx_research.production import ExecutionMode, ProductionPipeline
from agx_research.universe.bootstrap import materialize_universe_seed
from agx_research.universe.collected import CollectedUniverseProvider

SEED_DIR = Path(__file__).resolve().parents[1] / "data" / "universe"
SNAPSHOT_DATE = date(2026, 7, 26)


def _rows(index: str) -> list[dict[str, str]]:
    with (SEED_DIR / f"{index}.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_reviewed_seed_is_complete_unique_and_traceable():
    egx30 = _rows("EGX30")
    egx70 = _rows("EGX70")
    assert len(egx30) == 31
    assert len(egx70) == 70
    assert sum(float(row["weight_percent"]) for row in egx30) == pytest.approx(100.0)

    all_rows = [*egx30, *egx70]
    assert all(row["ticker"] and row["company_name"] and row["isin"] for row in all_rows)
    assert all(row["as_of_date"] == SNAPSHOT_DATE.isoformat() for row in all_rows)
    assert len({row["ticker"] for row in all_rows}) == 101
    assert len({row["isin"] for row in all_rows}) == 101
    assert not ({row["ticker"] for row in egx30} & {row["ticker"] for row in egx70})

    manifest = json.loads((SEED_DIR / "source_manifest.json").read_text(encoding="utf-8"))
    assert manifest["collection_method"] == "manual_review"
    assert manifest["indexes"]["EGX30"]["source_url"].startswith("https://www.egx.com.eg/")
    assert manifest["indexes"]["EGX70"]["source_url"].startswith("https://egx.com.eg/")


def test_seed_materializes_into_the_single_runtime_provider(tmp_path):
    assert materialize_universe_seed(SEED_DIR, tmp_path) == 101
    provider = CollectedUniverseProvider(tmp_path)
    assert len(provider.constituents(SNAPSHOT_DATE)) == 101
    assert provider.constituents(date(2026, 7, 25)) == {}
    assert (tmp_path / "universe" / "source_manifest.json").exists()


def test_packaged_universe_flows_to_every_ticker_artifact(tmp_path):
    data_dir = tmp_path / "data"
    dashboard = tmp_path / "dashboard"
    materialize_universe_seed(SEED_DIR, data_dir)

    pipeline = ProductionPipeline(data_dir=data_dir)
    pipeline.run(SNAPSHOT_DATE, mode=ExecutionMode.MOCK, dashboard_out=dashboard)

    universe = json.loads((dashboard / "universe.json").read_text())
    market_state = json.loads((dashboard / "market_state.json").read_text())
    readiness = json.loads((dashboard / "decision_readiness.json").read_text())
    expected = set(universe["tickers"])
    assert universe["count"] == 101
    assert set(market_state["dataset_snapshot"]["tickers"]) == expected
    assert {row["ticker"] for row in readiness} == expected
