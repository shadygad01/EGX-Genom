from datetime import date
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.events.adapters import derive_events_from_snapshot
from agx_research.events.entity import EntityKind
from agx_research.events.entity_resolver import EntityResolver
from agx_research.events.graph_integration import project_events
from agx_research.events.service import EventPlatform
from agx_research.graph.knowledge_graph import KnowledgeGraph
from agx_research.graph.nodes import NodeType
from agx_research.universe.provider import MappingUniverseProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def resolver(macro_ids=("BRENT_USD", "EGP_USD")) -> EntityResolver:
    return EntityResolver(
        MappingUniverseProvider({"COMI": "Commercial International Bank", "MFPC": "MOPCO"}),
        as_of=date(2026, 6, 14),
        known_macro_series_ids=list(macro_ids),
    )


# --- entity resolution ---


def test_resolves_exact_ticker():
    ref = resolver().resolve("COMI")
    assert ref.kind == EntityKind.COMPANY
    assert ref.canonical_id == "COMI"
    assert ref.display_name == "Commercial International Bank"


def test_resolves_company_name_case_insensitively():
    ref = resolver().resolve("commercial international bank")
    assert ref.kind == EntityKind.COMPANY
    assert ref.canonical_id == "COMI"
    assert ref.raw_mention == "commercial international bank"


def test_resolves_known_macro_series():
    ref = resolver().resolve("BRENT_USD")
    assert ref.kind == EntityKind.MACRO_SERIES
    assert ref.canonical_id == "BRENT_USD"


def test_unresolvable_mention_is_unknown_not_guessed():
    ref = resolver().resolve("some random text")
    assert ref.kind == EntityKind.UNKNOWN


# --- end to end: snapshot -> adapters -> platform -> graph ---


def _registered_events():
    provider = MockDataProvider(MOCK_ROOT)
    snapshot = build_snapshot(
        provider,
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD", "EGP_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    platform = EventPlatform()
    return platform.register_all(derive_events_from_snapshot(snapshot))


def test_adapters_produce_resolved_entities_and_valid_subtypes():
    events = _registered_events()
    assert events, "expected the mock snapshot to yield events"
    for event in events:
        assert event.subtype != ""
        for ref in event.entities:
            assert ref.kind in (EntityKind.COMPANY, EntityKind.MACRO_SERIES)


def test_adapter_derivation_is_idempotent_through_the_platform():
    provider = MockDataProvider(MOCK_ROOT)
    snapshot = build_snapshot(
        provider,
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    platform = EventPlatform()
    first = platform.register_all(derive_events_from_snapshot(snapshot))
    second = platform.register_all(derive_events_from_snapshot(snapshot))

    # Re-deriving from the same snapshot re-registers the same ids at the
    # same versions -- no duplicates, no confidence inflation.
    assert {e.id for e in first} == {e.id for e in second}
    assert all(e.version == 1 for e in second)
    assert len(platform.repository.all_latest()) == len({e.id for e in first})


def test_events_project_into_the_knowledge_graph():
    events = _registered_events()
    graph = KnowledgeGraph()
    project_events(graph, events)

    event_nodes = [n for n in graph.nodes.all_latest() if n.node_type == NodeType.EVENT]
    company_nodes = [n for n in graph.nodes.all_latest() if n.node_type == NodeType.COMPANY]
    assert len(event_nodes) == len({e.id for e in events})
    assert {n.id for n in company_nodes} <= {"COMI", "MFPC"}

    # Every event connects to at least one entity node.
    for event in events:
        assert graph.neighbors(event.id), f"event {event.id} has no graph edges"
