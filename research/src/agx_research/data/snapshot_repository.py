"""Versioned persistence for DatasetSnapshots.

Closes a gap named in `docs/EPOCH_II_REPORT.md`: snapshots were content-hashed
and immutable from the start, but never had a repository, so there was no
way to persist "which snapshot did session X actually run against" beyond
whatever `ArtifactRepository` entries happened to reference it.
"""

from __future__ import annotations

from pathlib import Path

from agx_research.data.snapshot import DatasetSnapshot
from agx_research.storage.repository import JsonFileRepository


class DatasetSnapshotRepository(JsonFileRepository[DatasetSnapshot]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(DatasetSnapshot, persist_path)
