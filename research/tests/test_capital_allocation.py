"""Tests for the Capital Allocation Intelligence engine -- global
opportunity ranking, the capital deployment queue, opportunity-cost
attribution, and capital recycling. Exercised with hand-built
`PositionAwareDecision`s (the same posture `test_investment_proof.py`
uses for `thesis_survival`), since the engine's whole job is deterministic
bookkeeping over fields `DecisionService` already computes -- no live
pipeline is needed to prove the matching algorithm correct.
"""

from __future__ import annotations

from datetime import date

import pytest

from agx_research.capital_allocation import CapitalAllocationEngine
from agx_research.config import Horizon
from agx_research.decision_service.service import PositionAction, PositionAwareDecision
from agx_research.domain.provenance import Provenance
from agx_research.explainability import Explanation

AS_OF = date(2026, 8, 1)


def _decision(
    ticker: str,
    action: PositionAction,
    *,
    target: float,
    current: float,
    score: float,
    expected_return: float | None = 0.05,
    expected_risk: float | None = 0.03,
    abstained: bool = False,
) -> PositionAwareDecision:
    return PositionAwareDecision(
        ticker=ticker,
        as_of=AS_OF,
        action=action,
        target_weight=target,
        current_weight=current,
        horizon=Horizon.INVESTMENT,
        confidence=0.7,
        opportunity_score=score,
        expected_return=expected_return,
        expected_risk=expected_risk,
        investment_thesis="test thesis",
        abstained=abstained,
        explanation=Explanation(why_this_stock="x", why_now="x", why_not_others="x"),
        provenance=Provenance(produced_by="test", produced_at=AS_OF.isoformat(), inputs=[]),
    )


def test_ranking_orders_every_ticker_by_opportunity_score_descending():
    decisions = [
        _decision("A", PositionAction.NO_ACTION, target=0.0, current=0.0, score=0.2),
        _decision("B", PositionAction.BUY, target=0.3, current=0.0, score=2.0),
        _decision("C", PositionAction.HOLD, target=0.1, current=0.1, score=0.8),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    assert [r.ticker for r in plan.ranking] == ["B", "C", "A"]
    assert [r.rank for r in plan.ranking] == [1, 2, 3]


def test_ranking_includes_zero_score_tickers_not_only_funded_ones():
    decisions = [
        _decision("WINNER", PositionAction.BUY, target=0.2, current=0.0, score=1.0),
        _decision("REJECTED", PositionAction.NO_ACTION, target=0.0, current=0.0, score=0.0),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    assert {r.ticker for r in plan.ranking} == {"WINNER", "REJECTED"}
    assert len(plan.queue) == 1  # only the funded ticker has a real capital request


def test_new_buy_is_funded_from_idle_cash_when_cash_is_sufficient():
    decisions = [
        _decision("HELD", PositionAction.HOLD, target=0.2, current=0.2, score=0.5),
        _decision("NEW", PositionAction.BUY, target=0.3, current=0.0, score=1.5),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    entry = plan.queue[0]
    assert entry.ticker == "NEW"
    assert len(entry.capital_sources) == 1
    assert entry.capital_sources[0].ticker is None  # funded entirely from cash
    assert entry.capital_sources[0].amount == pytest.approx(0.3)
    assert plan.capital_recycled == []  # nothing displaced -- cash was enough


def test_insufficient_cash_displaces_the_weakest_ranked_holding_first():
    decisions = [
        _decision("WEAK", PositionAction.EXIT, target=0.0, current=0.25, score=0.0),
        _decision("MID", PositionAction.HOLD, target=0.35, current=0.35, score=0.6),
        _decision("OK", PositionAction.HOLD, target=0.30, current=0.30, score=0.5),
        _decision("STRONG_NEW", PositionAction.BUY, target=0.30, current=0.0, score=2.0),
    ]
    # idle cash before = 1 - (0.25+0.35+0.30+0) = 0.10; STRONG_NEW needs 0.30
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    entry = next(q for q in plan.queue if q.ticker == "STRONG_NEW")
    sources_by_ticker = {s.ticker: s.amount for s in entry.capital_sources}
    assert sources_by_ticker[None] == pytest.approx(0.10)
    assert sources_by_ticker["WEAK"] == pytest.approx(0.20)
    # MID/OK outrank STRONG_NEW's need for displacement -- never touched.
    assert "MID" not in sources_by_ticker
    assert "OK" not in sources_by_ticker

    release = next(r for r in plan.capital_released_today if r.ticker == "WEAK")
    assert release.amount == pytest.approx(0.25)
    destinations = {d.ticker: d.amount for d in release.destinations}
    assert destinations["STRONG_NEW"] == pytest.approx(0.20)
    assert destinations[None] == pytest.approx(0.05)  # remainder returned to cash

    assert ("WEAK", "STRONG_NEW", pytest.approx(0.20)) == (
        plan.capital_recycled[0].from_ticker,
        plan.capital_recycled[0].to_ticker,
        plan.capital_recycled[0].amount,
    )


def test_stronger_holding_is_never_displaced_to_fund_a_weaker_new_idea():
    decisions = [
        _decision("STRONG_HELD", PositionAction.HOLD, target=0.40, current=0.40, score=2.5),
        _decision("WEAK_NEW", PositionAction.BUY, target=0.10, current=0.0, score=0.3),
    ]
    # idle cash = 1 - 0.40 = 0.60, plenty to fund WEAK_NEW without touching STRONG_HELD.
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    entry = plan.queue[0]
    assert entry.ticker == "WEAK_NEW"
    assert all(s.ticker is None for s in entry.capital_sources)
    assert plan.capital_released_today == []


def test_highest_opportunity_cost_names_the_best_rejected_idea():
    decisions = [
        _decision("FUNDED", PositionAction.BUY, target=0.9, current=0.0, score=5.0),
        _decision("BEST_REJECTED", PositionAction.NO_ACTION, target=0.0, current=0.0, score=1.2),
        _decision("WORST_REJECTED", PositionAction.NO_ACTION, target=0.0, current=0.0, score=0.1),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    assert plan.highest_opportunity_cost[0].ticker == "BEST_REJECTED"
    assert plan.highest_opportunity_cost[0].opportunity_score == pytest.approx(1.2)
    tickers = [h.ticker for h in plan.highest_opportunity_cost]
    assert tickers == sorted(tickers, key=lambda t: -next(h.opportunity_score for h in plan.highest_opportunity_cost if h.ticker == t))

    entry = plan.queue[0]
    assert "BEST_REJECTED" in entry.opportunity_cost_note


def test_no_rejected_alternative_states_so_explicitly():
    decisions = [
        _decision("ONLY", PositionAction.BUY, target=0.1, current=0.0, score=1.0),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    assert plan.highest_opportunity_cost == []
    assert "no rejected alternative exists today" in plan.queue[0].opportunity_cost_note


def test_best_new_opportunities_excludes_already_held_increases():
    decisions = [
        _decision("BRAND_NEW", PositionAction.BUY, target=0.2, current=0.0, score=1.0),
        _decision("TOPPED_UP", PositionAction.INCREASE_POSITION, target=0.3, current=0.1, score=0.8),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    assert [r.ticker for r in plan.best_new_opportunities] == ["BRAND_NEW"]


def test_allocation_changes_covers_every_moved_ticker_sorted_by_magnitude():
    decisions = [
        _decision("SMALL_MOVE", PositionAction.REDUCE_POSITION, target=0.09, current=0.10, score=0.4),
        _decision("BIG_MOVE", PositionAction.BUY, target=0.30, current=0.0, score=2.0),
        _decision("UNCHANGED", PositionAction.HOLD, target=0.10, current=0.10, score=0.5),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    tickers = [c.ticker for c in plan.allocation_changes]
    assert tickers == ["BIG_MOVE", "SMALL_MOVE"]  # UNCHANGED never appears


def test_cash_waiting_reflects_true_leftover_after_all_targets():
    decisions = [
        _decision("A", PositionAction.BUY, target=0.2, current=0.0, score=1.0),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    assert plan.cash_waiting.idle_cash_before == pytest.approx(1.0)
    assert plan.cash_waiting.idle_cash_after == pytest.approx(0.8)
    assert plan.cash_waiting.idle_cash_after > 0
    assert "cash" in plan.cash_waiting.reason.lower()


def test_fully_deployed_portfolio_reports_zero_idle_cash_and_no_waiting_reason_conflict():
    decisions = [
        _decision("ALL_IN", PositionAction.BUY, target=1.0, current=0.0, score=3.0),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    assert plan.cash_waiting.idle_cash_after == pytest.approx(0.0)
    assert "deployed" in plan.cash_waiting.reason.lower()


def test_abstained_held_ticker_never_triggers_a_fabricated_capital_release():
    # DecisionService labels an abstained held ticker "hold" but still
    # reports target_weight=0.0 (no fresh evidence to score) -- the engine
    # must not read that as a real sell-to-fund-something-else movement.
    decisions = [
        _decision("NO_FRESH_EVIDENCE", PositionAction.HOLD, target=0.0, current=0.05, score=0.0, abstained=True),
        _decision("NEW", PositionAction.BUY, target=0.1, current=0.0, score=1.0),
    ]
    plan = CapitalAllocationEngine().build(decisions, AS_OF)
    assert plan.capital_released_today == []
    assert plan.capital_recycled == []
    assert [c.ticker for c in plan.allocation_changes] == ["NEW"]
    entry = plan.queue[0]
    assert entry.capital_sources[0].ticker is None  # funded from cash, not from the abstained holding
    # The abstained ticker still appears in the ranking (transparency),
    # just never as a capital source/demand.
    assert "NO_FRESH_EVIDENCE" in {r.ticker for r in plan.ranking}


def test_empty_universe_produces_an_honest_empty_plan():
    plan = CapitalAllocationEngine().build([], AS_OF)
    assert plan.ranking == []
    assert plan.queue == []
    assert plan.capital_released_today == []
    assert plan.capital_recycled == []
    assert plan.best_new_opportunities == []
    assert plan.highest_opportunity_cost == []
    assert plan.allocation_changes == []
    assert plan.cash_waiting.idle_cash_before == pytest.approx(1.0)
    assert plan.cash_waiting.idle_cash_after == pytest.approx(1.0)
