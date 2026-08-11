"""Reproducibility metadata (mission Phase 19).

Every `discover()`/`validate()`/`final_holdout()` call stamps a
`ReproducibilityManifest` recording exactly what produced it: a fresh
experiment id, the git commit actually checked out (reusing
`dashboard.manifest`'s own honest, `GITHUB_SHA`-aware resolution rather
than a second implementation -- a local run genuinely has no
GitHub-issued commit identity beyond `git rev-parse HEAD`, and this
module never invents one), the engine/feature-factory/target-factory
versions, the dataset source/version the panel was built from, the full
engine config, and a timestamp. Every `Pattern` this module's manifests
accompany carries the `experiment_id` that discovered/validated/holdout-
checked it (`registry.Pattern.experiment_id`), so any pattern's own run
can be traced back and, in principle, reproduced.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from agx_research.dashboard.manifest import _git_commit_sha
from agx_research.domain.identifiers import new_id

# Bump whenever FeatureFactory's transform set changes in a way that would
# change an already-computed feature's values for the same input data --
# same "explicit version, not implicit trust" posture as
# `dashboard.manifest.ARTIFACT_SCHEMA_VERSION`.
FEATURE_FACTORY_VERSION = "1.0.0"
TARGET_FACTORY_VERSION = "1.0.0"

_REPO_ROOT = Path(__file__).resolve().parents[4]


class ReproducibilityManifest(BaseModel):
    experiment_id: str
    generated_at: datetime
    git_commit: str | None
    engine_name: str
    engine_version: str
    feature_factory_version: str
    target_factory_version: str
    dataset_source: str
    dataset_version: str | None
    config: dict


def build_reproducibility_manifest(
    *,
    engine_name: str,
    engine_version: str,
    dataset_source: str = "unknown",
    dataset_version: str | None = None,
    config: dict,
    repo_root: Path | None = None,
) -> ReproducibilityManifest:
    return ReproducibilityManifest(
        experiment_id=new_id("experiment"),
        generated_at=datetime.now(),
        git_commit=_git_commit_sha(repo_root or _REPO_ROOT),
        engine_name=engine_name,
        engine_version=engine_version,
        feature_factory_version=FEATURE_FACTORY_VERSION,
        target_factory_version=TARGET_FACTORY_VERSION,
        dataset_source=dataset_source,
        dataset_version=dataset_version,
        config=config,
    )


__all__ = [
    "FEATURE_FACTORY_VERSION",
    "TARGET_FACTORY_VERSION",
    "ReproducibilityManifest",
    "build_reproducibility_manifest",
]
