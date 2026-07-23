"""A versioned, reusable computation over a DatasetSnapshot.

Principle 5 names Features as a versioned entity distinct from raw data and
models. Registering a feature once and referencing it by (id, version) from
any agent, experiment, or model — instead of inlining the same arithmetic
in each one — is what makes that versioning meaningful rather than nominal.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeatureDefinition(BaseModel):
    id: str
    version: int = 1
    name: str
    description: str
    inputs: list[str] = Field(default_factory=list)
