"""Regression tests for the Decision-Centric Gap Audit / Architecture
Adversarial Review's capability changes: the ECONOMIC_RELEASES/
MACROECONOMIC merge (R3 folds Q5/Q9 into one Country & Macro Risk axis)
and the new Sovereign & Credit Context sources feeding it.
"""

from __future__ import annotations

from agx_research.acquisition_intelligence.capability import CAPABILITY_STRATEGIES, Capability
from agx_research.acquisition_intelligence.target import seed_target_organizations
from agx_research.sources.catalog import seed_sources


def test_economic_releases_capability_no_longer_exists():
    assert not hasattr(Capability, "ECONOMIC_RELEASES")
    assert "economic_releases" not in {c.value for c in Capability}


def test_macroeconomic_pool_absorbs_former_economic_releases_sources():
    pool = CAPABILITY_STRATEGIES[Capability.MACROECONOMIC]
    for source_id in ("trading_economics", "cbe", "capmas", "mof_egypt"):
        assert source_id in pool


def test_macroeconomic_pool_includes_new_sovereign_credit_sources():
    pool = CAPABILITY_STRATEGIES[Capability.MACROECONOMIC]
    for source_id in ("moodys_ratings", "sp_global_ratings", "fitch_ratings"):
        assert source_id in pool


def test_news_pool_includes_amwal_alghad():
    assert "amwal_alghad" in CAPABILITY_STRATEGIES[Capability.NEWS]


def test_macroeconomic_pool_includes_previously_unmapped_gov_and_external_sector_sources():
    # Mission Completion Review finding: egypt_open_data/suez_canal_stats
    # were catalogued but had zero capability mapping at all.
    pool = CAPABILITY_STRATEGIES[Capability.MACROECONOMIC]
    assert "egypt_open_data" in pool
    assert "suez_canal_stats" in pool


def test_every_capability_strategy_id_exists_in_the_source_catalog():
    catalog_ids = {s.id for s in seed_sources()}
    for capability, pool in CAPABILITY_STRATEGIES.items():
        for source_id in pool:
            assert source_id in catalog_ids, f"{capability}: {source_id} not in catalog"


def test_every_target_organization_source_ref_exists_in_the_catalog():
    catalog_ids = {s.id for s in seed_sources()}
    for target in seed_target_organizations():
        if target.existing_source_id:
            assert target.existing_source_id in catalog_ids, target.id


def test_new_sovereign_and_amwal_targets_are_seeded():
    ids = {t.id for t in seed_target_organizations()}
    assert {"moodys_ratings", "sp_global_ratings", "fitch_ratings", "amwal_alghad"} <= ids


def test_fred_excluded_from_live_macroeconomic_pool():
    # Regression test (2026-07-31, TD-50): 3 consecutive real live
    # `deploy-pages.yml` runs all timed out fetching FRED, so it was never
    # actually a working live dependency. `fred`'s `SourceSpec` stays
    # IMPLEMENTED/catalogued (the collector and its own unit tests are
    # real, legitimate code) -- only the live capability pool that decides
    # what actually gets fetched stopped depending on it.
    assert "fred" not in CAPABILITY_STRATEGIES[Capability.MACROECONOMIC]
    assert "fred" in {s.id for s in seed_sources()}
