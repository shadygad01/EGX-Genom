"""SourceRegistry: the versioned catalog of every data source AGX knows.

Same repository mechanics as every other store. Sources are updated by
adding new revisions (e.g. a measured data_quality_score replacing the
declared prior), never edited in place.
"""

from __future__ import annotations

from pathlib import Path

from agx_research.sources.spec import SourceCategory, SourceSpec, SourceStatus
from agx_research.storage.repository import JsonFileRepository


class SourceRegistry(JsonFileRepository[SourceSpec]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(SourceSpec, persist_path)

    def by_category(self, category: SourceCategory) -> list[SourceSpec]:
        return [s for s in self.all_latest() if s.category == category]

    def by_status(self, status: SourceStatus) -> list[SourceSpec]:
        return [s for s in self.all_latest() if s.status == status]

    def collectable(self) -> list[SourceSpec]:
        return self.by_status(SourceStatus.IMPLEMENTED)

    def record_measured_quality(self, source_id: str, score: float) -> SourceSpec:
        current = self.latest(source_id)
        if current is None:
            raise KeyError(f"No source with id {source_id}")
        return self.add(
            current.model_copy(
                update={"version": current.version + 1, "data_quality_score": score}
            )
        )
