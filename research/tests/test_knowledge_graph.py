from datetime import date, datetime

from agx_research.config import Horizon
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.graph.builder import edges_from_provenance
from agx_research.graph.knowledge_graph import KnowledgeGraph
from agx_research.graph.nodes import GraphNode, NodeType
from agx_research.hypotheses.hypothesis import Hypothesis, StageResult
from agx_research.hypotheses.pipeline import StageName
from agx_research.knowledge.store import KnowledgeStore
from agx_research.validation.statistical import StatisticalEvidence


def test_add_and_query_nodes_and_edges():
    graph = KnowledgeGraph()
    node_a = graph.add_node(GraphNode(id="a", node_type=NodeType.HYPOTHESIS, label="Hypothesis A"))
    node_b = graph.add_node(GraphNode(id="b", node_type=NodeType.KNOWLEDGE, label="Knowledge B"))
    edge = edges_from_provenance(
        NodeType.KNOWLEDGE,
        "b",
        1,
        Provenance(
            produced_by="test",
            produced_at=datetime.now(),
            inputs=[ProvenanceRef(kind="hypothesis", ref_id="a", ref_version=1)],
        ),
    )[0]
    graph.add_edge(edge)

    neighbors = graph.neighbors("a")
    assert len(neighbors) == 1
    assert neighbors[0].target_id == "b"
    assert node_a.id == "a" and node_b.id == "b"


def test_edges_from_provenance_skips_unrecognized_kinds():
    provenance = Provenance(
        produced_by="test",
        produced_at=datetime.now(),
        inputs=[ProvenanceRef(kind="some_future_kind_not_yet_a_node_type", ref_id="x")],
    )
    edges = edges_from_provenance(NodeType.KNOWLEDGE, "b", 1, provenance)
    assert edges == []


def test_full_chain_is_walkable_from_knowledge_back_to_hypothesis():
    """An end-to-end proof that the graph is a real view over Epoch I provenance,
    not a separately-maintained structure that could drift from it.
    """
    hypothesis = Hypothesis(
        id="hyp-graph",
        statement="test",
        created_by="agent",
        created_at=date(2026, 6, 1),
        horizon=Horizon.SWING,
        affected_assets=["COMI"],
        provenance=Provenance(produced_by="agent@0.1.0", produced_at=datetime.now()),
    )
    for stage in StageName:
        hypothesis = hypothesis.advance(
            StageResult(stage_name=stage.value, passed=True, evaluated_at=datetime.now())
        )

    store = KnowledgeStore()
    knowledge = store.promote(
        hypothesis,
        confidence=0.7,
        statistical_evidence=StatisticalEvidence(
            method="SignificanceThresholdValidator", statistic=2.5, p_value=0.01, sample_size=40
        ),
        economic_explanation="test",
        expected_return=0.03,
        expected_risk=0.02,
    )

    graph = KnowledgeGraph()
    graph.add_node(GraphNode(id=hypothesis.id, node_type=NodeType.HYPOTHESIS, label=hypothesis.statement))
    graph.add_node(GraphNode(id=knowledge.id, node_type=NodeType.KNOWLEDGE, label=knowledge.economic_explanation))
    for edge in edges_from_provenance(NodeType.KNOWLEDGE, knowledge.id, knowledge.version, knowledge.provenance):
        graph.add_edge(edge)

    edges = graph.edges_between(hypothesis.id, knowledge.id)
    assert len(edges) == 1
    assert edges[0].source_type == NodeType.HYPOTHESIS
    assert edges[0].target_type == NodeType.KNOWLEDGE


def _chain_graph():
    """a -> b -> c, plus isolated d."""
    graph = KnowledgeGraph()
    for node_id, node_type in [
        ("a", NodeType.HYPOTHESIS),
        ("b", NodeType.KNOWLEDGE),
        ("c", NodeType.GENE),
        ("d", NodeType.COMPANY),
    ]:
        graph.add_node(GraphNode(id=node_id, node_type=node_type, label=node_id))
    from agx_research.graph.edges import GraphEdge
    from agx_research.domain.identifiers import new_id

    graph.add_edge(GraphEdge(id=new_id("edge"), source_id="a", source_type=NodeType.HYPOTHESIS,
                             target_id="b", target_type=NodeType.KNOWLEDGE, relationship="contributed_to"))
    graph.add_edge(GraphEdge(id=new_id("edge"), source_id="b", source_type=NodeType.KNOWLEDGE,
                             target_id="c", target_type=NodeType.GENE, relationship="contributed_to"))
    return graph


def test_shortest_path_walks_the_chain():
    graph = _chain_graph()
    path = graph.shortest_path("a", "c")
    assert path is not None
    assert [(e.source_id, e.target_id) for e in path] == [("a", "b"), ("b", "c")]


def test_shortest_path_returns_none_when_unreachable():
    graph = _chain_graph()
    assert graph.shortest_path("a", "d") is None


def test_shortest_path_same_node_is_empty():
    assert _chain_graph().shortest_path("a", "a") == []


def test_subgraph_respects_hop_limit():
    graph = _chain_graph()
    nodes_1hop, edges_1hop = graph.subgraph("a", hops=1)
    assert {n.id for n in nodes_1hop} == {"a", "b"}
    assert len(edges_1hop) == 1

    nodes_2hop, _ = graph.subgraph("a", hops=2)
    assert {n.id for n in nodes_2hop} == {"a", "b", "c"}
