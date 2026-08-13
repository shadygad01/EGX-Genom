"""Tests for the capability-driven runtime Acquisition Decision Engine:
`rank_capability_strategies` (pure ranking over registry state) and
`CapabilityDecisionEngine` (rank -> execute -> automatic fallback), both
exercised with fakes -- no network, no concrete collector class.
"""

from __future__ import annotations

from agx_research.acquisition_intelligence.capability import Capability
from agx_research.acquisition_intelligence.capability_engine import (
    CapabilityDecisionEngine,
    rank_capability_strategies,
)
from agx_research.collectors.service import CollectionRunResult
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.reputation import SourceMetricsRepository
from agx_research.sources.spec import (
    AccessMethod,
    SourceCategory,
    SourceSpec,
    SourceStatus,
)


def _spec(source_id: str, *, status: SourceStatus, reliability=0.7, freshness=0.7, conflict_priority=50) -> SourceSpec:
    return SourceSpec(
        id=source_id, name=source_id, category=SourceCategory.MARKET_DATA,
        access_method=AccessMethod.CSV_DOWNLOAD, status=status,
        reliability_score=reliability, freshness_score=freshness, conflict_priority=conflict_priority,
    )


class _FakeCollector:
    def __init__(self, source_id: str, *, fetch_error: Exception | None = None):
        self.spec = _spec(source_id, status=SourceStatus.IMPLEMENTED)
        self._fetch_error = fetch_error
        self.name = source_id
        self.version = "1.0.0"
        self.fetcher = None

    def fetch(self):
        if self._fetch_error:
            raise self._fetch_error
        return []


def _empty_result(source_id: str, *, price_bars=0, financials=0) -> CollectionRunResult:
    return CollectionRunResult(
        source_id=source_id, documents_fetched=1, batches_materialized=0, batches_withheld=0,
        price_bars_written=price_bars, macro_observations_written=0, news_items_written=0,
        corporate_events_written=0, index_constituents_written=0,
        financial_statement_line_items_written=financials, events_registered=0, assessments=[],
    )


class _FakeCollectionService:
    """A stand-in for `CollectionService` that returns pre-scripted results
    per source id, never touching the real fetch/parse/materialize path --
    this test suite is about ranking/fallback orchestration, not collection
    mechanics (already covered by `test_collection_service.py`).
    """

    def __init__(self, results_by_source: dict[str, CollectionRunResult | Exception]):
        self.results_by_source = results_by_source
        self.calls: list[str] = []

    def run(self, collector, *, expected_records: int) -> CollectionRunResult:
        source_id = collector.spec.id
        self.calls.append(source_id)
        outcome = self.results_by_source[source_id]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_rank_capability_strategies_reports_no_active_trading_calendar_source():
    registry = SourceRegistry()
    ranked = rank_capability_strategies(Capability.TRADING_CALENDAR, registry)
    assert ranked == []


def test_rank_capability_strategies_exposes_only_verified_price_source():
    registry = SourceRegistry()
    registry.add(_spec("egx_price_composite", status=SourceStatus.IMPLEMENTED, reliability=0.7, freshness=0.7))
    registry.add(_spec("egx_official_prices", status=SourceStatus.NEEDS_KEY, reliability=0.9, freshness=0.9))

    ranked = rank_capability_strategies(Capability.PRICE_DATA, registry)
    assert [row.source_id for row in ranked] == ["egx_price_composite"]
    assert ranked[0].ready is True


def test_rank_capability_strategies_uses_measured_reputation_when_available():
    registry = SourceRegistry()
    registry.add(_spec("egx_price_composite", status=SourceStatus.IMPLEMENTED, reliability=0.5, freshness=0.5))
    metrics = SourceMetricsRepository()
    metrics.record_run("egx_price_composite", succeeded=True, records_expected=10, records_produced=10)
    for _ in range(5):
        metrics.record_run(
            "egx_price_composite", succeeded=True, records_expected=10, records_produced=10, confidence_score=0.95,
        )

    ranked_without = rank_capability_strategies(Capability.PRICE_DATA, registry)
    ranked_with = rank_capability_strategies(Capability.PRICE_DATA, registry, metrics)
    without_score = next(r for r in ranked_without if r.source_id == "egx_price_composite").composite_score
    with_score = next(r for r in ranked_with if r.source_id == "egx_price_composite").composite_score
    assert with_score != without_score


def test_decide_and_execute_selects_verified_composite_price_source():
    registry = SourceRegistry()
    registry.add(_spec("egx_price_composite", status=SourceStatus.IMPLEMENTED))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService({"egx_price_composite": _empty_result("egx_price_composite", price_bars=10)})
    engine = CapabilityDecisionEngine(registry, factory)
    decision, results, failures = engine.decide_and_execute(Capability.PRICE_DATA, service)

    assert decision.succeeded is True
    assert decision.selected_source_ids == ["egx_price_composite"]
    assert results["egx_price_composite"].price_bars_written == 10
    assert failures == {}
    assert decision.attempts[0].outcome == "succeeded"
    assert service.calls == ["egx_price_composite"]


def test_decide_and_execute_reports_zero_yield_without_unverified_fallback():
    registry = SourceRegistry()
    registry.add(_spec("egx_price_composite", status=SourceStatus.IMPLEMENTED, reliability=0.9, freshness=0.9))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService({"egx_price_composite": _empty_result("egx_price_composite", price_bars=0)})
    engine = CapabilityDecisionEngine(registry, factory)
    decision, results, _failures = engine.decide_and_execute(Capability.PRICE_DATA, service)

    assert decision.succeeded is False
    assert decision.selected_source_ids == []
    assert results["egx_price_composite"].price_bars_written == 0
    assert decision.attempts[0].outcome == "zero_yield"


def test_decide_and_execute_reports_exception_without_unverified_fallback():
    registry = SourceRegistry()
    registry.add(_spec("egx_price_composite", status=SourceStatus.IMPLEMENTED, reliability=0.9, freshness=0.9))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService({"egx_price_composite": RuntimeError("simulated fetch failure")})
    engine = CapabilityDecisionEngine(registry, factory)
    decision, results, failures = engine.decide_and_execute(Capability.PRICE_DATA, service)

    assert decision.selected_source_ids == []
    assert failures == {"egx_price_composite": "RuntimeError: simulated fetch failure"}
    assert results == {}


def test_decide_and_execute_reports_failure_when_nothing_succeeds():
    registry = SourceRegistry()
    registry.add(_spec("stooq", status=SourceStatus.IMPLEMENTED))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService({"stooq": _empty_result("stooq", price_bars=0)})
    engine = CapabilityDecisionEngine(registry, factory)
    decision, _results, _failures = engine.decide_and_execute(Capability.PRICE_DATA, service)

    assert decision.succeeded is False
    assert decision.selected_source_ids == []


def test_decide_and_execute_skips_when_no_live_collector_wiring():
    registry = SourceRegistry()
    registry.add(_spec("egx_price_composite", status=SourceStatus.IMPLEMENTED))

    def factory(source_id, spec):
        return None  # this deployment has no live wiring for anything

    service = _FakeCollectionService({})
    engine = CapabilityDecisionEngine(registry, factory)
    decision, results, failures = engine.decide_and_execute(Capability.PRICE_DATA, service)

    assert decision.succeeded is False
    assert results == {} and failures == {}
    assert decision.attempts[0].outcome == "skipped"
    assert "No live collector wiring" in decision.attempts[0].reason
    assert service.calls == []


def test_macroeconomic_capability_is_exhaustive_not_first_success_only():
    registry = SourceRegistry()
    registry.add(_spec("worldbank", status=SourceStatus.IMPLEMENTED, reliability=0.9, freshness=0.9))
    registry.add(_spec("capmas", status=SourceStatus.IMPLEMENTED, reliability=0.5, freshness=0.5))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService({
        "worldbank": _empty_result("worldbank", price_bars=2),
        "capmas": _empty_result("capmas", price_bars=1),
    })
    engine = CapabilityDecisionEngine(registry, factory)
    decision, results, _failures = engine.decide_and_execute(Capability.MACROECONOMIC, service)

    # Both complementary macro sources run -- this is not a "pick one"
    # capability (World Bank's Egypt CPI and CAPMAS's domestic indices cover
    # disjoint data), so both must be selected, not just the top-ranked one.
    # (Not "fred": excluded from the live MACROECONOMIC pool, see TD-50 --
    # picking a still-included pair keeps this test meaningful.)
    assert set(decision.selected_source_ids) == {"worldbank", "capmas"}
    assert set(results) == {"worldbank", "capmas"}


def test_news_capability_collects_every_ready_outlet_for_corroboration():
    registry = SourceRegistry()
    registry.add(_spec("enterprise_press", status=SourceStatus.IMPLEMENTED))
    registry.add(_spec("alborsa", status=SourceStatus.IMPLEMENTED))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService(
        {
            "enterprise_press": _empty_result("enterprise_press", price_bars=2),
            "alborsa": _empty_result("alborsa", price_bars=3),
        }
    )
    engine = CapabilityDecisionEngine(registry, factory)

    decision, results, _ = engine.decide_and_execute(Capability.NEWS, service)

    assert set(decision.selected_source_ids) == {"enterprise_press", "alborsa"}
    assert set(results) == {"enterprise_press", "alborsa"}


def test_financial_statements_collects_every_ready_issuer():
    registry = SourceRegistry()
    registry.add(_spec("telecom_egypt_ir", status=SourceStatus.IMPLEMENTED))
    registry.add(_spec("orascom_ir", status=SourceStatus.IMPLEMENTED))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService(
        {
            "telecom_egypt_ir": _empty_result("telecom_egypt_ir", financials=8),
            "orascom_ir": _empty_result("orascom_ir", financials=3),
        }
    )
    decision, results, _ = CapabilityDecisionEngine(registry, factory).decide_and_execute(
        Capability.FINANCIAL_STATEMENTS, service
    )

    assert set(decision.selected_source_ids) == {"telecom_egypt_ir", "orascom_ir"}
    assert set(results) == {"telecom_egypt_ir", "orascom_ir"}
    assert service.calls == decision.selected_source_ids


def test_decide_and_execute_reuses_a_source_already_collected_for_another_capability():
    # Real-world shape (sources/catalog.py + capability.py, live-verified
    # 2026-08-02): chief_egx_financials, telecom_egypt_ir, and orascom_ir
    # are each catalogued under both FINANCIAL_STATEMENTS and
    # INVESTOR_RELATIONS. Before "One Collection -> One Canonical Dataset
    # -> Multiple Consumers", the production pipeline's `for capability in
    # Capability:` loop -- which reuses one `CapabilityDecisionEngine`
    # instance across every capability -- fetched each of these sources
    # twice in a single run: once per capability that lists it.
    registry = SourceRegistry()
    registry.add(_spec("chief_egx_financials", status=SourceStatus.IMPLEMENTED))
    registry.add(_spec("telecom_egypt_ir", status=SourceStatus.IMPLEMENTED))
    registry.add(_spec("orascom_ir", status=SourceStatus.IMPLEMENTED))
    registry.add(_spec("egxpilot_fundamentals", status=SourceStatus.IMPLEMENTED))
    registry.add(_spec("egid_financial_filings", status=SourceStatus.TOS_REVIEW))
    registry.add(_spec("company_ir", status=SourceStatus.PLANNED))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService(
        {
            "chief_egx_financials": _empty_result("chief_egx_financials", financials=5),
            "telecom_egypt_ir": _empty_result("telecom_egypt_ir", financials=8),
            "orascom_ir": _empty_result("orascom_ir", financials=3),
            "egxpilot_fundamentals": _empty_result("egxpilot_fundamentals", financials=100),
        }
    )
    engine = CapabilityDecisionEngine(registry, factory)

    fs_decision, _fs_results, _ = engine.decide_and_execute(Capability.FINANCIAL_STATEMENTS, service)
    ir_decision, ir_results, _ = engine.decide_and_execute(Capability.INVESTOR_RELATIONS, service)

    # Each real, shared source was fetched exactly once total across both
    # capability calls, even though both capabilities were satisfied by it.
    for source_id in ("chief_egx_financials", "telecom_egypt_ir", "orascom_ir"):
        assert service.calls.count(source_id) == 1, source_id
        assert source_id in fs_decision.selected_source_ids
        assert source_id in ir_decision.selected_source_ids

    # The second capability's own attempts are honestly labelled "reused",
    # never silently folded into "succeeded" as if it had fetched again.
    ir_attempts = {a.source_id: a for a in ir_decision.attempts}
    for source_id in ("chief_egx_financials", "telecom_egypt_ir", "orascom_ir"):
        assert ir_attempts[source_id].outcome == "reused"
    assert ir_results["chief_egx_financials"].financial_statement_line_items_written == 5

    # egxpilot_fundamentals is only catalogued under FINANCIAL_STATEMENTS,
    # so it is correctly never even considered for INVESTOR_RELATIONS.
    assert "egxpilot_fundamentals" not in ir_attempts


def test_sector_membership_is_satisfied_by_chief_egx_financials_without_a_second_fetch():
    # chief_egx_financials derives real SectorClassification records as a
    # byproduct of collecting financial statements (see
    # chief_financials.py's `_sector_from_csv_url`); it was already running
    # for FINANCIAL_STATEMENTS/INVESTOR_RELATIONS but, before this fix,
    # was never listed under SECTOR_MEMBERSHIP -- so this capability always
    # reported `succeeded=False` even on a run with real sector data.
    registry = SourceRegistry()
    registry.add(_spec("chief_egx_financials", status=SourceStatus.IMPLEMENTED))
    registry.add(_spec("egx_official", status=SourceStatus.DISABLED))

    def factory(source_id, spec):
        return _FakeCollector(source_id)

    service = _FakeCollectionService(
        {"chief_egx_financials": _empty_result("chief_egx_financials", financials=5)}
    )
    engine = CapabilityDecisionEngine(registry, factory)

    engine.decide_and_execute(Capability.FINANCIAL_STATEMENTS, service)
    sector_decision, _, _ = engine.decide_and_execute(Capability.SECTOR_MEMBERSHIP, service)

    assert sector_decision.succeeded is True
    assert sector_decision.selected_source_ids == ["chief_egx_financials"]
    sector_attempt = next(
        a for a in sector_decision.attempts if a.source_id == "chief_egx_financials"
    )
    assert sector_attempt.outcome == "reused"
    assert service.calls.count("chief_egx_financials") == 1


def test_rank_capability_strategies_marks_uncatalogued_source_not_ready():
    registry = SourceRegistry()
    ranked = rank_capability_strategies(Capability.CORPORATE_DISCLOSURES, registry)

    fra = next(row for row in ranked if row.source_id == "fra_egypt")
    assert fra.spec is None
    assert fra.ready is False
    assert "not catalogued" in fra.reason.lower()


def test_rank_capability_strategies_orders_by_composite_and_marks_ready():
    registry = SourceRegistry()
    registry.add(_spec("egx_price_composite", status=SourceStatus.IMPLEMENTED, reliability=0.9, freshness=0.9))

    ranked = rank_capability_strategies(Capability.PRICE_DATA, registry)

    assert [row.source_id for row in ranked] == ["egx_price_composite"]
    assert ranked[0].ready is True
    assert ranked[0].composite_score > 0
