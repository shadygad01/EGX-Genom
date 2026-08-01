"""Tests for ShadowFundLedger persistence and the two dashboard exports."""

from __future__ import annotations

from datetime import date

from agx_research.decision_service.country_risk import CountryRiskAssessment, CountryRiskSeverity
from agx_research.shadow_fund.engine import advance
from agx_research.shadow_fund.export import export_shadow_fund, export_shadow_fund_history
from agx_research.shadow_fund.repository import ShadowFundLedger
from tests.test_shadow_fund import make_recommendation, snapshot_with_prices

NO_RISK = CountryRiskAssessment(as_of=date(2026, 7, 1), severity=CountryRiskSeverity.NORMAL)


def test_ledger_history_is_the_daily_nav_series(tmp_path):
    ledger = ShadowFundLedger(tmp_path / "shadow_fund.json")
    assert ledger.latest_snapshot() is None
    assert export_shadow_fund(ledger) is None

    day1 = date(2026, 7, 1)
    rec1 = make_recommendation("COMI", day1)
    snap1 = snapshot_with_prices(day1, {"COMI": [(day1, 100.0)], "EGX30": [(day1, 100.0)]})
    state1 = advance(None, [rec1], day1, snap1, country_risk=NO_RISK)
    ledger.record(state1)

    day2 = date(2026, 7, 2)
    rec2 = make_recommendation("COMI", day2)
    snap2 = snapshot_with_prices(
        day2, {"COMI": [(day1, 100.0), (day2, 105.0)], "EGX30": [(day1, 100.0), (day2, 100.0)]}
    )
    state2 = advance(state1, [rec2], day2, snap2, country_risk=NO_RISK)
    ledger.record(state2)

    assert len(ledger.daily_history()) == 2
    assert ledger.latest_snapshot().date == day2

    # Persisted round-trip -- a fresh ledger instance reading the same file
    # must reconstruct the identical two-day history.
    reloaded = ShadowFundLedger(tmp_path / "shadow_fund.json")
    assert len(reloaded.daily_history()) == 2
    assert reloaded.latest_snapshot().nav == state2.nav


def test_export_shadow_fund_current_state(tmp_path):
    ledger = ShadowFundLedger(tmp_path / "shadow_fund.json")
    day1 = date(2026, 7, 1)
    rec1 = make_recommendation("COMI", day1)
    snap1 = snapshot_with_prices(day1, {"COMI": [(day1, 100.0)], "EGX30": [(day1, 100.0)]})
    state1 = advance(None, [rec1], day1, snap1, country_risk=NO_RISK)
    ledger.record(state1)

    state = export_shadow_fund(ledger)
    assert state is not None
    assert state.nav == state1.nav
    assert state.closed_positions == []
    assert not hasattr(state, "attribution_state")  # internal-only rolling state, not published
    assert not hasattr(state, "closed_positions_today")


def test_export_shadow_fund_history_flattens_transactions_across_days(tmp_path):
    ledger = ShadowFundLedger(tmp_path / "shadow_fund.json")
    day1 = date(2026, 7, 1)
    rec1 = make_recommendation("COMI", day1)
    snap1 = snapshot_with_prices(day1, {"COMI": [(day1, 100.0)], "EGX30": [(day1, 100.0)]})
    state1 = advance(None, [rec1], day1, snap1, country_risk=NO_RISK)
    ledger.record(state1)

    history = export_shadow_fund_history(ledger)
    assert len(history.nav_series) == 1
    assert len(history.transactions) == 1
    assert history.transactions[0].ticker == "COMI"
