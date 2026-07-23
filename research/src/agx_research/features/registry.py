"""A registry of known feature definitions, keyed by (id, version).

Deliberately not a repository (features aren't mutated/versioned at
runtime the way knowledge or hypotheses are) — this is closer to a schema
registry: a place code can look up "what does feature X, version Y, mean"
without every consumer needing to know the definition inline.
"""

from __future__ import annotations

from agx_research.features.definition import FeatureDefinition


class FeatureRegistry:
    def __init__(self) -> None:
        self._definitions: dict[tuple[str, int], FeatureDefinition] = {}

    def register(self, definition: FeatureDefinition) -> FeatureDefinition:
        key = (definition.id, definition.version)
        if key in self._definitions:
            raise ValueError(f"Feature {definition.id} v{definition.version} already registered")
        self._definitions[key] = definition
        return definition

    def get(self, feature_id: str, version: int) -> FeatureDefinition:
        try:
            return self._definitions[(feature_id, version)]
        except KeyError as exc:
            raise KeyError(f"Feature {feature_id} v{version} is not registered") from exc

    def latest_version(self, feature_id: str) -> FeatureDefinition:
        candidates = [d for (fid, _), d in self._definitions.items() if fid == feature_id]
        if not candidates:
            raise KeyError(f"No versions registered for feature {feature_id}")
        return max(candidates, key=lambda d: d.version)
