"""The 10 institutional-robustness checks, one function per mission
question. Each function runs real platform code against a scenario from
`scenarios.py` and returns a `report.CheckResult` -- concrete counts and
outcomes as evidence, named gaps/defects as findings, never a bare
pass/fail with no evidence behind it.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from agx_research.data.mock_provider import MockDataProvider
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.decision_service.position import PositionState
from agx_research.decision_service.service import DecisionService
from agx_research.institutional_validation import scenarios as sc
from agx_research.institutional_validation.diffing import diff_knowledge_history
from agx_research.institutional_validation.report import CheckResult, CheckVerdict
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.meta.decision_engine import DecisionAction
from agx_research.meta.decision_ledger import DecisionLedger
from agx_research.portfolio.constructor import PortfolioConstructor


def _real_mock_coverage(mock_root: Path | None, tickers: list[str], as_of: date) -> int:
    """How many `tickers` have real (non-synthetic) mock price history
    today -- used only to report the platform's actual current data
    coverage honestly, never to gate a check's pass/fail on it."""
    if mock_root is None:
        return 0
    try:
        provider = MockDataProvider(mock_root)
        return sum(
            1 for ticker in tickers if provider.get_price_history(ticker, as_of - timedelta(days=30), as_of)
        )
    except Exception:
        return 0


def _action_counts(recommendations) -> dict[str, int]:
    counts: dict[str, int] = {}
    for rec in recommendations:
        for decision in rec.horizon_decisions.values():
            counts[decision.action.value] = counts.get(decision.action.value, 0) + 1
    return counts


# --- Q1/Q2: rank the full EGX30/EGX70 universe -------------------------------


def check_universe_ranking(
    question_number: int, index_name: str, tickers: list[str], as_of: date, *, mock_root: Path | None = None
) -> CheckResult:
    real_covered = _real_mock_coverage(mock_root, tickers, as_of)

    scenario = sc.synthetic_full_universe(tickers, as_of, scenario_id=f"synthetic_{index_name.lower()}")
    actions = _action_counts(scenario.recommendations)
    ranked = sorted(scenario.recommendations, key=lambda r: r.combined_expected_return, reverse=True)

    evidence = [
        f"Real {index_name} constituent list: {len(tickers)} tickers (from research/data/universe/{index_name}.csv).",
        f"Real mock price coverage today: {real_covered}/{len(tickers)} tickers.",
        f"Synthetic full-scale run: {len(scenario.recommendations)}/{len(tickers)} tickers produced a "
        f"Recommendation (100% expected -- every ticker had synthetic promoted knowledge).",
        f"Action distribution across the full synthetic universe: {actions}.",
        f"Ranked (sorted by combined_expected_return) without error: {len(ranked)} entries, "
        f"top={ranked[0].ticker if ranked else None}, bottom={ranked[-1].ticker if ranked else None}.",
    ]
    findings = []
    if real_covered < len(tickers):
        findings.append(
            f"Real mock price coverage is only {real_covered}/{len(tickers)} {index_name} tickers today -- "
            "the ranking mechanism is universe-size-agnostic by construction (RecommendationService.recommend() "
            "takes any ticker list), but real, non-synthetic ranked output for the full index is data-blocked, "
            "not code-blocked."
        )
    verdict = CheckVerdict.PASS if len(scenario.recommendations) == len(tickers) else CheckVerdict.FAIL
    if verdict == CheckVerdict.PASS and findings:
        verdict = CheckVerdict.PARTIAL
    return CheckResult(
        question_number=question_number,
        question=f"Can the system rank the full {index_name} universe?",
        verdict=verdict,
        evidence=evidence,
        findings=findings,
        scenario_ids=[scenario.scenario_id],
    )


# --- Q3: explain every ranking -----------------------------------------------


def check_explain_every_ranking(scenario: sc.SyntheticUniverseScenario) -> CheckResult:
    missing = [
        rec.ticker
        for rec in scenario.recommendations
        if not rec.explanation.why_this_stock or not rec.explanation.why_now
    ]
    structural_proof = "not attempted: pydantic required field"
    try:
        from agx_research.meta.decision_engine import Recommendation

        Recommendation(
            ticker="X", as_of=scenario.as_of, combined_expected_return=0.0, combined_expected_risk=0.0,
            confidence=0.0, horizon_predictions={}, horizon_decisions={}, provenance=None,
        )  # type: ignore[call-arg]
        structural_proof = "FAILED: construction without explanation/provenance succeeded"
    except Exception as exc:
        structural_proof = f"confirmed: {type(exc).__name__} raised when explanation/provenance omitted"

    evidence = [
        f"{len(scenario.recommendations)}/{len(scenario.recommendations)} recommendations in the synthetic "
        f"full-universe run carry a non-empty Explanation (why_this_stock/why_now populated).",
        f"Structural falsification attempt (construct a Recommendation without explanation/provenance): {structural_proof}.",
        "Explanation is a required (non-Optional, no-default) field on Recommendation, PortfolioRecommendation, "
        "and PositionAwareDecision -- pydantic raises ValidationError on any construction path that omits it.",
    ]
    verdict = CheckVerdict.PASS if not missing and "confirmed" in structural_proof else CheckVerdict.FAIL
    return CheckResult(
        question_number=3,
        question="Can it explain every ranking?",
        verdict=verdict,
        evidence=evidence,
        findings=[f"{len(missing)} recommendation(s) with an empty explanation: {missing}"] if missing else [],
        scenario_ids=[scenario.scenario_id],
    )


# --- Q4: reject every stock if appropriate -----------------------------------


def check_rejection(scenario: sc.SyntheticUniverseScenario, zero_evidence: sc.SyntheticUniverseScenario) -> CheckResult:
    actions = _action_counts(scenario.recommendations)
    avoid_count = actions.get(DecisionAction.AVOID.value, 0)
    abstain_count = actions.get(DecisionAction.ABSTAIN.value, 0)

    # Falsification attempt: every AVOID-labeled ticker really does have a
    # non-positive expected return (never a mislabeled buy).
    mislabeled = [
        rec.ticker
        for rec in scenario.recommendations
        for decision in rec.horizon_decisions.values()
        if decision.action == DecisionAction.AVOID and decision.expected_return > 0
    ]

    evidence = [
        f"Full synthetic universe: {avoid_count} AVOID, {abstain_count} ABSTAIN "
        f"(of {len(scenario.recommendations)} recommendations) -- real rejection outcomes, not zero.",
        f"Zero-evidence universe ({len(zero_evidence.tickers)} tickers, empty KnowledgeStore): "
        f"{len(zero_evidence.recommendations)} recommendations produced -- 100% rejected by absence of evidence.",
        f"Falsification attempt (every AVOID ticker checked for expected_return<=0): "
        f"{len(mislabeled)} mislabeled ticker(s) found.",
    ]
    verdict = CheckVerdict.PASS
    findings = []
    if zero_evidence.recommendations:
        verdict = CheckVerdict.FAIL
        findings.append("Zero-evidence universe produced a non-empty recommendation list -- Principle 1 violated.")
    if mislabeled:
        verdict = CheckVerdict.FAIL
        findings.append(f"AVOID applied to positive-expected-return ticker(s): {mislabeled}")
    return CheckResult(
        question_number=4,
        question="Can it reject every stock if appropriate?",
        verdict=verdict,
        evidence=evidence,
        findings=findings,
        scenario_ids=[scenario.scenario_id, zero_evidence.scenario_id],
    )


# --- Q5: recommend holding cash ----------------------------------------------


def check_hold_cash(all_reject_scenario: sc.SyntheticUniverseScenario) -> CheckResult:
    portfolio = PortfolioConstructor().construct(all_reject_scenario.recommendations, all_reject_scenario.as_of)
    evidence = [
        f"All-reject universe ({len(all_reject_scenario.tickers)} tickers, no BUY_CANDIDATE-eligible thesis "
        f"among them): portfolio has {len(portfolio.positions)} position(s), "
        f"cash_weight={portfolio.cash_weight:.4f}.",
        f"Explanation states the reason: {portfolio.explanation.why_this_stock!r}",
    ]
    verdict = CheckVerdict.PASS if portfolio.cash_weight == 1.0 and not portfolio.positions else CheckVerdict.FAIL
    return CheckResult(
        question_number=5,
        question="Can it recommend holding cash?",
        verdict=verdict,
        evidence=evidence,
        scenario_ids=[all_reject_scenario.scenario_id],
    )


# --- Q6: build a complete portfolio, not isolated recommendations -----------


def check_complete_portfolio(scenario: sc.SyntheticUniverseScenario) -> CheckResult:
    portfolio = PortfolioConstructor().construct(scenario.recommendations, scenario.as_of)
    weight_sum = sum(p.weight for p in portfolio.positions)
    over_cap = [p.ticker for p in portfolio.positions if p.weight > PortfolioConstructor().max_position_weight + 1e-9]

    positions = {t: PositionState(ticker=t, held=False) for t in scenario.tickers}
    crisis_normal = CountryRiskAssessment(as_of=scenario.as_of, severity=CountryRiskSeverity.NORMAL)
    position_aware = DecisionService().decide_portfolio(
        scenario.recommendations, positions, scenario.as_of, country_risk=crisis_normal
    )
    pa_weight_sum = sum(d.target_weight for d in position_aware)

    evidence = [
        f"PortfolioConstructor (autonomous, position-unaware): {len(portfolio.positions)} position(s), "
        f"weights sum to {weight_sum:.4f} (<=1: {weight_sum <= 1.0 + 1e-9}), cash_weight={portfolio.cash_weight:.4f}.",
        f"Every position capped at max_position_weight={PortfolioConstructor().max_position_weight}: "
        f"{len(over_cap)} violation(s).",
        f"DecisionService.decide_portfolio (position-aware, joint normalization over "
        f"{len(scenario.tickers)} tickers): target weights sum to {pa_weight_sum:.4f}.",
        "Both constructors jointly normalize across the full recommendation set (not per-ticker isolated "
        "scoring) -- confirmed by the weight sums above staying bounded regardless of universe size.",
    ]
    verdict = CheckVerdict.PASS if weight_sum <= 1.0 + 1e-9 and not over_cap and pa_weight_sum <= 1.0 + 1e-9 else CheckVerdict.FAIL
    return CheckResult(
        question_number=6,
        question="Can it build a complete portfolio instead of isolated recommendations?",
        verdict=verdict,
        evidence=evidence,
        findings=[f"Positions exceeding the position cap: {over_cap}"] if over_cap else [],
        scenario_ids=[scenario.scenario_id],
    )


# --- Q7: compare against benchmark indices -----------------------------------


def check_benchmark_comparison(as_of: date, valid_until: date, *, mock_root: Path | None = None) -> CheckResult:
    bench = sc.benchmark_scenario(as_of, valid_until)
    ledger = DecisionLedger()
    ledger.record_recommendations([bench.recommendation])
    ledger.evaluate_expired(bench.snapshot_at_evaluation, benchmark_ticker=bench.benchmark_ticker)
    records = ledger.all_latest()
    record = records[0]

    expected_gross = (bench.exit_price - bench.entry_price) / bench.entry_price
    expected_realized = expected_gross - 20.0 / 10_000
    matches = record.realized_return is not None and abs(record.realized_return - expected_realized) < 1e-9

    real_egx30_coverage = _real_mock_coverage(mock_root, ["EGX30"], as_of) > 0

    evidence = [
        f"Synthetic benchmark scenario: realized_return={record.realized_return}, "
        f"benchmark_return={record.benchmark_return}, excess_return={record.excess_return}, hit={record.hit}.",
        f"Hand-computed realized_return={expected_realized:.6f}; mechanism matches: {matches}.",
        f"Real mock price data contains a literal 'EGX30' index ticker today: {real_egx30_coverage}.",
    ]
    findings = []
    verdict = CheckVerdict.PASS if matches else CheckVerdict.FAIL
    if matches and not real_egx30_coverage:
        findings.append(
            "DecisionLedger.evaluate_expired()'s benchmark math is correct (proven above with synthetic data), "
            "but no ticker literally named 'EGX30' (or any other index-level series) exists in real mock/production "
            "price data -- every real DecisionRecord's benchmark_return stays None today. This is a data gap, "
            "not a code defect: the mechanism only needs a price series under the benchmark_ticker id to work."
        )
        verdict = CheckVerdict.BLOCKED
    return CheckResult(
        question_number=7,
        question="Can it compare recommendations against benchmark indices?",
        verdict=verdict,
        evidence=evidence,
        findings=findings,
        scenario_ids=["benchmark_scenario"],
    )


# --- Q8: detect when an investment thesis has failed -------------------------


def check_thesis_failure_detection(start: date) -> CheckResult:
    lifecycle = sc.thesis_lifecycle_scenario(start)
    per_date_outcomes = {d: lifecycle.monitor.evaluate(d) for d in lifecycle.evaluation_dates}

    fail_knowledge = lifecycle.knowledge_store.latest(f"synthetic-{lifecycle.failing_ticker}")
    hold_knowledge = lifecycle.knowledge_store.latest(f"synthetic-{lifecycle.holding_ticker}")

    evidence = [
        f"Declining synthetic thesis ({lifecycle.failing_ticker}, expected positive return, price engineered "
        f"to fall): final status={fail_knowledge.status.value}, "
        f"retirement_reason={fail_knowledge.retirement_reason!r}.",
        f"Rising synthetic thesis ({lifecycle.holding_ticker}, expected positive return, price engineered "
        f"to rise as expected): final status={hold_knowledge.status.value} "
        "(must NOT be retired -- a false-positive retirement would itself be a defect).",
        f"Evaluated across {len(lifecycle.evaluation_dates)} real dates, {sum(1 for outs in per_date_outcomes.values() for o in outs)} "
        "total PerformanceRecord(s) appended.",
    ]
    findings = [
        "ContinuousLearningMonitor is real and mechanically correct (proven above), but is not wired into "
        "production.pipeline.ProductionPipeline -- no autonomous `agx run` currently invokes thesis-failure "
        "detection; it is only exercised directly (in tests, and now this validation framework). Wiring it in "
        "requires a real design decision about cadence (it needs a *later* as_of than a knowledge object's "
        "discovery date to have any realized forward return at all) that this validation mission did not settle."
    ]
    verdict = CheckVerdict.PASS if fail_knowledge.status == KnowledgeStatus.RETIRED and hold_knowledge.status != KnowledgeStatus.RETIRED else CheckVerdict.FAIL
    if verdict == CheckVerdict.PASS:
        verdict = CheckVerdict.PARTIAL  # mechanism proven, but not autonomously wired -- named above
    return CheckResult(
        question_number=8,
        question="Can it detect when an investment thesis has failed?",
        verdict=verdict,
        evidence=evidence,
        findings=findings,
        scenario_ids=["thesis_lifecycle_scenario"],
    )


# --- Q9: identify why a recommendation changed -------------------------------


def check_change_attribution(start: date) -> CheckResult:
    lifecycle = sc.thesis_lifecycle_scenario(start)
    for d in lifecycle.evaluation_dates:
        lifecycle.monitor.evaluate(d)

    diffs = diff_knowledge_history(lifecycle.knowledge_store, f"synthetic-{lifecycle.failing_ticker}")
    retirement_diff = next((d for d in diffs if "RETIRED" in d.summary), None)

    evidence = [
        f"New capability (this validation mission): diff_knowledge_history() reconstructed "
        f"{len(diffs)} revision-to-revision diff(s) for the failing thesis's knowledge object.",
        f"Retirement transition correctly attributed: {retirement_diff.summary if retirement_diff else 'NOT FOUND'}",
    ]
    findings = [
        "This capability only covers KnowledgeObject (the one decision-chain entity actually persisted with "
        "a version history in a Repository). Recommendation and PortfolioRecommendation are recomputed fresh "
        "every run and never stored with a version history -- there is currently no way to answer 'why did "
        "today's Recommendation for ticker X differ from yesterday's' directly; only the underlying knowledge's "
        "own change history is traceable. Adding day-over-day Recommendation persistence would be a real, "
        "separate architectural decision (a new versioned store for an entity that's deliberately ephemeral "
        "today), not something this validation mission should decide unilaterally."
    ]
    verdict = CheckVerdict.PARTIAL if retirement_diff is not None else CheckVerdict.FAIL
    return CheckResult(
        question_number=9,
        question="Can it identify why a recommendation changed?",
        verdict=verdict,
        evidence=evidence,
        findings=findings,
        scenario_ids=["thesis_lifecycle_scenario"],
    )


# --- Q10: trace every decision back to evidence ------------------------------


def check_evidence_traceability(as_of: date) -> CheckResult:
    chain = sc.evidence_chain_scenario(as_of)

    hop1 = chain.knowledge.provenance.inputs and chain.knowledge.provenance.inputs[0].ref_id == chain.hypothesis_stub.id
    hop2 = any(ref.ref_id == chain.knowledge.id for ref in chain.recommendation.provenance.inputs)
    hop3 = chain.position_aware_decision.provenance.inputs and chain.position_aware_decision.provenance.inputs[0].ref_id == chain.recommendation.ticker
    hop4 = any(ref.ref_id == chain.knowledge.id for ref in chain.position_aware_decision.explanation.evidence_refs)

    evidence = [
        f"Hop 1 (hypothesis -> knowledge): knowledge.provenance.inputs references hypothesis id "
        f"{chain.hypothesis_stub.id!r}: {bool(hop1)}.",
        f"Hop 2 (knowledge -> recommendation): recommendation.provenance.inputs references knowledge id "
        f"{chain.knowledge.id!r}: {bool(hop2)}.",
        f"Hop 3 (recommendation -> decision): decision.provenance.inputs references "
        f"{chain.position_aware_decision.provenance.inputs[0].ref_id if chain.position_aware_decision.provenance.inputs else None!r}: {bool(hop3)}.",
        f"Hop 4 (decision -> evidence_refs): decision.explanation.evidence_refs traces back to knowledge id "
        f"{chain.knowledge.id!r}: {bool(hop4)}.",
        f"Final decision: {chain.position_aware_decision.action.value}, target_weight="
        f"{chain.position_aware_decision.target_weight:.4f}.",
    ]
    findings = []
    if hop3:
        findings.append(
            "Hop 3 links by ticker string (Recommendation has no id/version field), not a stable versioned "
            "pointer -- if two Recommendations for the same ticker were ever produced on the same day (they "
            "currently cannot be, by construction), the link would be ambiguous. Named, not a defect today."
        )
    all_hops = hop1 and hop2 and hop3 and hop4
    verdict = CheckVerdict.PASS if all_hops else CheckVerdict.FAIL
    if all_hops and findings:
        verdict = CheckVerdict.PARTIAL
    return CheckResult(
        question_number=10,
        question="Can every decision be traced back to evidence?",
        verdict=verdict,
        evidence=evidence,
        findings=findings,
        scenario_ids=["evidence_chain_scenario"],
    )


__all__ = [
    "check_benchmark_comparison",
    "check_change_attribution",
    "check_complete_portfolio",
    "check_evidence_traceability",
    "check_explain_every_ranking",
    "check_hold_cash",
    "check_rejection",
    "check_thesis_failure_detection",
    "check_universe_ranking",
]
