"""The Knowledge Graph: nodes and versioned relationships between them.

Backed by two `Repository[T]`s (nodes, edges) rather than a dedicated graph
database — consistent with the rest of the system, and sufficient for a
scaffold's query needs (neighbors, path between two nodes). Swapping in a
real graph database later is a new `Repository[T]` implementation behind
the same interface, not a rewrite of this class.
"""

from __future__ import annotations

from pathlib import Path

from agx_research.graph.edges import GraphEdge
from agx_research.graph.nodes import GraphNode
from agx_research.storage.repository import JsonFileRepository


class KnowledgeGraph:
    def __init__(
        self,
        node_persist_path: Path | str | None = None,
        edge_persist_path: Path | str | None = None,
    ):
        self.nodes: JsonFileRepository[GraphNode] = JsonFileRepository(GraphNode, node_persist_path)
        self.edges: JsonFileRepository[GraphEdge] = JsonFileRepository(GraphEdge, edge_persist_path)

    def add_node(self, node: GraphNode) -> GraphNode:
        return self.nodes.add(node)

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        return self.edges.add(edge)

    def neighbors(self, node_id: str) -> list[GraphEdge]:
        return [
            e for e in self.edges.all_latest() if e.source_id == node_id or e.target_id == node_id
        ]

    def edges_between(self, node_a_id: str, node_b_id: str) -> list[GraphEdge]:
        return [
            e
            for e in self.edges.all_latest()
            if {e.source_id, e.target_id} == {node_a_id, node_b_id}
        ]
