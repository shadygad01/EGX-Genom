"""Tests for the CIO Desk dashboard artifacts (Portfolio Summary,
Monitoring Warnings, Investment Committee Summary) -- the backend layer
behind the Institutional Investment Operating System mission's "what
should I do today" home screen. Each engine is exercised with real
platform code (real `KnowledgeStore`/`PortfolioConstructor`/
`RecommendationService`/`investment_proof` calls), matching this
codebase's existing test posture.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from agx_research.config import Horizon
from agx_research.dashboard.committee_summary import build_committee_summary
from agx_research.dashboard.monitoring import WarningCategory, build_warnings
from agx_research.dashboard.portfolio_summary import build_portfolio_summary
from agx_research.data.schemas import CorporateEvent
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.domain.provenance import Provenance
from agx_research.explainability import Explanation
from agx_research.investment_proof.portfolio_validation import PortfolioValidationEngine
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_quality import apply_decision_quality_gate
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.portfolio.constructor import PortfolioConstructor, PortfolioPosition, PortfolioRecommendation
from agx_research.validation.statistical import StatisticalEvidence

AS_OF = date(2026, 6, 14)


def make_knowledge(id_: str, ticker: str, creator_agent: str, expected_return: float, **kwargs) -> KnowledgeObject:
    return KnowledgeObject(
        id=id_,
        discovery_date=date(2026, 5, 1),
        creator_agent=creator_agent,
        supporting_evidence=["test evidence"],
        confidence=kwargs.get("confidence", 0.7),
        statistical_evidence=StatisticalEvidence(method="t-test", statistic=2.5, p_value=0.01, sample_size=60),
        economic_explanation="test rationale",
        affected_assets=[ticker],
        horizon=Horizon.INVESTMENT,
        expected_return=expected_return,
        expected_risk=kwargs.get("expected_risk", 0.05),
        status=kwargs.get("status", KnowledgeStatus.PROMOTED),
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )


# --- portfolio_summary.py -----------------------------------------------------


def test_portfolio_summary_computes_weighted_expected_return():
    positions = [
        PortfolioPosition(ticker="A", weight=0.5, score=1.0, expected_return=0.10, expected_risk=0.05, confidence=0.8),
        PortfolioPosition(ticker="B", weight=0.1, score=0.5, expected_return=0.02, expected_risk=0.04, confidence=0.7),
    ]
    portfolio = PortfolioRecommendation(
        id="p1",
        as_of=AS_OF,
        positions=positions,
        cash_weight=0.4,
        explanation=Explanation(why_this_stock="x", why_now="x", why_not_others="x"),
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )
    report = build_portfolio_summary(portfolio, AS_OF)
    assert report.is_live_portfolio is False
    assert report.position_count == 2
    assert report.expected_return == pytest.approx((0.5 * 0.10 + 0.1 * 0.02) / 0.6)
    assert report.expected_risk == pytest.approx((0.5 * 0.05 + 0.1 * 0.04) / 0.6)
    assert report.weights_reconcile is True


def test_portfolio_summary_handles_all_cash():
    portfolio = PortfolioRecommendation(
        id="p1",
        as_of=AS_OF,
        positions=[],
        cash_weight=1.0,
        explanation=Explanation(why_this_stock="x", why_now="x", why_not_others="x"),
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )
    report = build_portfolio_summary(portfolio, AS_OF)
    assert report.expected_return is None
    assert report.position_count == 0


# --- monitoring.py -------------------------------------------------------------


def test_build_warnings_detects_macro_risk_broken_thesis_catalyst_and_review():
    store = KnowledgeStore()
    store._repo.add(make_knowledge("k-comi", "COMI", "macro_agent", 0.08))
    store._repo.add(make_knowledge("k-hrho", "HRHO", "macro_agent", 0.08))
    store.transition_status("k-hrho", KnowledgeStatus.RETIRED, reason="realized return disagreed")
    retired = store.latest("k-hrho")
    retired.retired_at = AS_OF
    store._repo.add(retired)

    recs = RecommendationService(store).recommend(["COMI"], AS_OF, latest_prices={"COMI": 90.0})
    recs = apply_decision_quality_gate(recs)
    portfolio = PortfolioConstructor().construct(recs, AS_OF)
    assert portfolio.positions, "expected COMI to be a real, funded position"

    corporate_events = {
        "COMI": [CorporateEvent(ticker="COMI", event_date=AS_OF - timedelta(days=2), event_type="earnings", description="Q2 earnings")]
    }
    country_risk = CountryRiskAssessment(as_of=AS_OF, severity=CountryRiskSeverity.DETERIORATING, reasons=["EGP moved 6%"])
    pv = PortfolioValidationEngine().validate(portfolio.positions, portfolio.cash_weight, AS_OF)

    report = build_warnings(
        as_of=AS_OF,
        portfolio=portfolio,
        recommendations=recs,
        knowledge_store=store,
        corporate_events=corporate_events,
        country_risk=country_risk,
        illiquid_tickers=set(),
        portfolio_validation=pv,
    )
    categories = {w.category for w in report.warnings}
    assert WarningCategory.MACRO_RISK_INCREASED in categories
    assert WarningCategory.BROKEN_THESIS in categories
    assert WarningCategory.CATALYST_EXPIRED in categories
    broken = next(w for w in report.warnings if w.category == WarningCategory.BROKEN_THESIS)
    assert broken.ticker == "HRHO"


def test_build_warnings_empty_when_nothing_is_wrong():
    store = KnowledgeStore()
    store._repo.add(make_knowledge("k-comi", "COMI", "macro_agent", 0.08))
    recs = RecommendationService(store).recommend(["COMI"], AS_OF, latest_prices={"COMI": 90.0})
    recs = apply_decision_quality_gate(recs)
    portfolio = PortfolioConstructor().construct(recs, AS_OF)
    country_risk = CountryRiskAssessment(as_of=AS_OF, severity=CountryRiskSeverity.NORMAL)
    pv = PortfolioValidationEngine().validate(portfolio.positions, portfolio.cash_weight, AS_OF)

    report = build_warnings(
        as_of=AS_OF,
        portfolio=portfolio,
        recommendations=recs,
        knowledge_store=store,
        corporate_events={},
        country_risk=country_risk,
        illiquid_tickers=set(),
        portfolio_validation=pv,
    )
    assert report.warnings == []


def test_build_warnings_flags_liquidity_and_concentration():
    positions = [
        PortfolioPosition(ticker="A", weight=0.5, score=1.0, expected_return=0.1, expected_risk=0.05, confidence=0.8),
        PortfolioPosition(ticker="B", weight=0.1, score=0.5, expected_return=0.05, expected_risk=0.04, confidence=0.7),
    ]
    portfolio = PortfolioRecommendation(
        id="p1", as_of=AS_OF, positions=positions, cash_weight=0.4,
        explanation=Explanation(why_this_stock="x", why_now="x", why_not_others="x"),
        provenance=Provenance(produced_by="test", produced_at=datetime.now()),
    )
    store = KnowledgeStore()
    country_risk = CountryRiskAssessment(as_of=AS_OF, severity=CountryRiskSeverity.NORMAL)
    pv = PortfolioValidationEngine().validate(positions, portfolio.cash_weight, AS_OF)
    report = build_warnings(
        as_of=AS_OF, portfolio=portfolio, recommendations=[], knowledge_store=store,
        corporate_events={}, country_risk=country_risk, illiquid_tickers={"A"}, portfolio_validation=pv,
    )
    categories = {w.category for w in report.warnings}
    assert WarningCategory.LIQUIDITY_DETERIORATION in categories
    assert WarningCategory.PORTFOLIO_CONCENTRATION in categories


# --- committee_summary.py -------------------------------------------------------


def test_committee_summary_includes_risk_portfolio_and_cio_rows():
    knowledge_by_ticker = {
        "COMI": [make_knowledge("k1", "COMI", "macro_agent", 0.08), make_knowledge("k2", "COMI", "financial_performance_agent", 0.05)],
    }
    positions = [PortfolioPosition(ticker="COMI", weight=0.5, score=1.0, expected_return=0.08, expected_risk=0.05, confidence=0.8)]
    pv = PortfolioValidationEngine().validate(positions, 0.5, AS_OF)
    report = build_committee_summary(
        AS_OF, ["COMI"], knowledge_by_ticker, latest_prices={"COMI": 90.0}, portfolio_validation=pv
    )
    committees = {o.committee for o in report.opinions}
    assert {"macro", "quality", "risk", "portfolio", "chief_investment_officer"} <= committees
    cio = next(o for o in report.opinions if o.committee == "chief_investment_officer")
    assert cio.stance in {"aligned", "mixed", "diverging", "no_data"}


def test_committee_summary_no_data_when_no_knowledge():
    report = build_committee_summary(AS_OF, ["EMPTY"], {}, latest_prices={})
    macro = next(o for o in report.opinions if o.committee == "macro")
    assert macro.stance == "no_data"
    assert report.tickers_evaluated == 0
