from agx_research.methodology import MethodologyRegistry, seed_methodology_registry, seed_research_sources
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import SourceCategory, SourceStatus


def test_seed_research_sources_covers_arxiv_ssrn_nber():
    ids = {s.id for s in seed_research_sources()}
    assert ids == {"arxiv", "ssrn", "nber"}


def test_research_sources_are_planned_and_uncatalogued_for_decisions():
    # None of these carry a collector or a Capability mapping -- they must
    # never be wired into the operational collector plan or capability
    # engine.
    for spec in seed_research_sources():
        assert spec.status == SourceStatus.PLANNED
        assert spec.category == SourceCategory.RESEARCH
        assert spec.collector is None
        assert spec.integrated_capabilities == []


def test_seed_methodology_registry_is_independent_of_the_operational_registry():
    registry = seed_methodology_registry()
    assert isinstance(registry, SourceRegistry)
    ids = {s.id for s in registry.all_latest()}
    assert ids == {"arxiv", "ssrn", "nber"}
    assert isinstance(registry, MethodologyRegistry)
    assert registry.claims.all_latest() == []


def test_seed_methodology_registry_is_idempotent():
    registry = seed_methodology_registry()
    before = {s.id: s.version for s in registry.all_latest()}

    seed_methodology_registry(registry)

    after = {s.id: s.version for s in registry.all_latest()}
    assert before == after


def test_seed_methodology_registry_retires_a_source_removed_from_its_own_catalog():
    from agx_research.sources.spec import ActivationStatus

    registry = SourceRegistry()
    registry.add(
        seed_research_sources()[0].model_copy(update={"id": "no_longer_in_methodology_catalog"})
    )

    seed_methodology_registry(registry)

    retired = registry.latest("no_longer_in_methodology_catalog")
    assert retired.status == SourceStatus.DISABLED
    assert retired.activation_status == ActivationStatus.RETIRED
