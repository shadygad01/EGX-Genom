from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "research" / "scripts" / "build_price_feasibility_evidence.py"
OUTPUT = ROOT / "docs" / "evidence" / "egx-price-feasibility-2026-07-26"


def _load_script():
    spec = importlib.util.spec_from_file_location("price_feasibility", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_price_feasibility_artifacts_cover_canonical_universe() -> None:
    module = _load_script()
    module.main()

    coverage = json.loads((OUTPUT / "coverage_report.json").read_text(encoding="utf-8"))
    matrix = json.loads((OUTPUT / "price_source_matrix.json").read_text(encoding="utf-8"))

    assert coverage["universe"]["company_count"] == 100
    assert coverage["universe"]["security_ticker_count"] == 101
    assert coverage["universe"]["dual_security_issuer"]["tickers"] == ["VLMR", "VLMRA"]
    assert coverage["verdict"] == "A_technical_B_licensed"
    assert len(coverage["sources"]) == 28
    assert len(matrix["rows"]) == 28
    assert matrix["summary"]["free_legal_complete_sources"] == 0
    assert matrix["summary"]["free_technical_complete_architectures"] == 1
    architecture = coverage["technical_architecture"]
    assert architecture["remaining_missing_count"] == 0
    assert architecture["historical_retrieval_coverage_percent"] == 100.0
    assert architecture["fresh_daily_completed_session"]["coverage_percent"] == 100.0

    required = {"ticker", "supported", "missing", "reason"}
    for source in coverage["sources"]:
        assert len(source["ticker_results"]) == 101
        assert all(set(result) == required for result in source["ticker_results"])


def test_known_coverage_counts_are_not_confused_with_legal_suitability() -> None:
    module = _load_script()
    module.main()
    coverage = json.loads((OUTPUT / "coverage_report.json").read_text(encoding="utf-8"))
    by_source = {source["source"]: source for source in coverage["sources"]}

    assert by_source["Twelve Data"]["supported_count"] == 101
    assert by_source["EOD Historical Data (EODHD)"]["supported_count"] == 99
    assert by_source["StockAnalysis.com"]["supported_count"] == 99
    assert by_source["Kaggle: EGX Egyptian Stocks 2021-2026"]["supported_count"] == 80
    assert by_source["Kaggle: Egyptian Stock Exchange-EGX30"]["supported_count"] == 31
    assert by_source["Yahoo Finance / yfinance"]["supported_count"] == 91


def test_live_probe_union_covers_every_security() -> None:
    yahoo = json.loads((OUTPUT / "yahoo_live_probe.json").read_text(encoding="utf-8"))
    stockanalysis = json.loads(
        (OUTPUT / "stockanalysis_live_probe.json").read_text(encoding="utf-8")
    )

    assert yahoo["requested_count"] == 101
    assert yahoo["supported_count"] == 91
    assert yahoo["sample_supported_count"] == 10
    assert stockanalysis["requested_count"] == 101
    assert stockanalysis["supported_count"] == 99

    yahoo_ok = {result["ticker"] for result in yahoo["results"] if result["supported"]}
    stockanalysis_ok = {
        result["ticker"] for result in stockanalysis["results"] if result["supported"]
    }
    assert len(yahoo_ok | stockanalysis_ok) == 101
