from datetime import date, datetime

import pytest

from agx_research.config import Horizon
from agx_research.data.schemas import CorporateEvent
from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.decision_service.liquidity_floor import compute_illiquid_tickers
from agx_research.decision_service.position import PositionState
from agx_research.decision_service.service import (
    DecisionService,
    PositionAction,
)
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.explainability import Explanation
from agx_research.horizons.base import Prediction
from agx_research.knowledge.lifecycle import KnowledgeStatus
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_engine import DecisionAction, MetaDecisionEngine, PublicationStatus
from agx_research.meta.decision_quality import apply_decision_quality_gate
from agx_research.validation.statistical import StatisticalEvidence

NO_RISK = CountryRiskAssessment(as_of=date(2026, 6, 14), severity=CountryRiskSeverity.NORMAL)


def make_prediction(
    ticker: str,
    expected_return: float,
    expected_risk: float,
    confidence: float,
    reference_price: float | None = 100.0,
    horizon: Horizon = Horizon.INVESTMENT,
    explanation: Explanation | None = None,
) -> Prediction:
    return Prediction(
        ticker=ticker,
        horizon=horizon,
        as_of=date(2026, 6, 14),
        model_id="investment_alpha",
        model_version="0.1.0",
        expected_return=expected_return,
        expected_risk=expected_risk,
        confidence=confidence,
        reference_price=reference_price,
        explanation=explanation
        or Explanation(
            why_this_stock="test", why_now="test", why_not_others="test",
            supporting_evidence=["test evidence"],
            evidence_refs=[ProvenanceRef(kind="knowledge", ref_id="know-1")],
            invalidation_conditions=["test invalidation condition"],
        ),
        supporting_knowledge_ids=["know-1"],
        provenance=Provenance(produced_by="investment_alpha@0.1.0", produced_at=datetime.now()),
    )


def make_publication_ready_recommendation(
    ticker: str, expected_return: float = 0.10, expected_risk: float = 0.05, confidence: float = 0.8
):
    """A real Recommendation, built the same way `MetaDecisionEngine` always
    builds one (not a hand-constructed fake), pushed through the real
    `apply_decision_quality_gate()` (`meta/decision_quality.py`) -- the
    per-decision gate that replaced the old system-wide, track-record-
    and-legal-review gate (project owner direction, 2026-08-02). Hand-
    setting only `publication_status` (not `max_position_pct`, which the
    same gate function sets) previously left `max_position_pct=0.0`,
    silently zeroing every target weight regardless of a real decision's
    action. Using the real gate function is both the fix and the more
    honest test -- the same lesson `institutional_validation/scenarios.py`
    already learned from its own version of this bug."""
    prediction = make_prediction(ticker, expected_return, expected_risk, confidence)
    recommendation = MetaDecisionEngine().decide(ticker, date(2026, 6, 14), {Horizon.INVESTMENT: prediction})
    assert recommendation is not None
    decision = recommendation.horizon_decisions[Horizon.INVESTMENT]
    assert decision.action == DecisionAction.BUY_CANDIDATE  # sanity: score >= 1.0 threshold cleared
    return apply_decision_quality_gate([recommendation])[0]


def _apply_publication_ready(recommendation):
    """Same real-gate fix as `make_publication_ready_recommendation`, for
    tests that hand-build a multi-horizon `Recommendation` directly."""
    return apply_decision_quality_gate([recommendation])[0]


def make_research_only_recommendation(ticker: str):
    """A real Recommendation whose decision never clears publication --
    the default, honest state for almost everything today."""
    prediction = make_prediction(ticker, 0.10, 0.05, 0.8)
    recommendation = MetaDecisionEngine().decide(ticker, date(2026, 6, 14), {Horizon.INVESTMENT: prediction})
    assert recommendation.horizon_decisions[Horizon.INVESTMENT].publication_status == PublicationStatus.RESEARCH_ONLY
    return recommendation


def test_buy_when_no_position_and_positive_publication_ready_signal():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.action == PositionAction.BUY
    assert decision.target_weight > 0
    assert not decision.abstained
    assert decision.explanation.why_this_stock


def test_research_only_recommendation_never_produces_a_position():
    rec = make_research_only_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert decisions[0].action == PositionAction.NO_ACTION
    assert decisions[0].target_weight == 0.0


def test_increase_when_held_below_cap_and_signal_still_positive():
    rec = make_publication_ready_recommendation("COMI")
    position = PositionState(ticker="COMI", held=True, current_weight=0.01)
    decisions = DecisionService(max_position_weight=0.25).decide_portfolio(
        [rec], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    decision = decisions[0]
    assert decision.action == PositionAction.INCREASE_POSITION
    assert decision.target_weight > position.current_weight


def test_hold_when_held_and_target_matches_current_weight():
    rec = make_publication_ready_recommendation("COMI")
    target = rec.horizon_decisions[Horizon.INVESTMENT].max_position_pct
    # Force target_weight to equal current_weight by capping at the exact
    # score-derived weight (single ticker -> full weight, capped by
    # max_position_weight only).
    service = DecisionService(max_position_weight=target if target > 0 else 0.05)
    position = PositionState(ticker="COMI", held=True, current_weight=service.max_position_weight)
    decisions = service.decide_portfolio(
        [rec], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert decisions[0].action == PositionAction.HOLD


def test_exit_when_held_and_no_fresh_investment_horizon_evidence():
    position = PositionState(ticker="COMI", held=True, current_weight=0.05)
    decisions = DecisionService().decide_portfolio(
        [], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    decision = decisions[0]
    assert decision.abstained
    assert decision.action == PositionAction.HOLD  # abstain overlay while held, never a forced sell


def test_reduce_when_held_and_signal_weakens_but_stays_positive():
    strong = make_publication_ready_recommendation("COMI", expected_return=0.30, expected_risk=0.05)
    weak = make_publication_ready_recommendation("MFPC", expected_return=0.08, expected_risk=0.05)
    # Two competing tickers: COMI's larger relative score shrinks MFPC's
    # normalized share below MFPC's current (previously larger) weight.
    positions = {
        "MFPC": PositionState(ticker="MFPC", held=True, current_weight=0.24),
    }
    decisions = DecisionService(max_position_weight=0.25).decide_portfolio(
        [strong, weak], positions=positions, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    mfpc = next(d for d in decisions if d.ticker == "MFPC")
    assert mfpc.action == PositionAction.REDUCE_POSITION
    assert 0 < mfpc.target_weight < mfpc.current_weight


def test_liquidity_floor_overrides_a_positive_signal_to_no_action():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec],
        positions={},
        as_of=date(2026, 6, 14),
        country_risk=NO_RISK,
        illiquid_tickers={"COMI"},
    )
    decision = decisions[0]
    assert decision.action == PositionAction.NO_ACTION
    assert decision.target_weight == 0.0
    assert any("liquidity" in reason.lower() for reason in decision.reasons)


def test_liquidity_floor_forces_exit_for_a_held_illiquid_position():
    rec = make_publication_ready_recommendation("COMI")
    position = PositionState(ticker="COMI", held=True, current_weight=0.05)
    decisions = DecisionService().decide_portfolio(
        [rec],
        positions={"COMI": position},
        as_of=date(2026, 6, 14),
        country_risk=NO_RISK,
        illiquid_tickers={"COMI"},
    )
    assert decisions[0].action == PositionAction.EXIT


def test_country_risk_crisis_forces_exit_regardless_of_signal_strength():
    rec = make_publication_ready_recommendation("COMI", expected_return=0.50, expected_risk=0.01, confidence=0.99)
    position = PositionState(ticker="COMI", held=True, current_weight=0.05)
    crisis = CountryRiskAssessment(
        as_of=date(2026, 6, 14), severity=CountryRiskSeverity.CRISIS, reasons=["Moody's downgrade"]
    )
    decisions = DecisionService().decide_portfolio(
        [rec], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=crisis
    )
    decision = decisions[0]
    assert decision.action == PositionAction.EXIT
    assert any("downgrade" in reason.lower() for reason in decision.reasons)


def test_country_risk_crisis_forces_no_action_for_unheld_ticker():
    rec = make_publication_ready_recommendation("COMI", expected_return=0.50, expected_risk=0.01, confidence=0.99)
    crisis = CountryRiskAssessment(as_of=date(2026, 6, 14), severity=CountryRiskSeverity.CRISIS)
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=crisis
    )
    assert decisions[0].action == PositionAction.NO_ACTION


def test_macro_overlay_dampens_target_weight_and_records_a_reason():
    from agx_research.decision_service.macro_overlay import MacroDecisionOverlay

    rec = make_publication_ready_recommendation("COMI")
    undampened = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )[0]

    defensive_overlay = MacroDecisionOverlay(
        as_of=date(2026, 6, 14), decision="defensive", score=-0.5,
        exposure_multiplier=0.5, available_weight=1.0,
        rationale="test: defensive macro regime",
    )
    dampened = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK,
        macro_overlay=defensive_overlay,
    )[0]

    assert dampened.target_weight == pytest.approx(undampened.target_weight * 0.5)
    assert any("Macro overlay" in reason for reason in dampened.reasons)


def test_supportive_macro_overlay_leaves_target_weight_unchanged():
    from agx_research.decision_service.macro_overlay import MacroDecisionOverlay

    rec = make_publication_ready_recommendation("COMI")
    supportive_overlay = MacroDecisionOverlay(
        as_of=date(2026, 6, 14), decision="supportive", score=0.5,
        exposure_multiplier=1.0, available_weight=1.0,
        rationale="test: supportive macro regime",
    )
    undampened = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )[0]
    with_overlay = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK,
        macro_overlay=supportive_overlay,
    )[0]
    assert with_overlay.target_weight == pytest.approx(undampened.target_weight)
    assert not any("Macro overlay" in reason for reason in with_overlay.reasons)


def test_sector_is_passed_through_from_the_sectors_map():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK,
        sectors={"COMI": "Banks"},
    )
    assert decisions[0].sector == "Banks"


def test_unclassified_ticker_has_no_fabricated_sector():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK,
    )
    assert decisions[0].sector is None


def test_similar_historical_cases_populated_from_real_prior_events():
    from agx_research.events.entity import EntityKind, EntityRef
    from agx_research.events.event import EventSeverity, EventType
    from agx_research.events.service import EventPlatform, build_candidate_event
    from agx_research.events.taxonomy import EventSubtype

    event_platform = EventPlatform()
    event_platform.register(
        build_candidate_event(
            event_type=EventType.CORPORATE,
            subtype=EventSubtype.DIVIDEND,
            entities=[EntityRef(kind=EntityKind.COMPANY, canonical_id="COMI", raw_mention="COMI")],
            event_date=date(2026, 5, 1),
            source="test",
            confidence=0.8,
            severity=EventSeverity.MEDIUM,
            provenance=Provenance(produced_by="test", produced_at=datetime.now()),
        )
    )

    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK,
        event_platform=event_platform,
    )
    cases = decisions[0].explanation.similar_historical_cases
    assert len(cases) == 1
    assert "2026-05-01" in cases[0]
    assert "dividend" in cases[0].lower()


def test_no_event_platform_leaves_similar_historical_cases_honestly_empty():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert decisions[0].explanation.similar_historical_cases == []


def test_invalid_max_position_weight_rejected():
    import pytest

    with pytest.raises(ValueError):
        DecisionService(max_position_weight=0.0)
    with pytest.raises(ValueError):
        DecisionService(max_position_weight=1.5)


def test_liquidity_floor_helper_flags_thin_and_no_history_tickers():
    from agx_research.data.mock_provider import MockDataProvider
    from agx_research.data.snapshot import build_snapshot
    from pathlib import Path

    mock_root = Path(__file__).resolve().parents[1] / "data" / "mock"
    snapshot = build_snapshot(
        MockDataProvider(mock_root),
        tickers=["COMI", "MFPC", "NOSUCHTICKER"],
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )
    illiquid = compute_illiquid_tickers(snapshot, min_average_traded_value=1e18)
    assert {"COMI", "MFPC"} <= illiquid  # threshold set absurdly high -> everything flagged
    assert "NOSUCHTICKER" in illiquid  # no price history at all -> illiquid, never assumed tradable

    permissive = compute_illiquid_tickers(snapshot, min_average_traded_value=0.0)
    assert "NOSUCHTICKER" in permissive  # still illiquid: no history, regardless of floor
    assert "COMI" not in permissive


def test_decision_carries_horizon_thesis_and_review_date():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    decision = decisions[0]
    assert decision.horizon == Horizon.INVESTMENT
    assert "COMI" in decision.investment_thesis
    assert "buy" in decision.investment_thesis.lower()
    assert decision.expected_review_date == rec.horizon_decisions[Horizon.INVESTMENT].valid_until


def test_no_evidence_decision_has_no_thesis_numbers_and_no_review_date():
    position = PositionState(ticker="COMI", held=True, current_weight=0.05)
    decisions = DecisionService().decide_portfolio(
        [], positions={"COMI": position}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    decision = decisions[0]
    assert decision.expected_review_date is None
    assert "no current investment-horizon evidence" in decision.investment_thesis.lower()


def test_key_risks_include_expected_risk_and_a_disagreeing_sibling_horizon():
    investment_pred = make_prediction("COMI", 0.10, 0.05, 0.8, horizon=Horizon.INVESTMENT)
    micro_pred = make_prediction("COMI", -0.05, 0.03, 0.7, horizon=Horizon.MICRO)
    rec = MetaDecisionEngine().decide(
        "COMI", date(2026, 6, 14), {Horizon.INVESTMENT: investment_pred, Horizon.MICRO: micro_pred}
    )
    assert rec is not None
    assert rec.horizon_decisions[Horizon.MICRO].action == DecisionAction.AVOID
    rec = _apply_publication_ready(rec)

    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    decision = decisions[0]
    assert any("model-estimated risk" in r.lower() for r in decision.key_risks)
    assert any("micro" in r.lower() and "avoid" in r.lower() for r in decision.key_risks)


def test_contradicting_evidence_includes_disagreeing_sibling_horizon_and_country_risk():
    investment_pred = make_prediction("COMI", 0.10, 0.05, 0.8, horizon=Horizon.INVESTMENT)
    swing_pred = make_prediction("COMI", -0.02, 0.03, 0.65, horizon=Horizon.SWING)
    rec = MetaDecisionEngine().decide(
        "COMI", date(2026, 6, 14), {Horizon.INVESTMENT: investment_pred, Horizon.SWING: swing_pred}
    )
    assert rec is not None
    rec = _apply_publication_ready(rec)

    deteriorating = CountryRiskAssessment(
        as_of=date(2026, 6, 14),
        severity=CountryRiskSeverity.DETERIORATING,
        reasons=["EGP_USD moved -6.00% over the available window (floor 5%)"],
    )
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=deteriorating
    )
    decision = decisions[0]
    assert any("swing" in e.lower() for e in decision.contradicting_evidence)
    assert any("egp_usd" in e.lower() for e in decision.contradicting_evidence)
    # Deteriorating (not crisis) country risk must not force target weight to zero.
    assert decision.target_weight > 0


def test_active_catalysts_reflects_a_same_day_corporate_event():
    rec = make_publication_ready_recommendation("COMI")
    as_of = date(2026, 6, 14)
    events = {
        "COMI": [
            CorporateEvent(
                ticker="COMI", event_date=as_of, event_type="dividend", description="Cash dividend declared"
            )
        ]
    }
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=as_of, country_risk=NO_RISK, corporate_events=events
    )
    decision = decisions[0]
    assert any("dividend" in c.lower() for c in decision.active_catalysts)


def test_active_catalysts_empty_without_corporate_events():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert decisions[0].active_catalysts == []


def test_monitoring_events_lists_knowledge_currently_in_monitoring_status(tmp_path):
    explanation = Explanation(
        why_this_stock="test",
        why_now="test",
        why_not_others="test",
        evidence_refs=[ProvenanceRef(kind="knowledge", ref_id="know-1")],
    )
    investment_pred = make_prediction("COMI", 0.10, 0.05, 0.8, explanation=explanation)
    rec = MetaDecisionEngine().decide("COMI", date(2026, 6, 14), {Horizon.INVESTMENT: investment_pred})
    assert rec is not None
    rec = _apply_publication_ready(rec)

    store = KnowledgeStore(tmp_path / "knowledge.json")
    store._repo.add(
        KnowledgeObject(
            id="know-1",
            discovery_date=date(2026, 5, 1),
            creator_agent="test_agent",
            supporting_evidence=["test"],
            confidence=0.8,
            statistical_evidence=StatisticalEvidence(
                method="t-test", statistic=2.5, p_value=0.01, sample_size=100
            ),
            economic_explanation="Momentum persists post-earnings.",
            affected_assets=["COMI"],
            horizon=Horizon.INVESTMENT,
            expected_return=0.10,
            expected_risk=0.05,
            status=KnowledgeStatus.MONITORING,
            provenance=Provenance(produced_by="test", produced_at=datetime.now()),
        )
    )

    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK, knowledge_store=store
    )
    decision = decisions[0]
    assert any("know-1" in m and "momentum" in m.lower() for m in decision.monitoring_events)


def test_monitoring_events_empty_without_a_knowledge_store():
    rec = make_publication_ready_recommendation("COMI")
    decisions = DecisionService().decide_portfolio(
        [rec], positions={}, as_of=date(2026, 6, 14), country_risk=NO_RISK
    )
    assert decisions[0].monitoring_events == []
