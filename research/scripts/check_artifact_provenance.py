"""Artifact provenance gate (AD-64, docs/ARCHITECTURE_DECISIONS.md).

Fails (non-zero exit) when a PR/push changes anything under
`web/public/data/` unless the manifest committed alongside it
(`web/public/data/manifest.json`) proves the bundle came from the one
canonical GitHub Actions production workflow
(`agx_research.dashboard.manifest.CANONICAL_WORKFLOW_NAME`/
`CANONICAL_REPOSITORY`). This is the exact gap the 2026-08-03 investigation
found: `web/public/data/investment_cases.json` and its siblings had been
committed from an out-of-band, mock-mode local run with nothing to tell
it apart from a genuine production run.

Only *new* changes are gated (a diff against a base ref) -- artifacts
already in the tree before this check existed are Phase 2's job to
regenerate correctly, not something this script silently blocks every
future PR on. If no base ref can be resolved (shallow clone, first
commit, running outside git) this prints a warning and exits 0 rather
than failing CI on an infrastructure question it can't answer -- the
gate on the *content* it can check is unconditional.

Run via `uv run python scripts/check_artifact_provenance.py` from
`research/` (also invoked by `tests/test_artifact_provenance.py`, and by
CI's research job).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA_DIR = REPO_ROOT / "web" / "public" / "data"
MANIFEST_PATH = DASHBOARD_DATA_DIR / "manifest.json"

sys.path.insert(0, str(REPO_ROOT / "research" / "src"))


def _ref_exists(ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def resolve_base_ref(explicit: str | None) -> str | None:
    for candidate in (explicit, "origin/main", "main", "HEAD~1"):
        if candidate and _ref_exists(candidate):
            return candidate
    return None


def changed_dashboard_data_files(base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD", "--", "web/public/data"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def validate_manifest_is_canonical(manifest: dict) -> list[str]:
    """Pure validation over a manifest dict -- the part this module's own
    regression test exercises directly, without needing real git history.
    Returns a list of problems; empty means the manifest proves a
    canonical production run."""
    from agx_research.dashboard.manifest import (  # noqa: PLC0415
        ArtifactPublicationManifest,
        is_canonical_production,
    )

    try:
        parsed = ArtifactPublicationManifest.model_validate(manifest)
    except Exception as exc:  # noqa: BLE001 - report, don't crash the gate
        return [f"manifest.json does not match ArtifactPublicationManifest schema: {exc}"]

    if is_canonical_production(parsed):
        return []

    problems = []
    if parsed.pipeline_mode != "live":
        problems.append(f"pipeline_mode is {parsed.pipeline_mode!r}, expected 'live'")
    from agx_research.dashboard.manifest import (  # noqa: PLC0415
        CANONICAL_REPOSITORY,
        CANONICAL_WORKFLOW_NAME,
    )

    if parsed.workflow_name != CANONICAL_WORKFLOW_NAME:
        problems.append(
            f"workflow_name is {parsed.workflow_name!r}, expected {CANONICAL_WORKFLOW_NAME!r}"
        )
    if parsed.repository != CANONICAL_REPOSITORY:
        problems.append(f"repository is {parsed.repository!r}, expected {CANONICAL_REPOSITORY!r}")
    if not parsed.workflow_run_id:
        problems.append("workflow_run_id is missing -- not a real GitHub Actions run")
    if not parsed.git_commit:
        problems.append("git_commit is missing")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    explicit_base = argv[0] if argv else None

    base_ref = resolve_base_ref(explicit_base)
    if base_ref is None:
        print(
            "check_artifact_provenance: could not resolve a base ref (shallow clone or "
            "no git history available) -- skipping diff-based gate."
        )
        return 0

    changed = changed_dashboard_data_files(base_ref)
    if not changed:
        print(f"check_artifact_provenance: no web/public/data changes vs {base_ref}.")
        return 0

    print(f"check_artifact_provenance: {len(changed)} file(s) changed under web/public/data:")
    for path in changed:
        print(f"  {path}")

    if not MANIFEST_PATH.exists():
        print(
            "\n::error::web/public/data changed but manifest.json is missing. "
            "Only the canonical GitHub Actions production workflow may publish these "
            "artifacts -- see docs/ARCHITECTURE_DECISIONS.md (AD-64)."
        )
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    problems = validate_manifest_is_canonical(manifest)
    if problems:
        print("\n::error::manifest.json does not prove a canonical production run:")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "\nSee docs/ARCHITECTURE_DECISIONS.md (AD-64): only "
            "'Deploy web dashboard to GitHub Pages' running in live mode against "
            "shadygad01/EGX-Genom may publish web/public/data."
        )
        return 1

    print("check_artifact_provenance: manifest.json proves a canonical production run. OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
