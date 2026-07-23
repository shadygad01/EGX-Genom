"""Structured lineage: what produced this entity, and from what inputs.

This is what makes explainability (Principle 3) more than prose — every
persisted entity in the discovery chain (a finding, a hypothesis, a
knowledge object, a prediction, a recommendation) carries a `Provenance`
pointing at the ids (and versions, where the input is itself versioned) of
whatever produced it. Walking that chain via each entity's repository is
how a "why does this recommendation exist" question gets answered with
data instead of a sentence.

Deliberately not attached to transient computation outputs (experiment
results, validation results) — those aren't identified, persisted entities,
and forcing provenance onto every return value would be ceremony without
benefit.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProvenanceRef(BaseModel):
    """A pointer to one input entity: what kind it is, its id, and (if versioned) which version."""

    kind: str
    ref_id: str
    ref_version: int | str | None = None


class Provenance(BaseModel):
    produced_by: str
    produced_at: datetime
    inputs: list[ProvenanceRef] = Field(default_factory=list)
