"""Tests for the real (non-stub) research agents added in System 08."""

from datetime import date
from pathlib import Path

import pytest

from agx_research.agents.corporate_events import CorporateEventsAgent
from agx_research.agents.financial_performance import FinancialPerformanceAgent
from agx_research.agents.liquidity import LiquidityAgent
from agx_research.agents.macro import MacroAgent
from agx_research.agents.news_intelligence import NewsIntelligenceAgent
from agx_research.agents.technical_structure import TechnicalStructureAgent
from agx_research.config import Horizon
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot
from agx_research.financials.provider import FinancialStatementProvider
from agx_research.financials.schema import FinancialStatementLineItem

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


class _FakeFinancialStatementProvider(FinancialStatementProvider):
    """In-memory fixture -- no mock financial-statement CSVs exist yet
    (real collectors only cover 2 real companies with 1-2 periods each),
    so agent-mechanism tests need synthetic multi-period data, exactly
    like `test_financials.py`'s own `_write_line_items_csv` fixture does
    for `CollectedFinancialStatementProvider`."""

    def __init__(self, items: dict[str, list[FinancialStatementLineItem]]):
        self.items = items

    def get_line_items(self, ticker, start, end, *, statement_type=None):
        return [
            item
            for item in self.items.get(ticker, [])
            if start <= item.period_end_date <= end
            and (statement_type is None or item.statement_type == statement_type)
        ]


def snapshot(financials_provider: FinancialStatementProvider | None = None):
    provider = MockDataProvider(MOCK_ROOT)
    return build_snapshot(
        provider,
        tickers=["COMI", "MFPC"],
        macro_series_ids=["BRENT_USD", "EGP_USD"],
        as_of=date(2026, 6, 14),
        lookback_days=30,
        financials_provider=financials_provider,
    )


def _line_item(ticker, period_end_date, statement_type, line_item, value):
    return FinancialStatementLineItem(
        ticker=ticker,
        period_end_date=period_end_date,
        period_type="ANNUAL",
        statement_type=statement_type,
        line_item=line_item,
        value=value,
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


def test_financial_performance_agent_empty_when_no_statements():
    # No financials_provider given -> financial_statements stays {} ->
    # honestly zero findings, never fabricated.
    assert FinancialPerformanceAgent().research(snapshot()) == []


def test_financial_performance_agent_detects_growth_acceleration():
    # All periods within the default 730-day financials_lookback_days
    # window behind the snapshot's as_of (2026-06-14).
    items = {
        "COMI": [
            _line_item("COMI", date(2024, 9, 30), "INCOME_STATEMENT", "revenue", 1_000_000),
            _line_item("COMI", date(2024, 12, 31), "INCOME_STATEMENT", "revenue", 1_050_000),
            _line_item("COMI", date(2025, 3, 31), "INCOME_STATEMENT", "revenue", 1_100_000),
            _line_item("COMI", date(2025, 6, 30), "INCOME_STATEMENT", "revenue", 1_400_000),
        ]
    }
    findings = FinancialPerformanceAgent(min_growth_shift=0.0).research(
        snapshot(_FakeFinancialStatementProvider(items))
    )
    growth_findings = [f for f in findings if "revenue growth" in f.proposed_hypothesis_statement]
    assert growth_findings
    finding = growth_findings[0]
    assert finding.agent_name == "financial_performance_agent"
    assert finding.horizon == Horizon.INVESTMENT
    assert finding.affected_assets == ["COMI"]
    assert "accelerating" in finding.proposed_hypothesis_statement
    assert any(e.startswith("recent_growth_rate=") for e in finding.evidence)


def test_financial_performance_agent_growth_threshold_filters():
    items = {
        "COMI": [
            _line_item("COMI", date(2024, 9, 30), "INCOME_STATEMENT", "revenue", 1_000_000),
            _line_item("COMI", date(2024, 12, 31), "INCOME_STATEMENT", "revenue", 1_050_000),
            _line_item("COMI", date(2025, 3, 31), "INCOME_STATEMENT", "revenue", 1_100_000),
            _line_item("COMI", date(2025, 6, 30), "INCOME_STATEMENT", "revenue", 1_150_000),
        ]
    }
    findings = FinancialPerformanceAgent(min_growth_shift=10.0, min_leverage_shift=10.0).research(
        snapshot(_FakeFinancialStatementProvider(items))
    )
    assert findings == []


def test_financial_performance_agent_detects_rising_leverage():
    items = {
        "MFPC": [
            _line_item("MFPC", date(2024, 9, 30), "BALANCE_SHEET", "total_debt", 200_000),
            _line_item("MFPC", date(2024, 9, 30), "BALANCE_SHEET", "total_equity", 1_000_000),
            _line_item("MFPC", date(2024, 12, 31), "BALANCE_SHEET", "total_debt", 220_000),
            _line_item("MFPC", date(2024, 12, 31), "BALANCE_SHEET", "total_equity", 1_000_000),
            _line_item("MFPC", date(2025, 3, 31), "BALANCE_SHEET", "total_debt", 240_000),
            _line_item("MFPC", date(2025, 3, 31), "BALANCE_SHEET", "total_equity", 1_000_000),
            _line_item("MFPC", date(2025, 6, 30), "BALANCE_SHEET", "total_debt", 600_000),
            _line_item("MFPC", date(2025, 6, 30), "BALANCE_SHEET", "total_equity", 1_000_000),
        ]
    }
    findings = FinancialPerformanceAgent(min_leverage_shift=0.0).research(
        snapshot(_FakeFinancialStatementProvider(items))
    )
    leverage_findings = [f for f in findings if "leverage" in f.proposed_hypothesis_statement]
    assert leverage_findings
    finding = leverage_findings[0]
    assert finding.horizon == Horizon.INVESTMENT
    assert "deteriorating" in finding.proposed_hypothesis_statement
    assert any(e.startswith("recent_debt_to_equity=") for e in finding.evidence)


def test_financial_performance_agent_requires_min_periods():
    items = {
        "COMI": [
            _line_item("COMI", date(2025, 12, 31), "INCOME_STATEMENT", "revenue", 1_000_000),
            _line_item("COMI", date(2026, 3, 31), "INCOME_STATEMENT", "revenue", 2_000_000),
        ]
    }
    assert FinancialPerformanceAgent(min_growth_shift=0.0).research(
        snapshot(_FakeFinancialStatementProvider(items))
    ) == []


def test_news_intelligence_agent_relates_sentiment_to_drift():
    findings = NewsIntelligenceAgent(min_shift=0.0).research(snapshot())
    assert findings
    tickers = {f.affected_assets[0] for f in findings}
    assert tickers <= {"COMI", "MFPC"}
    for finding in findings:
        assert finding.agent_name == "news_intelligence_agent"
        assert finding.horizon == Horizon.MICRO
        assert "drift" in finding.proposed_hypothesis_statement
        assert any(e.startswith("sentiment=") for e in finding.evidence)


def test_news_intelligence_agent_threshold_filters():
    assert NewsIntelligenceAgent(min_shift=10.0).research(snapshot()) == []


def test_news_intelligence_agent_skips_unclassifiable_headlines():
    # "Brent crude climbs on supply concerns" (mock news.csv) is tagged to
    # MFPC but is macro commentary, not a company-sentiment headline -- it
    # still matches "climbs" in the declared positive-phrase list, so this
    # test only asserts the agent never fabricates a sentiment for a
    # headline matching none of the declared phrases.
    from agx_research.agents.news_sentiment import classify_headline_sentiment

    assert classify_headline_sentiment("EGX30 index closes flat in quiet trading") is None


def test_all_agent_findings_carry_snapshot_provenance():
    items = {
        "COMI": [
            _line_item("COMI", date(2024, 9, 30), "INCOME_STATEMENT", "revenue", 1_000_000),
            _line_item("COMI", date(2024, 12, 31), "INCOME_STATEMENT", "revenue", 1_050_000),
            _line_item("COMI", date(2025, 3, 31), "INCOME_STATEMENT", "revenue", 1_100_000),
            _line_item("COMI", date(2025, 6, 30), "INCOME_STATEMENT", "revenue", 1_400_000),
        ]
    }
    snap = snapshot(_FakeFinancialStatementProvider(items))
    for agent in (
        MacroAgent(correlation_threshold=0.0),
        CorporateEventsAgent(min_shift=0.0),
        LiquidityAgent(correlation_threshold=0.0),
        TechnicalStructureAgent(min_gap=0.0),
        NewsIntelligenceAgent(min_shift=0.0),
        FinancialPerformanceAgent(min_growth_shift=0.0),
    ):
        for finding in agent.research(snap):
            assert finding.provenance.inputs[0].ref_id == snap.id
