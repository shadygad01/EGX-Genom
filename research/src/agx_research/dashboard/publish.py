"""The one path into the canonical production publication location
(AD-65, see docs/ARCHITECTURE_DECISIONS.md).

`CANONICAL_PRODUCTION_DASHBOARD_DIR` is defined exactly once, here --
every other module that needs it (`production.pipeline`) imports it from
this one place rather than redefining it, so "exactly one canonical
publication path" is enforced by there being exactly one name for it, not
by convention repeated in multiple files.

`publish_canonical_dataset()` is the only function permitted to write
into that directory. It never trusts its caller's claim that a bundle is
ready -- it re-validates from scratch, in order: artifact shape/schema
(`dashboard.validate.validate_dashboard_artifacts`), provenance
(`dashboard.manifest.is_canonical_production` -- only a real GitHub
Actions run of the canonical workflow passes this), and cross-artifact
consistency (`dashboard.consistency.validate_bundle_consistency`). Any
failure raises `PublicationError` and leaves the canonical directory
completely untouched -- no partial publish, ever. On success, the
canonical directory is replaced with the staged bundle via directory
renames on the same filesystem, each individually atomic, so a concurrent
reader never observes a half-old/half-new mix.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from agx_research.dashboard.consistency import validate_bundle_consistency
from agx_research.dashboard.manifest import ArtifactPublicationManifest, is_canonical_production
from agx_research.dashboard.validate import DashboardArtifactError, validate_dashboard_artifacts

CANONICAL_PRODUCTION_DASHBOARD_DIR = Path(__file__).resolve().parents[4] / "web" / "public" / "data"


class PublicationError(Exception):
    """Raised when a staged bundle fails validation. Nothing is ever
    published when this is raised -- the canonical directory keeps
    whatever its prior state was."""


def publish_canonical_dataset(
    staged_dir: Path,
    *,
    canonical_dir: Path = CANONICAL_PRODUCTION_DASHBOARD_DIR,
) -> None:
    manifest_path = staged_dir / "manifest.json"
    if not manifest_path.exists():
        raise PublicationError(f"{staged_dir} has no manifest.json -- refusing to publish.")
    manifest = ArtifactPublicationManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if not is_canonical_production(manifest):
        raise PublicationError(
            f"{staged_dir}'s manifest does not prove a canonical production run "
            f"(pipeline_mode={manifest.pipeline_mode!r}, workflow_name={manifest.workflow_name!r}, "
            f"repository={manifest.repository!r}, workflow_run_id={manifest.workflow_run_id!r}, "
            f"git_commit={manifest.git_commit!r}) -- refusing to publish. See AD-64/AD-65 in "
            "docs/ARCHITECTURE_DECISIONS.md."
        )

    try:
        validate_dashboard_artifacts(staged_dir)
    except DashboardArtifactError as exc:
        raise PublicationError(f"{staged_dir} failed artifact validation: {exc}") from exc

    problems = validate_bundle_consistency(staged_dir)
    if problems:
        raise PublicationError(
            f"{staged_dir} failed cross-artifact consistency validation:\n"
            + "\n".join(f"  - {p}" for p in problems)
        )

    _atomic_replace(staged_dir, canonical_dir.resolve())


def _atomic_replace(staged_dir: Path, canonical_dir: Path) -> None:
    canonical_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=canonical_dir.parent, prefix=".dashboard_publish_") as tmp:
        new_dir = Path(tmp) / "new"
        shutil.copytree(staged_dir, new_dir)
        if canonical_dir.exists():
            old_dir = Path(tmp) / "old"
            canonical_dir.rename(old_dir)
        new_dir.rename(canonical_dir)
