import pytest

from agx_research.sources import (
    AccessMethod,
    SourceCategory,
    SourceRegistry,
    SourceSpec,
    SourceStatus,
    seed_registry,
    seed_sources,
)


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="test_source",
        name="Test Source",
        category=SourceCategory.MARKET_DATA,
        access_method=AccessMethod.CSV_DOWNLOAD,
        status=SourceStatus.IMPLEMENTED,
        reliability_score=0.8,
        freshness_score=0.9,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


def test_seed_sources_covers_every_named_category_still_in_active_use():
    # SourceCategory.ALTERNATIVE is intentionally excluded: the seed
    # catalog no longer emits any source under it (Decision-Centric Gap
    # Audit, 2026-07-30), but the enum member itself must stay so real,
    # already-persisted production registry state with that category
    # (from before the cleanup) keeps deserializing -- see sources/spec.py.
    # SourceCategory.RESEARCH is excluded the same way, for the same
    # reason: arxiv/ssrn/nber moved out to the separate, non-operational
    # `agx_research.methodology.catalog` registry (2026-08-02), but the
    # enum member stays for the same real-persisted-data reason.
    specs = seed_sources()
    categories = {s.category for s in specs}
    assert categories == set(SourceCategory) - {
        SourceCategory.ALTERNATIVE,
        SourceCategory.RESEARCH,
    }


def test_research_sources_moved_out_of_the_operational_catalog():
    # Regression test for the 2026-08-02 registry split: arxiv/ssrn/nber
    # must never appear in the operational catalog (they'd otherwise be
    # picked up by production.pipeline.ProductionPipeline / the capability
    # engine) -- they live in agx_research.methodology.catalog instead.
    ids = {s.id for s in seed_sources()}
    assert ids.isdisjoint({"arxiv", "ssrn", "nber"})


def test_legacy_alternative_category_still_deserializes():
    # Regression test for a real production incident (2026-07-31): removing
    # SourceCategory.ALTERNATIVE entirely broke loading real, already-
    # persisted source_registry.json revisions carrying that category.
    spec = SourceSpec.model_validate(
        {
            "id": "legacy_source",
            "name": "Legacy Source",
            "category": "alternative",
            "access_method": "json_api",
            "status": "planned",
            "reliability_score": 0.5,
            "freshness_score": 0.5,
        }
    )
    assert spec.category == SourceCategory.ALTERNATIVE


def test_seed_sources_ids_are_unique():
    specs = seed_sources()
    ids = [s.id for s in specs]
    assert len(ids) == len(set(ids))


def test_decision_centric_audit_removed_tier_4_sources():
    ids = {s.id for s in seed_sources()}
    removed = {
        "wikipedia_pageviews", "google_trends", "github_releases",
        "company_social_official", "public_telegram", "patents",
        "hiring_signals", "google_scholar", "researchgate",
        "investing_com", "tradingview",
    }
    assert ids.isdisjoint(removed)


def test_decision_centric_audit_added_sovereign_and_amwal_sources():
    ids = {s.id for s in seed_sources()}
    added = {"moodys_ratings", "sp_global_ratings", "fitch_ratings", "amwal_alghad"}
    assert added <= ids


def test_seed_registry_status_breakdown_matches_seed_sources():
    registry = seed_registry()
    specs = seed_sources()
    for status in SourceStatus:
        expected = len([s for s in specs if s.status == status])
        assert len(registry.by_status(status)) == expected


def test_only_implemented_sources_are_collectable():
    registry = seed_registry()
    collectable = registry.collectable()
    assert collectable  # at least Stooq/FRED/RSS
    assert all(s.status == SourceStatus.IMPLEMENTED for s in collectable)


def test_data_quality_score_starts_unset_for_every_seeded_source():
    for spec in seed_sources():
        assert spec.data_quality_score is None


def test_by_category_filters_correctly():
    registry = SourceRegistry()
    registry.add(make_spec(id="a", category=SourceCategory.NEWS))
    registry.add(make_spec(id="b", category=SourceCategory.MACROECONOMIC))
    assert [s.id for s in registry.by_category(SourceCategory.NEWS)] == ["a"]


def test_record_measured_quality_creates_new_version_not_edit_in_place():
    registry = SourceRegistry()
    registry.add(make_spec(id="a"))
    updated = registry.record_measured_quality("a", 0.73)
    assert updated.version == 2
    assert updated.data_quality_score == 0.73
    history = registry.history("a")
    assert len(history) == 2
    assert history[0].data_quality_score is None


def test_record_measured_quality_unknown_source_raises():
    registry = SourceRegistry()
    with pytest.raises(KeyError):
        registry.record_measured_quality("does_not_exist", 0.5)


def test_retire_removed_disables_a_source_dropped_from_the_catalog():
    registry = SourceRegistry()
    registry.add(make_spec(id="dead_source", status=SourceStatus.PLANNED))

    [retired] = registry.retire_removed(current_catalog_ids={"some_other_source"})

    assert retired.id == "dead_source"
    assert retired.version == 2
    assert retired.status == SourceStatus.DISABLED
    from agx_research.sources.spec import ActivationStatus

    assert retired.activation_status == ActivationStatus.RETIRED
    assert "no longer in the source catalog" in retired.notes
    history = registry.history("dead_source")
    assert len(history) == 2
    assert history[0].status == SourceStatus.PLANNED


def test_retire_removed_leaves_still_catalogued_sources_untouched():
    registry = SourceRegistry()
    registry.add(make_spec(id="still_here", status=SourceStatus.IMPLEMENTED))

    retired = registry.retire_removed(current_catalog_ids={"still_here"})

    assert retired == []
    assert registry.latest("still_here").version == 1


def test_retire_removed_does_not_re_touch_an_already_disabled_source():
    registry = SourceRegistry()
    registry.add(make_spec(id="already_dead", status=SourceStatus.DISABLED))

    retired = registry.retire_removed(current_catalog_ids=set())

    assert retired == []
    assert registry.latest("already_dead").version == 1


def test_seed_registry_retires_a_source_deleted_from_the_seed_catalog():
    # Regression test for a real, live-evidenced gap: `seed_registry()`
    # only ever adds a new id, so deleting a `SourceSpec` from
    # `sources.catalog` never reached an already-running deployment's
    # persisted registry -- inspecting real production state showed all
    # 11 sources the Decision-Centric Redesign claimed to remove were
    # still sitting there as PLANNED, months later.
    registry = SourceRegistry()
    registry.add(make_spec(id="no_longer_catalogued", status=SourceStatus.PLANNED))

    seed_registry(registry)

    retired = registry.latest("no_longer_catalogued")
    assert retired.status == SourceStatus.DISABLED
    # Every currently-catalogued source must still be present and untouched.
    for spec in seed_sources():
        assert registry.latest(spec.id).id == spec.id


def test_amwal_alghad_is_implemented_with_a_real_verified_feed_url():
    # Regression test for the 2026-07-31 promotion: the weekly discovery
    # workflow's real network egress independently verified this feed
    # reachable (robots.txt permits it, a live probe succeeded, and the
    # Wayback Machine shows 143 archived snapshots spanning 1229 days) --
    # promoted on that evidence, same as every prior RSS-outlet promotion
    # in this registry.
    [spec] = [s for s in seed_sources() if s.id == "amwal_alghad"]
    assert spec.status == SourceStatus.IMPLEMENTED
    assert spec.collector == "RssNewsCollector"
    assert spec.base_url == "https://amwalalghad.com/feed/atom/"


def test_sync_declared_fields_promotes_an_already_persisted_planned_source():
    # Regression test for a real production incident (2026-07-31):
    # promoting amwal_alghad from PLANNED to IMPLEMENTED in the catalog
    # had no effect on a deployment that had already persisted its old
    # PLANNED spec, because seed_registry()'s add-loop only adds a
    # brand-new id -- it never revisits one that already exists.
    registry = SourceRegistry()
    registry.add(make_spec(id="amwal_alghad", status=SourceStatus.PLANNED))

    seed_registry(registry)

    spec = registry.latest("amwal_alghad")
    assert spec.status == SourceStatus.IMPLEMENTED
    assert spec.collector == "RssNewsCollector"
    assert spec.base_url == "https://amwalalghad.com/feed/atom/"
    assert spec.version == 2
    from agx_research.sources.spec import ActivationStatus, LifecycleState

    assert spec.lifecycle_state == LifecycleState.TRUSTED
    assert spec.activation_status == ActivationStatus.ACTIVE


def test_sync_declared_fields_preserves_measured_runtime_fields():
    registry = SourceRegistry()
    registry.add(make_spec(id="amwal_alghad", status=SourceStatus.PLANNED))
    registry.record_measured_quality("amwal_alghad", 0.62)
    from agx_research.sources.spec import HealthStatus

    registry.update_health("amwal_alghad", HealthStatus.DEGRADED)

    seed_registry(registry)

    spec = registry.latest("amwal_alghad")
    assert spec.status == SourceStatus.IMPLEMENTED
    assert spec.data_quality_score == 0.62
    assert spec.health_status == HealthStatus.DEGRADED


def test_sync_declared_fields_is_a_no_op_when_nothing_changed():
    registry = SourceRegistry()
    seed_registry(registry)
    before = registry.latest("amwal_alghad").version

    seed_registry(registry)

    assert registry.latest("amwal_alghad").version == before


def test_sync_declared_fields_does_not_reset_an_earned_lifecycle_stage_when_status_is_unchanged():
    registry = SourceRegistry()
    registry.add(make_spec(id="a", status=SourceStatus.IMPLEMENTED))
    from agx_research.sources.spec import LifecycleState

    registry.transition_lifecycle("a", LifecycleState.CORE)

    synced = registry.sync_declared_fields([make_spec(id="a", status=SourceStatus.IMPLEMENTED)])

    assert synced == []
    assert registry.latest("a").lifecycle_state == LifecycleState.CORE
