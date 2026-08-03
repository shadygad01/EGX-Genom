"""Artifact publication provenance (AD-64, see docs/ARCHITECTURE_DECISIONS.md).

Every dashboard artifact bundle ships one `manifest.json` alongside it,
recording *where the data actually came from* -- not just what it says.
This exists because a real incident (investigated 2026-08-03) showed the
gap: `web/public/data/investment_cases.json` and its siblings were
committed to `main` from an out-of-band, mock-mode local run (a different
machine, a throwaway worktree), and nothing in the pipeline or the web
app could tell the difference between that and a genuine `--mode live`
GitHub Actions production run. The dashboard rendered an honest "no
recommendations" empty state -- correct given the data it had -- but the
data itself had no way to prove it was the data it claimed to be.

Same "unknown over wrong" discipline as `docs/TRUTH_PRESERVATION_POLICY.md`
(AD-60): a field this module cannot verify is recorded as `None`, never
guessed. `git_commit`/`workflow_run_id`/`workflow_name`/`repository` are
only ever read from the environment a real `git`/GitHub Actions execution
actually sets -- never synthesized so a manifest "looks complete."
"""

from __future__ import annotations

import os
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

# Bump whenever a field is added, renamed, or reinterpreted -- consumers
# (the web app's provenance check, the CI gate) key off this to know
# whether they understand the shape they're looking at.
ARTIFACT_SCHEMA_VERSION = "1"

# The one workflow/repository allowed to produce a manifest the web app
# will treat as "production-generated". Any other value (a fork, a local
# run, a renamed workflow) is honestly reported as unverified -- never
# silently accepted just because *a* manifest is present.
CANONICAL_WORKFLOW_NAME = "Deploy web dashboard to GitHub Pages"
CANONICAL_REPOSITORY = "shadygad01/EGX-Genom"

PipelineMode = Literal["live", "mock", "replay"]


class ArtifactPublicationManifest(BaseModel):
    """Provenance for one published dashboard artifact bundle. Written
    once per `write_dashboard_artifacts`/production pipeline export,
    alongside the artifact files themselves -- not per individual file,
    since every file in a bundle shares one generation event."""

    generated_at: datetime
    pipeline_mode: PipelineMode
    git_commit: str | None = None
    workflow_run_id: str | None = None
    workflow_name: str | None = None
    repository: str | None = None
    generator_version: str
    source_data_as_of: date | None = None
    schema_version: str = ARTIFACT_SCHEMA_VERSION


def _git_commit_sha(repo_root: Path) -> str | None:
    """The commit actually checked out when the artifacts were generated.
    `GITHUB_SHA` is authoritative inside GitHub Actions; a plain `git
    rev-parse HEAD` is the honest best-effort outside of it (a local run
    genuinely doesn't have a GitHub-issued commit identity, and this
    module never invents one)."""
    github_sha = os.environ.get("GITHUB_SHA")
    if github_sha:
        return github_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def build_manifest(
    *,
    mode: PipelineMode,
    generator_version: str,
    source_data_as_of: date | None,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> ArtifactPublicationManifest:
    """Builds the manifest for one artifact bundle. `mode` is a plain
    string (`"live"`/`"mock"`/`"replay"`) rather than
    `production.collector_plan.ExecutionMode` on purpose -- this module is
    a leaf dashboard concern `production/` depends on (to write its own
    manifest), so depending back on `production` here would be circular.
    Callers holding an `ExecutionMode` pass `mode.value`.

    `workflow_run_id`, `workflow_name`, and `repository` are only ever
    populated from the GitHub Actions environment (`GITHUB_RUN_ID`/
    `GITHUB_WORKFLOW`/`GITHUB_REPOSITORY`) that a real Actions execution
    sets -- a local run (mock or live) leaves them `None` rather than
    fabricating a workflow identity it doesn't have."""
    repo_root = repo_root or Path(__file__).resolve().parents[4]
    return ArtifactPublicationManifest(
        generated_at=now or datetime.now(),
        pipeline_mode=mode,
        git_commit=_git_commit_sha(repo_root),
        workflow_run_id=os.environ.get("GITHUB_RUN_ID"),
        workflow_name=os.environ.get("GITHUB_WORKFLOW"),
        repository=os.environ.get("GITHUB_REPOSITORY"),
        generator_version=generator_version,
        source_data_as_of=source_data_as_of,
        schema_version=ARTIFACT_SCHEMA_VERSION,
    )


def is_canonical_production(manifest: ArtifactPublicationManifest | None) -> bool:
    """True only if every field required to trust this bundle as the
    canonical GitHub Actions production run is present and matches --
    partial evidence (a manifest that merely claims `pipeline_mode="live"`
    with no workflow/run identity behind it) is not enough."""
    if manifest is None:
        return False
    return (
        manifest.pipeline_mode == "live"
        and manifest.workflow_name == CANONICAL_WORKFLOW_NAME
        and manifest.repository == CANONICAL_REPOSITORY
        and bool(manifest.workflow_run_id)
        and bool(manifest.git_commit)
    )
