"""Generic, versioned, append-only storage for any entity with `id` and `version`.

Every domain store (knowledge, hypotheses, and future stores for
predictions, feature values, dataset snapshots, ...) is a thin, meaningfully
named wrapper around one of these rather than hand-rolling its own JSON
read/write loop. A write never overwrites a previous revision — it appends
— so `history()` always reconstructs every past state of an entity. This is
what lets Principle 5 ("everything is versioned") hold for every entity
type without each one reinventing how versioning works.

Swapping the backing store (e.g. to a real database once there's enough
scale to need one) means writing a new `Repository[T]` implementation, not
touching any of the call sites that already depend on this interface.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, Protocol, TypeVar, runtime_checkable


@runtime_checkable
class Identified(Protocol):
    id: str
    version: int


T = TypeVar("T", bound=Identified)


class Repository(ABC, Generic[T]):
    @abstractmethod
    def add(self, entity: T) -> T:
        """Persist `entity` as a new revision. Callers are responsible for setting
        `entity.version` appropriately before calling this (typically `previous.version + 1`).
        """

    @abstractmethod
    def latest(self, entity_id: str) -> T | None:
        """Return the most recent revision of `entity_id`, or None if it doesn't exist."""

    @abstractmethod
    def history(self, entity_id: str) -> list[T]:
        """Return every revision of `entity_id` in the order they were added."""

    @abstractmethod
    def all_latest(self) -> list[T]:
        """Return the most recent revision of every entity in the repository."""


class JsonFileRepository(Repository[T]):
    """In-memory storage with optional JSON-file persistence.

    A foundation-scaffold implementation — swap for a real database once
    the repository needs concurrent writers or query performance beyond
    what fits in memory. `model_cls` is required (rather than inferred)
    because Python generics erase at runtime; it's what lets this class
    deserialize persisted JSON back into the right pydantic model.
    """

    def __init__(self, model_cls: type[T], persist_path: Path | str | None = None):
        self._model_cls = model_cls
        self._revisions: dict[str, list[T]] = {}
        self.persist_path = Path(persist_path) if persist_path else None
        if self.persist_path and self.persist_path.exists():
            self._load()

    def add(self, entity: T) -> T:
        self._revisions.setdefault(entity.id, []).append(entity)
        self._save()
        return entity

    def latest(self, entity_id: str) -> T | None:
        revisions = self._revisions.get(entity_id)
        return revisions[-1] if revisions else None

    def history(self, entity_id: str) -> list[T]:
        return list(self._revisions.get(entity_id, []))

    def all_latest(self) -> list[T]:
        return [revisions[-1] for revisions in self._revisions.values() if revisions]

    def _save(self) -> None:
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            entity_id: [json.loads(rev.model_dump_json()) for rev in revisions]
            for entity_id, revisions in self._revisions.items()
        }
        self.persist_path.write_text(json.dumps(payload, indent=2))

    def _load(self) -> None:
        payload = json.loads(self.persist_path.read_text())
        self._revisions = {
            entity_id: [self._model_cls.model_validate(rev) for rev in revisions]
            for entity_id, revisions in payload.items()
        }
