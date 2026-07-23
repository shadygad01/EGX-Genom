"""Tests for the real (non-stub) research agents added in System 08."""

from datetime import date
from pathlib import Path

import pytest

from agx_research.agents.corporate_events import CorporateEventsAgent
from agx_research.agents.financial_performance import FinancialPerformanceAgent
from agx_research.agents.historical_patterns import HistoricalPatternsAgent
from agx_research.agents.liquidity import LiquidityAgent
from agx_research.agents.macro import MacroAgent
from agx_research.agents.news_intelligence import NewsIntelligenceAgent
from agx_research.agents.technical_structure import TechnicalStructureAgent
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def snapshot():
    provider = MockDataProvider(MOCK_ROOT)
    return build_snapshot(
        provider,
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD", "EGP_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
    )


def test_macro_agent_finds_series_correlations_above_threshold():
    findings = MacroAgent(correlation_threshold=0.0).research(snapshot())
    assert findings
    for finding in findings:
        assert finding.agent_name == "macro_agent"
        assert len(finding.affected_assets) == 1
        assert finding.proposed_economic_rationale
        assert any(e.startswith("macro_correlation=") for e in finding.evidence)


def test_macro_agent_respects_threshold():
    assert MacroAgent(correlation_threshold=1.01).research(snapshot()) == []


def test_corporate_events_agent_detects_post_event_shift():
    findings = CorporateEventsAgent(min_shift=0.0).research(snapshot())
    assert findings
    tickers = {f.affected_assets[0] for f in findings}
    assert tickers <= {"COMI", "MFPC"}
    for finding in findings:
        assert "drift" in finding.proposed_hypothesis_statement
        assert finding.proposed_candidate_cause


def test_corporate_events_agent_threshold_filters():
    assert CorporateEventsAgent(min_shift=10.0).research(snapshot()) == []


def test_liquidity_agent_relates_volume_to_next_day_returns():
    findings = LiquidityAgent(correlation_threshold=0.0).research(snapshot())
    assert findings
    for finding in findings:
        assert any(e.startswith("volume_return_correlation=") for e in finding.evidence)


def test_technical_structure_agent_detects_ma_gap():
    findings = TechnicalStructureAgent(short_window=3, long_window=8, min_gap=0.0).research(snapshot())
    assert findings
    for finding in findings:
        assert "trend" in finding.proposed_hypothesis_statement
        assert any(e.startswith("ma_gap=") for e in finding.evidence)


def test_technical_structure_agent_rejects_bad_windows():
    with pytest.raises(ValueError):
        TechnicalStructureAgent(short_window=8, long_window=3)


def test_data_blocked_agents_remain_honest_stubs():
    for agent in (NewsIntelligenceAgent(), FinancialPerformanceAgent(), HistoricalPatternsAgent()):
        with pytest.raises(NotImplementedError):
            agent.research(snapshot())


def test_all_agent_findings_carry_snapshot_provenance():
    snap = snapshot()
    for agent in (
        MacroAgent(correlation_threshold=0.0),
        CorporateEventsAgent(min_shift=0.0),
        LiquidityAgent(correlation_threshold=0.0),
        TechnicalStructureAgent(min_gap=0.0),
    ):
        for finding in agent.research(snap):
            assert finding.provenance.inputs[0].ref_id == snap.id
