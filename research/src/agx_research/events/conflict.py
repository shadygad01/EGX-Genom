"""Conflict resolution: what happens when a new candidate event collides
(by fingerprint) with an existing one.

`ConservativeConflictPolicy` is the one real, concrete policy: metadata
keys present in both events with equal values are corroboration (raises
confidence); keys present in both with *different* values are a material
conflict, recorded and surfaced rather than silently overwritten. This is
"never fabricate confidence" applied directly to disagreeing sources — a
disagreement must be visible, not resolved by guessing which source is
right.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from agx_research.events.event import Event


class ConflictResolution(BaseModel):
    merged_metadata: dict[str, Any]
    merged_confidence: float = Field(ge=0.0, le=1.0)
    is_disputed: bool
    disputed_keys: list[str] = Field(default_factory=list)
    notes: str = ""


class ConflictResolutionPolicy(ABC):
    @abstractmethod
    def resolve(self, existing: Event, candidate: Event) -> ConflictResolution:
        """Compare `candidate` against the already-persisted `existing` event
        sharing its fingerprint, and decide how to merge them.
        """


class ConservativeConflictPolicy(ConflictResolutionPolicy):
    def __init__(self, *, corroboration_boost: float = 0.5, dispute_penalty: float = 0.2):
        self.corroboration_boost = corroboration_boost
        self.dispute_penalty = dispute_penalty

    def resolve(self, existing: Event, candidate: Event) -> ConflictResolution:
        shared_keys = set(existing.metadata) & set(candidate.metadata)
        disputed_keys = sorted(
            key for key in shared_keys if existing.metadata[key] != candidate.metadata[key]
        )
        is_disputed = bool(disputed_keys)

        # New keys from the candidate are additive information, not conflict.
        merged_metadata = {**candidate.metadata, **existing.metadata}

        if is_disputed:
            merged_confidence = max(
                0.0, min(existing.confidence, candidate.confidence) - self.dispute_penalty
            )
            notes = f"Disputed keys (existing value kept): {disputed_keys}."
        else:
            merged_confidence = min(
                1.0, existing.confidence + (1.0 - existing.confidence) * self.corroboration_boost
            )
            notes = "Corroborated by an additional source; no conflicting metadata."

        return ConflictResolution(
            merged_metadata=merged_metadata,
            merged_confidence=merged_confidence,
            is_disputed=is_disputed,
            disputed_keys=disputed_keys,
            notes=notes,
        )
