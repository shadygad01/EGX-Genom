from agx_research.acquisition_intelligence.target import (
    PRIORITY_CBE,
    PRIORITY_EGX_OFFICIAL,
    PRIORITY_EGX30_IR,
    generate_company_ir_targets,
    seed_target_organizations,
)
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


def test_egx_official_has_the_lowest_priority_number():
    targets = seed_target_organizations()
    non_per_constituent = [t for t in targets if not t.per_constituent]
    assert min(t.priority for t in non_per_constituent) == PRIORITY_EGX_OFFICIAL
    egx = next(t for t in targets if t.id == "egx_official")
    assert egx.priority == PRIORITY_EGX_OFFICIAL
    assert all(t.priority >= egx.priority for t in non_per_constituent)


def test_named_priority_targets_match_the_mission_order():
    by_id = {t.id: t.priority for t in seed_target_organizations()}
    assert by_id["egx_official"] < by_id["cbe"] == PRIORITY_CBE
    assert by_id["cbe"] < by_id["fra_egypt"] < by_id["capmas"] < by_id["enterprise_press"]
    assert by_id["enterprise_press"] < by_id["mubasher"] < by_id["zawya"] < by_id["reuters"]
    assert by_id["reuters"] < by_id["trading_economics"]
    # Sources not named in the mission's explicit list fall into the
    # catch-all "additional discovered source" tier, at or below every
    # explicitly-named source.
    assert by_id["asharq_business"] >= by_id["trading_economics"]
    assert by_id["cnbc_arabia"] >= by_id["trading_economics"]


def test_generate_company_ir_targets_produces_one_per_company_with_no_fabricated_hints():
    companies = {"COMI": "Commercial International Bank", "MFPC": "Misr Fertilizers Production Company"}
    targets = generate_company_ir_targets(companies)

    assert len(targets) == 2
    ids = {t.id for t in targets}
    assert ids == {"company_ir_comi", "company_ir_mfpc"}
    for target in targets:
        assert target.domain_hints == []  # never guessed
        assert target.priority == PRIORITY_EGX30_IR
        assert target.company_ticker in companies
        assert target.company_ticker in target.notes  # readable, traceable back to the ticker
        assert companies[target.company_ticker] in target.name


def test_generate_company_ir_targets_accepts_a_custom_priority():
    targets = generate_company_ir_targets({"X": "Company X"}, priority=99)
    assert targets[0].priority == 99


def test_generate_company_ir_targets_is_deterministically_sorted():
    companies = {"B": "Beta Corp", "A": "Alpha Corp"}
    targets = generate_company_ir_targets(companies)
    assert [t.company_ticker for t in targets] == ["A", "B"]
