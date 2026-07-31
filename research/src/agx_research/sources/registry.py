"""SourceRegistry: the versioned catalog of every data source AGX knows.

Same repository mechanics as every other store. Sources are updated by
adding new revisions (e.g. a measured data_quality_score replacing the
declared prior), never edited in place.
"""

from __future__ import annotations

from pathlib import Path

from agx_research.sources.spec import (
    ActivationStatus,
    HealthStatus,
    LifecycleState,
    SourceCategory,
    SourceSpec,
    SourceStatus,
    default_lifecycle_for_status,
)
from agx_research.storage.repository import JsonFileRepository


class SourceRegistry(JsonFileRepository[SourceSpec]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(SourceSpec, persist_path)

    def by_category(self, category: SourceCategory) -> list[SourceSpec]:
        return [s for s in self.all_latest() if s.category == category]

    def by_status(self, status: SourceStatus) -> list[SourceSpec]:
        return [s for s in self.all_latest() if s.status == status]

    def by_lifecycle_state(self, state: LifecycleState) -> list[SourceSpec]:
        return [s for s in self.all_latest() if s.lifecycle_state == state]

    def by_health_status(self, health: HealthStatus) -> list[SourceSpec]:
        return [s for s in self.all_latest() if s.health_status == health]

    def collectable(self) -> list[SourceSpec]:
        return [
            s
            for s in self.all_latest()
            if s.status == SourceStatus.IMPLEMENTED and s.activation_status == ActivationStatus.ACTIVE
        ]

    def record_measured_quality(self, source_id: str, score: float) -> SourceSpec:
        current = self.latest(source_id)
        if current is None:
            raise KeyError(f"No source with id {source_id}")
        return self.add(
            current.model_copy(
                update={"version": current.version + 1, "data_quality_score": score}
            )
        )

    def transition_lifecycle(self, source_id: str, new_state: LifecycleState) -> SourceSpec:
        """Move a source to a new lifecycle stage. Callers (the qualification
        pipeline) are responsible for only calling this with an evidence-backed
        next stage — the registry itself doesn't gate forward-only or
        evidence rules; `qualification.evaluate_promotion` does.
        """
        current = self.latest(source_id)
        if current is None:
            raise KeyError(f"No source with id {source_id}")
        return self.add(
            current.model_copy(
                update={"version": current.version + 1, "lifecycle_state": new_state}
            )
        )

    def update_health(self, source_id: str, health: HealthStatus) -> SourceSpec:
        current = self.latest(source_id)
        if current is None:
            raise KeyError(f"No source with id {source_id}")
        return self.add(
            current.model_copy(update={"version": current.version + 1, "health_status": health})
        )

    # A maintainer edits these directly in `sources.catalog`; everything
    # else on `SourceSpec` (health_status, data_quality_score,
    # reputation_score, and lifecycle_state/activation_status *except when
    # status itself changes* -- see below) is runtime-measured and must
    # never be clobbered by a catalog re-seed.
    _DECLARED_FIELDS = (
        "status", "access_method", "base_url", "collector",
        "collector_version", "category", "notes",
    )

    def sync_declared_fields(self, current_specs: list[SourceSpec]) -> list[SourceSpec]:
        """Push a new revision for any already-persisted source whose
        catalog-declared fields (see `_DECLARED_FIELDS`) differ from what's
        in `current_specs` -- e.g. a maintainer promoting a source from
        PLANNED to IMPLEMENTED after verifying a real endpoint.

        `seed_registry()`'s add-loop only adds a brand-new id; it never
        revisits one that already exists, so a real production incident
        (2026-07-31) showed a source promoted in `sources.catalog` stayed
        PLANNED forever in an already-running deployment that had already
        persisted its old PLANNED spec -- the exact same class of gap
        `retire_removed()` already closed for outright deletions, this
        time for updates. Runtime-measured fields
        (health_status/data_quality_score/reputation_score) are always
        carried forward unchanged. `lifecycle_state`/`activation_status`
        are only re-derived from the new `status` when `status` itself
        actually changed -- a source's own qualification-pipeline-earned
        lifecycle stage must never be reset by an unrelated catalog edit.
        """
        synced = []
        by_id = {spec.id: spec for spec in current_specs}
        for current in self.all_latest():
            spec = by_id.get(current.id)
            if spec is None:
                continue
            if all(
                getattr(current, field) == getattr(spec, field)
                for field in self._DECLARED_FIELDS
            ):
                continue
            updates = {field: getattr(spec, field) for field in self._DECLARED_FIELDS}
            updates["version"] = current.version + 1
            if current.status != spec.status:
                updates["lifecycle_state"] = spec.lifecycle_state
                updates["activation_status"] = spec.activation_status
            synced.append(self.add(current.model_copy(update=updates)))
        return synced

    def retire_removed(self, current_catalog_ids: set[str]) -> list[SourceSpec]:
        """Transition to DISABLED (which `default_lifecycle_for_status`
        already maps to `ActivationStatus.RETIRED`) any already-persisted
        source whose id no longer appears in `current_catalog_ids`.

        `seed_registry()` only ever *adds* an id it doesn't already know
        about -- deleting a `SourceSpec` from `sources.catalog` (e.g. the
        Decision-Centric Redesign's removal of 11 sources with zero
        capability mapping) never reaches an already-running deployment's
        persisted registry, since nothing ever re-derives membership from
        the current catalog. That source keeps looking "live" in that
        deployment forever, even though the code that was supposed to
        remove it already shipped. This closes that gap going forward: a
        new revision (never an edit or deletion, so its full prior history
        stays intact), not a change to how a currently-catalogued source
        is treated.
        """
        retired = []
        for existing in self.all_latest():
            if existing.id in current_catalog_ids or existing.status == SourceStatus.DISABLED:
                continue
            lifecycle_state, activation_status = default_lifecycle_for_status(
                SourceStatus.DISABLED
            )
            reason = (
                "Retired: no longer in the source catalog (removed as a source with "
                "zero capability mapping and no consumer)."
            )
            retired.append(
                self.add(
                    existing.model_copy(
                        update={
                            "version": existing.version + 1,
                            "status": SourceStatus.DISABLED,
                            "lifecycle_state": lifecycle_state,
                            "activation_status": activation_status,
                            "notes": (
                                f"{existing.notes} {reason}".strip()
                                if existing.notes
                                else reason
                            ),
                        }
                    )
                )
            )
        return retired
