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

    def _adjacency(self) -> dict[str, list[GraphEdge]]:
        adjacency: dict[str, list[GraphEdge]] = {}
        for edge in self.edges.all_latest():
            adjacency.setdefault(edge.source_id, []).append(edge)
            adjacency.setdefault(edge.target_id, []).append(edge)
        return adjacency

    def shortest_path(self, from_id: str, to_id: str) -> list[GraphEdge] | None:
        """BFS shortest path (edges treated as undirected — provenance
        questions are asked in both directions: "what led to X" and "what
        did X lead to"). Returns the edge sequence, or None if unreachable.
        """
        if from_id == to_id:
            return []
        adjacency = self._adjacency()
        visited = {from_id}
        frontier: list[tuple[str, list[GraphEdge]]] = [(from_id, [])]
        while frontier:
            next_frontier: list[tuple[str, list[GraphEdge]]] = []
            for node_id, path in frontier:
                for edge in adjacency.get(node_id, []):
                    other = edge.target_id if edge.source_id == node_id else edge.source_id
                    if other in visited:
                        continue
                    new_path = [*path, edge]
                    if other == to_id:
                        return new_path
                    visited.add(other)
                    next_frontier.append((other, new_path))
            frontier = next_frontier
        return None

    def subgraph(self, root_id: str, *, hops: int = 1) -> tuple[list[GraphNode], list[GraphEdge]]:
        """The n-hop neighborhood around `root_id`: every node reachable in
        at most `hops` undirected steps, plus every edge between them."""
        adjacency = self._adjacency()
        reached = {root_id}
        frontier = {root_id}
        for _ in range(hops):
            next_frontier: set[str] = set()
            for node_id in frontier:
                for edge in adjacency.get(node_id, []):
                    other = edge.target_id if edge.source_id == node_id else edge.source_id
                    if other not in reached:
                        next_frontier.add(other)
            reached |= next_frontier
            frontier = next_frontier
            if not frontier:
                break
        nodes = [n for n in self.nodes.all_latest() if n.id in reached]
        edges = [
            e for e in self.edges.all_latest() if e.source_id in reached and e.target_id in reached
        ]
        return nodes, edges
