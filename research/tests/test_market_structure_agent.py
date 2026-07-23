from datetime import date
from pathlib import Path

from agx_research.agents.market_structure import MarketStructureAgent
from agx_research.data.mock_provider import MockDataProvider

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def test_finds_correlated_pair_above_threshold():
    provider = MockDataProvider(MOCK_ROOT)
    agent = MarketStructureAgent(
        ticker_pairs=[("COMI", "MFPC")], lookback_days=30, correlation_threshold=0.0
    )

    findings = agent.research(provider, date(2026, 6, 14))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.agent_name == "market_structure_agent"
    assert set(finding.affected_assets) == {"COMI", "MFPC"}
    assert any(e.startswith("pearson_correlation=") for e in finding.evidence)


def test_no_finding_when_threshold_too_high():
    provider = MockDataProvider(MOCK_ROOT)
    agent = MarketStructureAgent(
        ticker_pairs=[("COMI", "MFPC")], lookback_days=30, correlation_threshold=1.01
    )

    findings = agent.research(provider, date(2026, 6, 14))

    assert findings == []


def test_no_finding_for_ticker_with_insufficient_history():
    provider = MockDataProvider(MOCK_ROOT)
    agent = MarketStructureAgent(
        ticker_pairs=[("COMI", "NOPE")], lookback_days=30, correlation_threshold=0.0
    )

    findings = agent.research(provider, date(2026, 6, 14))

    assert findings == []
