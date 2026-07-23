from datetime import date
from pathlib import Path

from agx_research.agents.market_structure import MarketStructureAgent
from agx_research.data.mock_provider import MockDataProvider
from agx_research.data.snapshot import build_snapshot

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"


def make_snapshot(tickers: list[str], lookback_days: int = 30):
    provider = MockDataProvider(MOCK_ROOT)
    return build_snapshot(
        provider,
        tickers=tickers,
        macro_series_ids=[],
        as_of=date(2026, 6, 14),
        lookback_days=lookback_days,
    )


def test_finds_correlated_pair_above_threshold():
    snapshot = make_snapshot(["COMI", "MFPC"])
    agent = MarketStructureAgent(ticker_pairs=[("COMI", "MFPC")], correlation_threshold=0.0)

    findings = agent.research(snapshot)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.agent_name == "market_structure_agent"
    assert finding.agent_version == "0.1.0"
    assert set(finding.affected_assets) == {"COMI", "MFPC"}
    assert any(e.startswith("pairwise_return_correlation") for e in finding.evidence)
    assert finding.provenance.inputs[0].kind == "dataset_snapshot"
    assert finding.provenance.inputs[0].ref_id == snapshot.id


def test_no_finding_when_threshold_too_high():
    snapshot = make_snapshot(["COMI", "MFPC"])
    agent = MarketStructureAgent(ticker_pairs=[("COMI", "MFPC")], correlation_threshold=1.01)

    findings = agent.research(snapshot)

    assert findings == []


def test_no_finding_for_ticker_with_insufficient_history():
    snapshot = make_snapshot(["COMI", "NOPE"])
    agent = MarketStructureAgent(ticker_pairs=[("COMI", "NOPE")], correlation_threshold=0.0)

    findings = agent.research(snapshot)

    assert findings == []
