"""Artifact provenance regression suite (AD-64, docs/ARCHITECTURE_DECISIONS.md).

Covers `agx_research.dashboard.manifest` (the model + builder + canonical
check), the structural mock/production path-separation guard in
`ProductionPipeline.run()`, and
`scripts/check_artifact_provenance.py`'s pure validation function -- the
exact three mechanisms that together make the 2026-08-03 incident
(mock-mode artifacts committed as if they were a genuine GitHub Actions
production run) structurally impossible to repeat silently.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

from agx_research.dashboard.manifest import (
    CANONICAL_REPOSITORY,
    CANONICAL_WORKFLOW_NAME,
    ArtifactPublicationManifest,
    build_manifest,
    is_canonical_production,
)
from agx_research.production.collector_plan import ExecutionMode
from agx_research.production.pipeline import ProductionPipeline
from agx_research.production.stages import StageName, StageStatus
from agx_research.universe.provider import MappingUniverseProvider

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_artifact_provenance import validate_manifest_is_canonical  # noqa: E402

TICKERS = ["COMI", "MFPC", "EAST", "ETEL"]
RUN_DATE = date(2026, 6, 14)


def make_pipeline(data_dir, tickers=TICKERS):
    return ProductionPipeline(
        data_dir=data_dir,
        universe_provider=MappingUniverseProvider({ticker: ticker for ticker in tickers}),
    )


def _clear_github_env(monkeypatch):
    for name in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_WORKFLOW", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(name, raising=False)


# ---- build_manifest / is_canonical_production ---------------------------


def test_build_manifest_never_fabricates_workflow_identity_outside_github_actions(monkeypatch):
    """A local run genuinely has no GitHub-issued workflow identity --
    build_manifest must record that as None, never guess a value that
    would make the bundle look more trustworthy than it is."""
    _clear_github_env(monkeypatch)
    manifest = build_manifest(mode="mock", generator_version="1.0.0", source_data_as_of=RUN_DATE)
    assert manifest.pipeline_mode == "mock"
    assert manifest.generator_version == "1.0.0"
    assert manifest.source_data_as_of == RUN_DATE
    assert manifest.workflow_run_id is None
    assert manifest.workflow_name is None
    assert manifest.repository is None
    assert manifest.schema_version == "1"


def test_build_manifest_reads_real_github_actions_environment(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")
    monkeypatch.setenv("GITHUB_RUN_ID", "123456")
    monkeypatch.setenv("GITHUB_WORKFLOW", CANONICAL_WORKFLOW_NAME)
    monkeypatch.setenv("GITHUB_REPOSITORY", CANONICAL_REPOSITORY)
    manifest = build_manifest(mode="live", generator_version="1.0.0", source_data_as_of=RUN_DATE)
    assert manifest.git_commit == "deadbeef"
    assert manifest.workflow_run_id == "123456"
    assert manifest.workflow_name == CANONICAL_WORKFLOW_NAME
    assert manifest.repository == CANONICAL_REPOSITORY
    assert is_canonical_production(manifest)


@pytest.mark.parametrize(
    "overrides",
    [
        {"pipeline_mode": "mock"},
        {"pipeline_mode": "replay"},
        {"workflow_run_id": None},
        {"git_commit": None},
        {"workflow_name": "some other workflow"},
        {"repository": "someone-else/EGX-Genom"},
    ],
)
def test_is_canonical_production_rejects_any_missing_or_mismatched_field(overrides):
    base = dict(
        generated_at="2026-08-03T12:00:00",
        pipeline_mode="live",
        git_commit="deadbeef",
        workflow_run_id="123456",
        workflow_name=CANONICAL_WORKFLOW_NAME,
        repository=CANONICAL_REPOSITORY,
        generator_version="1.0.0",
        source_data_as_of=None,
    )
    base.update(overrides)
    manifest = ArtifactPublicationManifest.model_validate(base)
    assert not is_canonical_production(manifest)


def test_is_canonical_production_accepts_the_fully_canonical_manifest():
    manifest = ArtifactPublicationManifest.model_validate(
        {
            "generated_at": "2026-08-03T12:00:00",
            "pipeline_mode": "live",
            "git_commit": "deadbeef",
            "workflow_run_id": "123456",
            "workflow_name": CANONICAL_WORKFLOW_NAME,
            "repository": CANONICAL_REPOSITORY,
            "generator_version": "1.0.0",
            "source_data_as_of": "2026-06-14",
        }
    )
    assert is_canonical_production(manifest)


def test_is_canonical_production_none_manifest_is_never_canonical():
    assert not is_canonical_production(None)


# ---- structural mock/production path separation --------------------------


def test_mock_mode_refuses_to_publish_to_the_canonical_production_path(tmp_path, monkeypatch):
    """The exact guard that makes the 2026-08-03 incident structurally
    impossible to repeat: a mock run must never be able to land artifacts
    in the one directory GitHub Pages actually serves. Monkeypatches the
    canonical path to a tmp directory -- never touches the real
    web/public/data during a test run."""
    fake_canonical = tmp_path / "canonical" / "web" / "public" / "data"
    monkeypatch.setattr(
        "agx_research.production.pipeline.CANONICAL_PRODUCTION_DASHBOARD_DIR", fake_canonical
    )

    pipeline = make_pipeline(tmp_path / "data")
    with pytest.raises(ValueError, match="canonical production publication path"):
        pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK, dashboard_out=fake_canonical)
    # The guard fires before run() does any work at all -- no partial/mock
    # data ever lands in what would be the production path.
    assert not fake_canonical.exists() or not any(fake_canonical.iterdir())


def test_mock_mode_publishes_normally_to_a_non_canonical_path(tmp_path, monkeypatch):
    fake_canonical = tmp_path / "canonical" / "web" / "public" / "data"
    monkeypatch.setattr(
        "agx_research.production.pipeline.CANONICAL_PRODUCTION_DASHBOARD_DIR", fake_canonical
    )
    dashboard_out = tmp_path / "dashboard"

    pipeline = make_pipeline(tmp_path / "data")
    report = pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK, dashboard_out=dashboard_out)

    stage = report.stage(StageName.DASHBOARD_ARTIFACT_GENERATOR)
    assert stage is not None
    assert stage.status == StageStatus.SUCCEEDED
    assert (dashboard_out / "manifest.json").exists()


def test_replay_mode_is_also_blocked_from_the_canonical_path(tmp_path, monkeypatch):
    """REPLAY is not LIVE either -- the guard must not special-case MOCK
    while leaving REPLAY (deterministic reprocessing of previously
    archived raw documents, still not a genuine new production run) free
    to overwrite the canonical path."""
    fake_canonical = tmp_path / "canonical" / "web" / "public" / "data"
    monkeypatch.setattr(
        "agx_research.production.pipeline.CANONICAL_PRODUCTION_DASHBOARD_DIR", fake_canonical
    )

    data_dir = tmp_path / "data"
    make_pipeline(data_dir).run(RUN_DATE, mode=ExecutionMode.MOCK)  # seed a raw archive to replay

    replay_pipeline = make_pipeline(data_dir)
    with pytest.raises(ValueError, match="canonical production publication path"):
        replay_pipeline.run(RUN_DATE, mode=ExecutionMode.REPLAY, dashboard_out=fake_canonical)


def test_published_manifest_records_the_mode_it_actually_ran_in(tmp_path):
    dashboard_out = tmp_path / "dashboard"
    pipeline = make_pipeline(tmp_path / "data")
    pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK, dashboard_out=dashboard_out)

    import json

    manifest = json.loads((dashboard_out / "manifest.json").read_text())
    assert manifest["pipeline_mode"] == "mock"
    assert manifest["source_data_as_of"] == RUN_DATE.isoformat()
    assert not is_canonical_production(ArtifactPublicationManifest.model_validate(manifest))


# ---- CI gate's pure validation function -----------------------------------


def test_ci_gate_rejects_mock_mode_manifest():
    problems = validate_manifest_is_canonical(
        {
            "generated_at": "2026-08-03T12:00:00",
            "pipeline_mode": "mock",
            "git_commit": "deadbeef",
            "workflow_run_id": None,
            "workflow_name": None,
            "repository": None,
            "generator_version": "1.0.0",
        }
    )
    assert problems, "a mock-mode manifest must never pass the CI provenance gate"


def test_ci_gate_accepts_fully_canonical_manifest():
    problems = validate_manifest_is_canonical(
        {
            "generated_at": "2026-08-03T12:00:00",
            "pipeline_mode": "live",
            "git_commit": "deadbeef",
            "workflow_run_id": "123456",
            "workflow_name": CANONICAL_WORKFLOW_NAME,
            "repository": CANONICAL_REPOSITORY,
            "generator_version": "1.0.0",
        }
    )
    assert problems == []


def test_ci_gate_rejects_malformed_manifest():
    problems = validate_manifest_is_canonical({"not": "a manifest"})
    assert problems
