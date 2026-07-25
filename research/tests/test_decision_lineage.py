import pytest

from agx_research.production.decision_lineage import export_decision_routes
from agx_research.sources.catalog import seed_registry
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def test_every_implemented_source_has_a_decision_route():
    registry = seed_registry()
    rows = export_decision_routes(registry)
    assert {row["source_id"] for row in rows} == {s.id for s in registry.collectable()}
    assert all(row["records"] and row["consumers"] for row in rows)
    assert all("meta_decision_engine" in row["consumers"] for row in rows)


def test_promoting_a_source_without_a_decision_route_fails_closed():
    registry = seed_registry()
    registry.add(
        SourceSpec(
            id="unrouted",
            name="Unrouted",
            category=SourceCategory.NEWS,
            access_method=AccessMethod.JSON_API,
            status=SourceStatus.IMPLEMENTED,
            reliability_score=0.5,
            freshness_score=0.5,
        )
    )
    with pytest.raises(ValueError, match="unrouted"):
        export_decision_routes(registry)
