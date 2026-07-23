"""The Alpha Genome: passive Pattern storage replaced by a living lineage.

Epoch I's `KnowledgeObject`/`KnowledgeStore` are untouched — they remain
the system of record for what passed the promotion gate. `Gene` is the
evolutionary layer on top: it wraps a `KnowledgeObject` and tracks how
knowledge about the same underlying idea evolves over time. A `Gene` is
never overwritten to reflect new evidence — `AlphaGenome.mutate()` (see
`service.py`) always creates a brand new child gene referencing its parent,
and marks the parent `REPLACED` rather than deleting or rewriting it. Old
knowledge is retired, not erased.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.domain.provenance import Provenance
from agx_research.knowledge.schema import PerformanceRecord


class GeneStatus(str, Enum):
    PROPOSED = "proposed"
    PROMOTED = "promoted"
    MONITORING = "monitoring"
    RETIRED = "retired"
    REPLACED = "replaced"


_ALLOWED_TRANSITIONS: dict[GeneStatus, set[GeneStatus]] = {
    GeneStatus.PROPOSED: {GeneStatus.PROMOTED, GeneStatus.RETIRED},
    GeneStatus.PROMOTED: {GeneStatus.MONITORING, GeneStatus.RETIRED, GeneStatus.REPLACED},
    GeneStatus.MONITORING: {GeneStatus.RETIRED, GeneStatus.REPLACED},
    GeneStatus.RETIRED: set(),
    GeneStatus.REPLACED: set(),
}


def can_transition(current: GeneStatus, target: GeneStatus) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


class Gene(BaseModel):
    id: str
    version: int = 1
    knowledge_id: str
    generation: int = 0
    parent_gene_ids: list[str] = Field(default_factory=list)
    child_gene_ids: list[str] = Field(default_factory=list)
    mutation_notes: str = ""
    evidence: list[str] = Field(default_factory=list)
    performance_history: list[PerformanceRecord] = Field(default_factory=list)
    status: GeneStatus = GeneStatus.PROMOTED
    retired_at: date | None = None
    retirement_reason: str | None = None
    provenance: Provenance
