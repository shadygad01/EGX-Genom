"""Atomic publication regression suite (AD-65, docs/ARCHITECTURE_DECISIONS.md).

Covers `dashboard.consistency.validate_bundle_consistency`,
`dashboard.publish.publish_canonical_dataset`, and the full
`ProductionPipeline.run()` staging/publish wiring -- proving that a
non-canonical bundle (wrong mode, no real workflow identity, internally
inconsistent, or simply invalid) can never overwrite whatever is already
at the canonical location, and that a genuinely canonical, internally
consistent bundle publishes atomically.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import pytest

from agx_research.collectors.fetcher import HttpFetcher
from agx_research.dashboard.consistency import validate_bundle_consistency
from agx_research.dashboard.manifest import CANONICAL_REPOSITORY, CANONICAL_WORKFLOW_NAME
from agx_research.dashboard.publish import PublicationError, publish_canonical_dataset
from agx_research.production.collector_plan import ExecutionMode
from agx_research.production.pipeline import ProductionPipeline
from agx_research.universe.provider import MappingUniverseProvider

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_production_pipeline import (  # noqa: E402
    TICKERS,
    _canned_live_urlopen,
    _live_content_fixture,
)

RUN_DATE = date(2026, 6, 14)


def make_pipeline(data_dir, tickers=TICKERS):
    return ProductionPipeline(
        data_dir=data_dir,
        universe_provider=MappingUniverseProvider({ticker: ticker for ticker in tickers}),
    )


def _mock_bundle(tmp_path) -> Path:
    """A real, valid, internally-consistent bundle -- just not a canonical
    one (mock mode, no workflow identity). Used as the fixture every test
    below mutates from, rather than hand-rolling brittle JSON."""
    bundle_dir = tmp_path / "mock_bundle"
    make_pipeline(tmp_path / "data").run(RUN_DATE, mode=ExecutionMode.MOCK, dashboard_out=bundle_dir)
    return bundle_dir


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


# ---- validate_bundle_consistency ------------------------------------------


def test_consistent_bundle_has_no_problems(tmp_path):
    bundle = _mock_bundle(tmp_path)
    assert validate_bundle_consistency(bundle) == []


def test_missing_manifest_is_a_problem(tmp_path):
    bundle = _mock_bundle(tmp_path)
    (bundle / "manifest.json").unlink()
    problems = validate_bundle_consistency(bundle)
    assert any("manifest.json is missing" in p for p in problems)


def test_mismatched_pipeline_mode_is_a_problem(tmp_path):
    bundle = _mock_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["pipeline_mode"] = "live"
    _write_json(manifest_path, manifest)

    problems = validate_bundle_consistency(bundle)
    assert any("execution_mode" in p and "pipeline_mode" in p for p in problems)


def test_mismatched_as_of_is_a_problem(tmp_path):
    bundle = _mock_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["source_data_as_of"] = "2026-01-01"
    _write_json(manifest_path, manifest)

    problems = validate_bundle_consistency(bundle)
    assert any("investment_cases.json" in p for p in problems)
    assert any("portfolio_summary.json" in p for p in problems)


def test_stale_generation_timestamp_is_a_problem(tmp_path):
    bundle = _mock_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["generated_at"] = "2020-01-01T00:00:00"
    _write_json(manifest_path, manifest)

    problems = validate_bundle_consistency(bundle)
    assert any("differ by" in p for p in problems)


# ---- publish_canonical_dataset --------------------------------------------


def test_mock_bundle_is_rejected_and_nothing_is_published(tmp_path):
    bundle = _mock_bundle(tmp_path)
    canonical_dir = tmp_path / "canonical" / "data"

    with pytest.raises(PublicationError, match="does not prove a canonical production run"):
        publish_canonical_dataset(bundle, canonical_dir=canonical_dir)
    assert not canonical_dir.exists()


def test_internally_inconsistent_bundle_is_rejected_even_with_a_canonical_looking_manifest(
    tmp_path,
):
    """Editing manifest.json alone to *claim* canonical status must not be
    enough -- cross-artifact consistency catches the resulting mismatch
    against execution_report.json's real execution_mode."""
    bundle = _mock_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest.update(
        pipeline_mode="live",
        workflow_name=CANONICAL_WORKFLOW_NAME,
        repository=CANONICAL_REPOSITORY,
        workflow_run_id="123456",
        git_commit="deadbeef",
    )
    _write_json(manifest_path, manifest)
    canonical_dir = tmp_path / "canonical" / "data"

    with pytest.raises(PublicationError, match="cross-artifact consistency"):
        publish_canonical_dataset(bundle, canonical_dir=canonical_dir)
    assert not canonical_dir.exists()


def test_schema_invalid_bundle_is_rejected(tmp_path):
    bundle = _mock_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest.update(
        pipeline_mode="live",
        workflow_name=CANONICAL_WORKFLOW_NAME,
        repository=CANONICAL_REPOSITORY,
        workflow_run_id="123456",
        git_commit="deadbeef",
    )
    _write_json(manifest_path, manifest)
    # Also make execution_report.json agree, so this fails specifically at
    # schema validation, not consistency.
    er_path = bundle / "execution_report.json"
    er = _read_json(er_path)
    er["execution_mode"] = "live"
    _write_json(er_path, er)
    (bundle / "knowledge.json").write_text("{not valid json")

    canonical_dir = tmp_path / "canonical" / "data"
    with pytest.raises(PublicationError, match="failed artifact validation"):
        publish_canonical_dataset(bundle, canonical_dir=canonical_dir)
    assert not canonical_dir.exists()


def _fully_canonical_bundle(tmp_path) -> Path:
    """A bundle whose manifest and execution_report.json mutually agree
    on a genuine 'live, canonical workflow' identity -- what a real
    GitHub Actions production run's staged output looks like."""
    bundle = _mock_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest.update(
        pipeline_mode="live",
        workflow_name=CANONICAL_WORKFLOW_NAME,
        repository=CANONICAL_REPOSITORY,
        workflow_run_id="123456",
        git_commit="deadbeef",
    )
    _write_json(manifest_path, manifest)
    er_path = bundle / "execution_report.json"
    er = _read_json(er_path)
    er["execution_mode"] = "live"
    er["git_commit"] = "deadbeef"
    er["workflow_run_id"] = "123456"
    _write_json(er_path, er)
    return bundle


def test_fully_canonical_and_consistent_bundle_publishes_atomically(tmp_path):
    bundle = _fully_canonical_bundle(tmp_path)
    canonical_dir = tmp_path / "canonical" / "data"

    publish_canonical_dataset(bundle, canonical_dir=canonical_dir)

    assert canonical_dir.exists()
    published_manifest = _read_json(canonical_dir / "manifest.json")
    assert published_manifest["pipeline_mode"] == "live"
    assert published_manifest["workflow_run_id"] == "123456"
    assert (canonical_dir / "execution_report.json").exists()
    assert (canonical_dir / "investment_cases.json").exists()


def test_a_rejected_publish_never_touches_pre_existing_canonical_content(tmp_path):
    """The exact regression requirement: non-canonical (or inconsistent)
    artifacts can never overwrite what's already published, even
    partially -- prior content must survive byte-for-byte."""
    canonical_dir = tmp_path / "canonical" / "data"
    good_bundle = _fully_canonical_bundle(tmp_path)
    publish_canonical_dataset(good_bundle, canonical_dir=canonical_dir)
    prior_manifest_bytes = (canonical_dir / "manifest.json").read_bytes()
    prior_files = sorted(p.name for p in canonical_dir.iterdir())

    bad_bundle = _mock_bundle(tmp_path)
    with pytest.raises(PublicationError):
        publish_canonical_dataset(bad_bundle, canonical_dir=canonical_dir)

    assert (canonical_dir / "manifest.json").read_bytes() == prior_manifest_bytes
    assert sorted(p.name for p in canonical_dir.iterdir()) == prior_files


# ---- full ProductionPipeline.run() wiring (AD-65) -------------------------


def test_end_to_end_live_run_with_canonical_workflow_identity_publishes(tmp_path, monkeypatch):
    """Reproduces what a real GitHub Actions execution of the canonical
    workflow looks like: LIVE mode, real collector code paths against
    canned (never real-network) content, and real GITHUB_* environment
    variables -- the only combination `publish_canonical_dataset()` (called
    internally by run()) accepts."""
    monkeypatch.setattr(HttpFetcher, "_robots_allows", lambda self, url: True)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.setattr(urllib.request, "urlopen", _canned_live_urlopen(_live_content_fixture()))
    monkeypatch.setenv("GITHUB_SHA", "deadbeefcafe")
    monkeypatch.setenv("GITHUB_RUN_ID", "987654321")
    monkeypatch.setenv("GITHUB_WORKFLOW", CANONICAL_WORKFLOW_NAME)
    monkeypatch.setenv("GITHUB_REPOSITORY", CANONICAL_REPOSITORY)

    canonical_dir = tmp_path / "canonical" / "data"
    monkeypatch.setattr("agx_research.production.pipeline.CANONICAL_PRODUCTION_DASHBOARD_DIR", canonical_dir)

    pipeline = make_pipeline(tmp_path / "data")
    report = pipeline.run(RUN_DATE, mode=ExecutionMode.LIVE, dashboard_out=canonical_dir)

    assert report.git_commit == "deadbeefcafe"
    assert report.workflow_run_id == "987654321"
    assert canonical_dir.exists()
    manifest = _read_json(canonical_dir / "manifest.json")
    assert manifest["pipeline_mode"] == "live"
    assert manifest["workflow_run_id"] == "987654321"
    assert manifest["git_commit"] == "deadbeefcafe"
    assert validate_bundle_consistency(canonical_dir) == []


def test_end_to_end_live_run_outside_ci_never_publishes(tmp_path, monkeypatch):
    """Same LIVE-mode run, same canned network -- but no GITHUB_* env vars,
    i.e. a developer's own machine. Mode alone is not enough; run() must
    still refuse to publish, and must raise rather than silently succeed
    with an unverifiable bundle."""
    monkeypatch.setattr(HttpFetcher, "_robots_allows", lambda self, url: True)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.setattr(urllib.request, "urlopen", _canned_live_urlopen(_live_content_fixture()))
    for name in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_WORKFLOW", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(name, raising=False)

    canonical_dir = tmp_path / "canonical" / "data"
    monkeypatch.setattr("agx_research.production.pipeline.CANONICAL_PRODUCTION_DASHBOARD_DIR", canonical_dir)

    pipeline = make_pipeline(tmp_path / "data")
    with pytest.raises(PublicationError):
        pipeline.run(RUN_DATE, mode=ExecutionMode.LIVE, dashboard_out=canonical_dir)

    assert not canonical_dir.exists()
