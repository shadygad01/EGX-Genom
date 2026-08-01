"""Institutional Investment Validation's own tests -- not just software
tests: this file is the record that the 10 repeatable scenarios keep
producing the verdicts this codebase can defend, so a regression in the
decision engine (not just in this validation package) fails CI here too.
"""

from datetime import date, timedelta

import pytest

from agx_research.decision_service.country_risk import CountryRiskSeverity
from agx_research.institutional_validation import checks, scenarios as sc
from agx_research.institutional_validation.diffing import diff_knowledge_history, diff_knowledge_revisions
from agx_research.institutional_validation.report import CheckVerdict, ValidationReport
from agx_research.institutional_validation.runner import run_institutional_validation
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.meta.decision_engine import DecisionAction
from agx_research.meta.decision_ledger import OutcomeStatus

AS_OF = date(2026, 6, 14)
LIFECYCLE_START = date(2026, 1, 1)


# --- scenarios.py -------------------------------------------------------


def test_real_universe_tickers_are_the_real_checked_in_lists():
    egx30, egx70 = sc.real_universe_tickers()
    assert len(egx30) == 31
    assert len(egx70) == 70
    assert len(set(egx30) & set(egx70)) == 0
    assert "COMI" in egx30


def test_synthetic_full_universe_covers_every_ticker_with_real_diversity():
    tickers = [f"T{i}" for i in range(40)]
    scenario = sc.synthetic_full_universe(tickers, AS_OF)
    assert len(scenario.recommendations) == 40
    actions = {
        decision.action
        for rec in scenario.recommendations
        for decision in rec.horizon_decisions.values()
    }
    # All four real outcomes must appear -- a scenario that only ever
    # produced BUY_CANDIDATE would prove nothing about rejection.
    assert actions == {
        DecisionAction.BUY_CANDIDATE, DecisionAction.AVOID, DecisionAction.ABSTAIN, DecisionAction.WATCH,
    }


def test_synthetic_full_universe_positions_carry_positive_max_position_pct():
    """Regression guard for the scenario-construction bug
    check_complete_portfolio caught during development: publication-ready
    BUY_CANDIDATE decisions must have gone through the real publication
    gate (max_position_pct > 0), not just a hand-set publication_status."""
    scenario = sc.synthetic_full_universe([f"T{i}" for i in range(20)], AS_OF)
    buy_decisions = [
        decision
        for rec in scenario.recommendations
        for decision in rec.horizon_decisions.values()
        if decision.action == DecisionAction.BUY_CANDIDATE
    ]
    assert buy_decisions
    assert all(decision.max_position_pct > 0 for decision in buy_decisions)


def test_zero_evidence_universe_produces_no_recommendations():
    scenario = sc.zero_evidence_universe(["A", "B", "C"], AS_OF)
    assert scenario.recommendations == []


def test_all_reject_universe_has_no_buy_candidate():
    scenario = sc.all_reject_universe([f"R{i}" for i in range(10)], AS_OF)
    actions = {
        decision.action
        for rec in scenario.recommendations
        for decision in rec.horizon_decisions.values()
    }
    assert DecisionAction.BUY_CANDIDATE not in actions


def test_thesis_lifecycle_scenario_retires_the_failing_thesis_not_the_holding_one():
    lifecycle = sc.thesis_lifecycle_scenario(LIFECYCLE_START)
    for evaluation_date in lifecycle.evaluation_dates:
        lifecycle.monitor.evaluate(evaluation_date)
    fail_knowledge = lifecycle.knowledge_store.latest(f"synthetic-{lifecycle.failing_ticker}")
    hold_knowledge = lifecycle.knowledge_store.latest(f"synthetic-{lifecycle.holding_ticker}")
    assert fail_knowledge.status == KnowledgeStatus.RETIRED
    assert hold_knowledge.status != KnowledgeStatus.RETIRED


def test_benchmark_scenario_produces_a_hand_verifiable_excess_return():
    from agx_research.meta.decision_ledger import DecisionLedger

    bench = sc.benchmark_scenario(AS_OF, AS_OF + timedelta(days=50))
    ledger = DecisionLedger()
    ledger.record_recommendations([bench.recommendation])
    ledger.evaluate_expired(bench.snapshot_at_evaluation, benchmark_ticker=bench.benchmark_ticker)
    record = ledger.all_latest()[0]
    assert record.outcome_status == OutcomeStatus.EVALUATED
    expected_realized = (bench.exit_price - bench.entry_price) / bench.entry_price - 20.0 / 10_000
    assert record.realized_return == pytest.approx(expected_realized)
    assert record.hit is True  # ticker (+1%/day) comfortably outpaces the benchmark (+0.3%/day)


def test_evidence_chain_scenario_walks_hypothesis_to_decision():
    chain = sc.evidence_chain_scenario(AS_OF)
    assert chain.knowledge.provenance.inputs[0].ref_id == chain.hypothesis_stub.id
    assert any(ref.ref_id == chain.knowledge.id for ref in chain.recommendation.provenance.inputs)
    assert chain.position_aware_decision.action.value == "buy"


def test_country_crisis_scenario_zeroes_target_weight_despite_maximal_conviction():
    from agx_research.decision_service.position import PositionState
    from agx_research.decision_service.service import DecisionService

    recommendations, crisis = sc.country_crisis_scenario(AS_OF)
    assert crisis.severity == CountryRiskSeverity.CRISIS
    positions = {"CRISISTEST": PositionState(ticker="CRISISTEST", held=False)}
    decisions = DecisionService().decide_portfolio(recommendations, positions, AS_OF, country_risk=crisis)
    assert decisions[0].target_weight == 0.0
    assert decisions[0].action.value == "no_action"


# --- diffing.py -----------------------------------------------------------


def test_diff_knowledge_revisions_reports_no_change_honestly():
    lifecycle = sc.thesis_lifecycle_scenario(LIFECYCLE_START)
    knowledge = lifecycle.knowledge_store.latest(f"synthetic-{lifecycle.failing_ticker}")
    diff = diff_knowledge_revisions(knowledge, knowledge)
    assert diff.changed_fields == []
    assert "no tracked field changed" in diff.summary


def test_diff_knowledge_history_reconstructs_the_full_retirement_story():
    lifecycle = sc.thesis_lifecycle_scenario(LIFECYCLE_START)
    for evaluation_date in lifecycle.evaluation_dates:
        lifecycle.monitor.evaluate(evaluation_date)
    diffs = diff_knowledge_history(lifecycle.knowledge_store, f"synthetic-{lifecycle.failing_ticker}")
    assert len(diffs) == 5  # PROMOTED->MONITORING, then 3x performance-record-only, then ->RETIRED
    assert any("RETIRED" in d.summary for d in diffs)


def test_diff_knowledge_revisions_rejects_different_entities():
    a = sc.thesis_lifecycle_scenario(LIFECYCLE_START)
    b = sc.thesis_lifecycle_scenario(LIFECYCLE_START)
    knowledge_a = a.knowledge_store.latest(f"synthetic-{a.failing_ticker}")
    knowledge_b = b.knowledge_store.latest(f"synthetic-{b.holding_ticker}")
    with pytest.raises(ValueError):
        diff_knowledge_revisions(knowledge_a, knowledge_b)


# --- checks.py --------------------------------------------------------------


def test_check_rejection_fails_if_zero_evidence_universe_ever_produced_a_recommendation():
    scenario = sc.synthetic_full_universe([f"T{i}" for i in range(20)], AS_OF)
    fake_nonempty_zero = sc.zero_evidence_universe(["X"], AS_OF)
    fake_nonempty_zero.recommendations = scenario.recommendations[:1]  # simulate a real violation
    result = checks.check_rejection(scenario, fake_nonempty_zero)
    assert result.verdict == CheckVerdict.FAIL


def test_check_hold_cash_passes_on_the_real_all_reject_scenario():
    scenario = sc.all_reject_universe([f"R{i}" for i in range(10)], AS_OF)
    result = checks.check_hold_cash(scenario)
    assert result.verdict == CheckVerdict.PASS


def test_check_complete_portfolio_passes_and_weights_never_exceed_one():
    scenario = sc.synthetic_full_universe([f"T{i}" for i in range(101)], AS_OF)
    result = checks.check_complete_portfolio(scenario)
    assert result.verdict == CheckVerdict.PASS


def test_check_benchmark_comparison_reports_blocked_without_real_egx30_coverage():
    result = checks.check_benchmark_comparison(AS_OF, AS_OF + timedelta(days=50), mock_root=None)
    assert result.verdict == CheckVerdict.BLOCKED


# --- runner.py: the full, repeatable report ----------------------------------


def test_full_report_covers_all_ten_questions_in_order():
    report = run_institutional_validation()
    assert isinstance(report, ValidationReport)
    assert [r.question_number for r in report.results] == list(range(1, 11))


def test_full_report_finds_no_genuine_defect_today():
    """The load-bearing regression test: if a future change to the decision
    engine, portfolio constructor, or continuous-learning monitor breaks
    one of the 10 properties outright, this turns FAIL and this test fails
    -- BLOCKED/PARTIAL (named, honest gaps) are expected and fine."""
    report = run_institutional_validation()
    failures = [r for r in report.results if r.verdict == CheckVerdict.FAIL]
    assert failures == [], f"Genuine defect(s) found: {[(r.question_number, r.findings) for r in failures]}"


def test_report_serializes_and_renders_markdown():
    report = run_institutional_validation()
    payload = report.model_dump(mode="json")
    assert payload["overall_verdict"] in {"pass", "partial", "blocked", "fail"}
    markdown = report.to_markdown()
    assert "# Institutional Investment Validation Report" in markdown
    assert "## 10." in markdown
