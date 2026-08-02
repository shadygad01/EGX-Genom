"""Project events into the Knowledge Graph.

Same discipline as `graph.edges_from_provenance()`: everything here is
derived mechanically from data the Event already carries — its resolved
entities and its typed relationships — never hand-maintained in parallel.
Entity nodes reuse the graph's existing `NodeType` vocabulary (COMPANY,
SECTOR, MARKET, MACRO_SERIES) so events, companies, and research artifacts
all live in one graph, not an event-only silo.
"""

from __future__ import annotations

from agx_research.domain.identifiers import new_id
from agx_research.events.entity import EntityKind
from agx_research.events.event import Event
from agx_research.graph.edges import GraphEdge
from agx_research.graph.knowledge_graph import KnowledgeGraph
from agx_research.graph.nodes import GraphNode, NodeType

_ENTITY_KIND_TO_NODE_TYPE: dict[EntityKind, NodeType] = {
    EntityKind.COMPANY: NodeType.COMPANY,
    EntityKind.SECTOR: NodeType.SECTOR,
    EntityKind.MACRO_SERIES: NodeType.MACRO_SERIES,
    EntityKind.MARKET: NodeType.MARKET,
}


def event_node(event: Event) -> GraphNode:
    return GraphNode(
        id=event.id,
        version=event.version,
        node_type=NodeType.EVENT,
        label=f"{event.event_type.value}/{event.subtype} @ {event.event_date.isoformat()}",
        metadata={
            "status": event.status.value,
            "severity": event.severity.value,
            "confidence": event.confidence,
        },
    )


def entity_nodes(event: Event) -> list[GraphNode]:
    """One node per resolvable entity; UNKNOWN entities are skipped rather
    than polluting the graph with unresolved mentions."""
    nodes: list[GraphNode] = []
    for entity in event.entities:
        node_type = _ENTITY_KIND_TO_NODE_TYPE.get(entity.kind)
        if node_type is None:
            continue
        nodes.append(
            GraphNode(
                id=entity.canonical_id,
                node_type=node_type,
                label=entity.display_name or entity.canonical_id,
            )
        )
    return nodes


def involvement_edges(event: Event) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    for entity in event.entities:
        node_type = _ENTITY_KIND_TO_NODE_TYPE.get(entity.kind)
        if node_type is None:
            continue
        edges.append(
            GraphEdge(
                id=new_id("edge"),
                source_id=event.id,
                source_type=NodeType.EVENT,
                target_id=entity.canonical_id,
                target_type=node_type,
                relationship="involves",
                metadata={"event_version": event.version},
            )
        )
    return edges


def relationship_edges(event: Event) -> list[GraphEdge]:
    return [
        GraphEdge(
            id=new_id("edge"),
            source_id=event.id,
            source_type=NodeType.EVENT,
            target_id=relationship.related_event_id,
            target_type=NodeType.EVENT,
            relationship=relationship.relationship_type.value,
            metadata={"notes": relationship.notes},
        )
        for relationship in event.relationships
    ]


def project_event(graph: KnowledgeGraph, event: Event, *, persist: bool = True) -> None:
    """Add one event, its entities, and every derived edge to the graph."""
    graph.add_node(event_node(event), persist=persist)
    for node in entity_nodes(event):
        if graph.nodes.latest(node.id) is None:
            graph.add_node(node, persist=persist)
    for edge in [*involvement_edges(event), *relationship_edges(event)]:
        graph.add_edge(edge, persist=persist)


def project_events(graph: KnowledgeGraph, events: list[Event]) -> None:
    try:
        for event in events:
            project_event(graph, event, persist=False)
    finally:
        graph.flush()
