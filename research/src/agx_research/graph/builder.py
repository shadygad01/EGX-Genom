"""Mechanically turns an entity's Provenance into GraphEdges.

The Knowledge Graph is largely a *view* over provenance that Epoch I
already produces on every persisted entity, not a new, separately
maintained source of truth — avoiding the classic bug of a graph that
drifts from the data it's supposed to represent.
"""

from __future__ import annotations

from agx_research.domain.identifiers import new_id
from agx_research.domain.provenance import Provenance
from agx_research.graph.edges import GraphEdge
from agx_research.graph.nodes import NodeType


def edges_from_provenance(
    entity_type: NodeType,
    entity_id: str,
    entity_version: int,
    provenance: Provenance,
    *,
    relationship: str = "contributed_to",
) -> list[GraphEdge]:
    """One edge per `provenance.inputs` entry, pointing from that input to this entity.

    Silently skips any `ProvenanceRef.kind` that isn't a recognized
    `NodeType` rather than mislabeling it. Every `kind` string used
    elsewhere in this codebase (hypothesis, knowledge, dataset_snapshot,
    feature, gene, research_finding, prediction) is already a `NodeType`
    member, so a skip here is a signal to add the new kind to `NodeType`,
    not a silent failure to worry about routinely.
    """
    edges: list[GraphEdge] = []
    for ref in provenance.inputs:
        try:
            source_type = NodeType(ref.kind)
        except ValueError:
            continue
        edges.append(
            GraphEdge(
                id=new_id("edge"),
                source_id=ref.ref_id,
                source_type=source_type,
                target_id=entity_id,
                target_type=entity_type,
                relationship=relationship,
                metadata={"source_version": ref.ref_version, "target_version": entity_version},
            )
        )
    return edges
