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
    specs = seed_sources()
    categories = {s.category for s in specs}
    assert categories == set(SourceCategory) - {SourceCategory.ALTERNATIVE}


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
