"""Tests for the Investment Proof Framework (`investment_proof/`) -- the
Mission 4 layer that composes `institutional_validation` plus decision
attribution, counterfactual ablation, committee validation, portfolio
validation, decision stability, thesis survival, confidence calibration and
walk-forward readiness into a final Capital Trust Report.

Every engine here is exercised with real platform code (real
`KnowledgeWeightedHorizonModel`/`MetaDecisionEngine`/`DecisionService`
calls), never a stubbed computation -- matching this codebase's existing
`test_institutional_validation.py` posture.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.decision_service.service import PositionAction, PositionAwareDecision
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability.explanation import Explanation
from agx_research.institutional_validation.report import CheckVerdict
from agx_research.investment_proof.attribution import DecisionAttributionEngine
from agx_research.investment_proof.calibration import ConfidenceCalibrationFramework
from agx_research.investment_proof.capital_trust import InvestmentProofEngine
from agx_research.investment_proof.categories import Category, category_for_agent
from agx_research.investment_proof.committee_validation import CommitteeValidationEngine
from agx_research.investment_proof.counterfactual import CounterfactualEngine
from agx_research.investment_proof.portfolio_validation import PortfolioValidationEngine
from agx_research.investment_proof.stability import DecisionStabilityEngine
from agx_research.investment_proof.thesis_survival import ThesisStatus, ThesisSurvivalEngine
from agx_research.investment_proof.walk_forward import WalkForwardInfrastructure
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_ledger import DecisionLedger
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.portfolio.constructor import PortfolioPosition
from agx_research.validation.statistical import StatisticalEvidence

AS_OF = date(2026, 6, 14)


def make_knowledge(
    id_: str,
    ticker: str,
    creator_agent: str,
    expected_return: float,
    *,
    confidence: float = 0.7,
    expected_risk: float = 0.05,
    horizon: Horizon = Horizon.INVESTMENT,
    discovery_date: date = date(2026, 5, 1),
) -> KnowledgeObject:
    return KnowledgeObject(
        id=id_,
        discovery_date=discovery_date,
        creator_agent=creator_agent,
        supporting_evidence=["test evidence"],
        confidence=confidence,
        statistical_evidence=StatisticalEvidence(method="t-test", statistic=2.5, p_value=0.01, sample_size=60),
        economic_explanation="test rationale",
        affected_assets=[ticker],
        horizon=horizon,
        expected_return=expected_return,
        expected_risk=expected_risk,
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


# --- categories.py -----------------------------------------------------------


def test_category_for_agent_maps_known_agents():
    assert category_for_agent("macro_agent") == Category.MACRO
    assert category_for_agent("financial_performance_agent") == Category.QUALITY


def test_category_for_agent_returns_none_for_unknown_agent():
    assert category_for_agent("not_a_real_agent") is None


# --- attribution.py ------------------------------------------------------------


def test_attribution_residual_is_near_zero_for_real_knowledge_weighted_prediction():
    knowledge = [
        make_knowledge("k1", "COMI", "macro_agent", 0.08),
        make_knowledge("k2", "COMI", "financial_performance_agent", 0.05),
    ]
    result = DecisionAttributionEngine().attribute("COMI", AS_OF, knowledge, reference_price=90.0)
    assert result.final_expected_return is not None
    assert result.attribution_residual == pytest.approx(0.0, abs=1e-6)
    categories = {c.category for c in result.return_contributions}
    assert Category.MACRO in categories
    assert Category.QUALITY in categories


def test_attribution_returns_empty_result_for_no_evidence():
    result = DecisionAttributionEngine().attribute("NOEVIDENCE", AS_OF, [], reference_price=50.0)
    assert result.final_expected_return is None
    assert result.return_contributions == []


def test_attribution_reports_unattributed_knowledge_from_an_unmapped_agent():
    knowledge = [make_knowledge("k1", "COMI", "some_unmapped_agent", 0.08)]
    result = DecisionAttributionEngine().attribute("COMI", AS_OF, knowledge)
    assert result.unattributed_knowledge_ids == ["k1"]
    assert result.return_contributions == []


# --- counterfactual.py ---------------------------------------------------------


def test_counterfactual_identifies_the_decisive_category():
    knowledge = [
        make_knowledge("k1", "COMI", "macro_agent", 0.20, confidence=0.9),
        make_knowledge("k2", "COMI", "financial_performance_agent", 0.02, confidence=0.5),
    ]
    result = CounterfactualEngine().analyze("COMI", AS_OF, knowledge, reference_price=90.0)
    assert result.baseline_action is not None
    assert Category.MACRO in result.decisive_categories


def test_counterfactual_handles_no_evidence_honestly():
    result = CounterfactualEngine().analyze("NOEVIDENCE", AS_OF, [])
    assert result.baseline_action is None
    assert result.scenarios == []
    assert result.decisive_categories == []


# --- committee_validation.py ---------------------------------------------------


def test_committee_validation_aggregates_agreement_across_tickers():
    knowledge_by_ticker = {
        "COMI": [
            make_knowledge("k1", "COMI", "macro_agent", 0.08),
            make_knowledge("k2", "COMI", "financial_performance_agent", 0.05),
        ],
        "HRHO": [
            make_knowledge("k3", "HRHO", "macro_agent", -0.03),
            make_knowledge("k4", "HRHO", "corporate_events_agent", 0.06),
        ],
    }
    result = CommitteeValidationEngine().validate(
        ["COMI", "HRHO"], AS_OF, knowledge_by_ticker, latest_prices={"COMI": 90.0, "HRHO": 20.0}
    )
    assert result.tickers_evaluated == 2
    macro = next(c for c in result.committees if c.category == Category.MACRO)
    assert macro.tickers_present == 2
    assert macro.historical_usefulness_status == "ready_for_data"


def test_committee_validation_skips_tickers_with_no_knowledge():
    result = CommitteeValidationEngine().validate(["EMPTY"], AS_OF, {}, latest_prices={})
    assert result.tickers_evaluated == 0


# --- stability.py ---------------------------------------------------------------


def test_recommendation_stability_is_identical_across_runs():
    store = KnowledgeStore()
    for i in range(5):
        store._repo.add(make_knowledge(f"k{i}", f"T{i}", "macro_agent", 0.05 + i / 100))
    tickers = [f"T{i}" for i in range(5)]
    result = DecisionStabilityEngine().verify_recommendation_stability(store, tickers, AS_OF, runs=3)
    assert result.identical is True
    assert result.differences == []


# --- calibration.py --------------------------------------------------------------


def test_calibration_report_is_honestly_insufficient_with_no_ledger_records():
    ledger = DecisionLedger()
    report = ConfidenceCalibrationFramework(ledger).calibration_report(Horizon.INVESTMENT)
    assert report.sample_status == "insufficient"
    assert report.brier_score is None
    assert report.expected_calibration_error is None


# --- walk_forward.py --------------------------------------------------------------


def test_walk_forward_replay_records_recommendations_across_real_trading_days():
    store = KnowledgeStore()
    tickers = ["COMI", "HRHO"]
    for ticker in tickers:
        store._repo.add(make_knowledge(f"k-{ticker}", ticker, "macro_agent", 0.06))

    ledger = DecisionLedger()
    infra = WalkForwardInfrastructure(lambda _as_of: RecommendationService(store), ledger)
    report = infra.run_replay(date(2026, 6, 1), date(2026, 6, 10), tickers)

    assert report.trading_days_replayed > 0
    assert report.errors == []
    assert report.recommendations_recorded == report.trading_days_replayed * len(tickers)


def test_walk_forward_required_datasets_are_ready_for_data_with_no_real_history():
    datasets = WalkForwardInfrastructure.required_datasets()
    assert all(d.status == "ready_for_data" for d in datasets)
    assert {d.name for d in datasets} == {
        "multi_year_real_egx_price_history",
        "real_egx30_index_level_price_series",
        "daily_promoted_knowledge_snapshots",
    }


# --- portfolio_validation.py -----------------------------------------------------


def test_portfolio_validation_flags_concentration_and_reconciles_weights():
    positions = [
        PortfolioPosition(ticker="A", weight=0.5, score=1.0, expected_return=0.1, expected_risk=0.05, confidence=0.8),
        PortfolioPosition(ticker="B", weight=0.1, score=0.5, expected_return=0.05, expected_risk=0.04, confidence=0.7),
    ]
    result = PortfolioValidationEngine().validate(positions, cash_weight=0.4, as_of=AS_OF)
    assert result.weights_reconcile is True
    assert result.concentration.status == "concentrated"  # herfindahl 0.5^2+0.1^2=0.26 > 0.25
    assert result.concentration.max_position_ticker == "A"


def test_portfolio_validation_reports_weight_mismatch_as_unreconciled():
    positions = [
        PortfolioPosition(ticker="A", weight=0.5, score=1.0, expected_return=0.1, expected_risk=0.05, confidence=0.8),
    ]
    result = PortfolioValidationEngine().validate(positions, cash_weight=0.1, as_of=AS_OF)
    assert result.weights_reconcile is False


# --- thesis_survival.py -----------------------------------------------------------


def _make_position_decision(
    ticker: str,
    action: PositionAction,
    contradicting: list[str],
    catalysts: list[str],
    review_date: date | None,
    knowledge_id: str | None = "k-thesis-1",
) -> PositionAwareDecision:
    return PositionAwareDecision(
        ticker=ticker,
        as_of=date(2026, 6, 1),
        action=action,
        target_weight=0.1,
        current_weight=0.0,
        horizon=Horizon.INVESTMENT,
        confidence=0.7,
        investment_thesis="Test thesis",
        key_risks=["test risk"],
        contradicting_evidence=contradicting,
        active_catalysts=catalysts,
        monitoring_events=[],
        expected_review_date=review_date,
        abstained=False,
        reasons=[],
        explanation=Explanation(
            why_this_stock="test",
            why_now="test",
            why_not_others="test",
            evidence_refs=[ProvenanceRef(kind="knowledge", ref_id=knowledge_id)] if knowledge_id else [],
        ),
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


def test_thesis_survival_alive_when_nothing_changed():
    store = KnowledgeStore()
    store._repo.add(make_knowledge("k-thesis-1", "COMI", "macro_agent", 0.08))
    original = _make_position_decision(
        "COMI", PositionAction.BUY, [], ["catalyst_a"], date(2026, 7, 1)
    )
    current = _make_position_decision(
        "COMI", PositionAction.BUY, [], ["catalyst_a"], date(2026, 8, 1)
    )
    report = ThesisSurvivalEngine().assess(original, current, store, as_of=date(2026, 6, 15))
    assert report.status == ThesisStatus.ALIVE
    assert report.broken_assumptions == []


def test_thesis_survival_broken_when_supporting_knowledge_retires_and_action_exits():
    store = KnowledgeStore()
    store._repo.add(make_knowledge("k-thesis-1", "COMI", "macro_agent", 0.08))
    store.transition_status("k-thesis-1", KnowledgeStatus.RETIRED, reason="realized return disagreed")
    original = _make_position_decision("COMI", PositionAction.BUY, [], [], date(2026, 7, 1))
    current = _make_position_decision("COMI", PositionAction.EXIT, ["thesis invalidated"], [], date(2026, 8, 1))
    report = ThesisSurvivalEngine().assess(original, current, store, as_of=date(2026, 7, 15))
    assert report.status == ThesisStatus.BROKEN
    assert report.broken_assumptions[0].knowledge_id == "k-thesis-1"
    assert report.review_date_passed is True


def test_thesis_survival_expired_when_no_current_decision_exists():
    store = KnowledgeStore()
    store._repo.add(make_knowledge("k-thesis-1", "COMI", "macro_agent", 0.08))
    original = _make_position_decision("COMI", PositionAction.BUY, [], [], date(2026, 7, 1))
    report = ThesisSurvivalEngine().assess(original, None, store, as_of=date(2026, 9, 1))
    assert report.status == ThesisStatus.EXPIRED
    assert report.days_elapsed == (date(2026, 9, 1) - date(2026, 6, 1)).days


# --- capital_trust.py: the full orchestrator -------------------------------------


def test_investment_proof_engine_produces_a_report_with_no_genuine_fail():
    report = InvestmentProofEngine().run(AS_OF, ticker_limit=6)
    failures = [d for d in report.dimensions if d.verdict == CheckVerdict.FAIL]
    assert failures == [], f"Genuine defect(s) found: {[(d.name, d.findings) for d in failures]}"
    assert report.overall_verdict in {"yes", "no", "partially"}


def test_investment_proof_engine_dimensions_cover_every_named_phase():
    report = InvestmentProofEngine().run(AS_OF, ticker_limit=6)
    names = {d.name for d in report.dimensions}
    assert names == {
        "decision_stability",
        "decision_attribution",
        "counterfactual_analysis",
        "committee_validation",
        "portfolio_validation",
        "thesis_survival",
        "confidence_calibration",
        "walk_forward_backtest",
    }


def test_investment_proof_engine_report_serializes_and_renders_markdown():
    report = InvestmentProofEngine().run(AS_OF, ticker_limit=6)
    payload = report.model_dump(mode="json")
    assert payload["overall_verdict"] in {"yes", "no", "partially"}
    markdown = report.to_markdown()
    assert "# Capital Trust Report" in markdown
    assert "## decision_stability" in markdown


def test_investment_proof_engine_overall_verdict_is_partially_pending_real_data():
    """Regression guard for this framework's own core honesty claim: with
    no real EGX history and no real DecisionLedger track record yet, the
    overall verdict must never silently claim full (YES) trust."""
    report = InvestmentProofEngine().run(AS_OF, ticker_limit=6)
    assert report.overall_verdict != "yes"
