from agx_research.acquisition_intelligence.target import seed_target_organizations
from agx_research.sources.catalog import seed_sources


def test_target_ids_are_unique():
    targets = seed_target_organizations()
    ids = [t.id for t in targets]
    assert len(ids) == len(set(ids))


def test_every_target_with_existing_source_id_actually_exists_in_seed_catalog():
    existing_ids = {s.id for s in seed_sources()}
    for target in seed_target_organizations():
        if target.existing_source_id:
            assert target.existing_source_id in existing_ids, target.existing_source_id


def test_non_per_constituent_targets_have_at_least_one_domain_hint():
    for target in seed_target_organizations():
        if not target.per_constituent:
            assert target.domain_hints, f"{target.id} has no domain hints"


def test_company_ir_is_marked_per_constituent():
    targets = {t.id: t for t in seed_target_organizations()}
    assert targets["company_ir"].per_constituent is True
