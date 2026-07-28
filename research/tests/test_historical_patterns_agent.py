"""Tests for HistoricalPatternsAgent's analog-matching methodology.

Uses hand-built synthetic price series (not the shared mock fixtures,
which are far too short for multi-year analog search) with a deliberately
repeating return pattern: the "matched" 20-day segment is bit-for-bit
identical every cycle, so the agent's own distance metric should find it
at distance 0 in every earlier cycle, making the expected top-k analogs
and their outcomes fully deterministic -- not a statistical approximation
the test has to tolerate.
"""

from __future__ import annotations

from datetime import date, timedelta

from agx_research.agents.historical_patterns import HistoricalPatternsAgent
from agx_research.config import Horizon
from agx_research.data.schemas import PriceBar
from agx_research.data.snapshot import DatasetSnapshot

TICKER = "COMI"

# The 20-day segment that gets matched, identical every cycle.
_MATCHED_PHASE = [
    0.01, -0.02, 0.015, 0.005, -0.01, 0.02, -0.015, 0.01, -0.005, 0.02,
    0.015, -0.02, 0.01, 0.005, -0.01, 0.02, 0.01, -0.015, 0.005, -0.01,
]
# The 10-day "what happened next" segment -- all-positive by construction,
# so every analog in the consistent-outcome fixture agrees in direction.
_POSITIVE_OUTCOME = [0.02, 0.01, 0.015, 0.005, 0.01, 0.02, 0.01, 0.015, 0.005, 0.02]
_NEGATIVE_OUTCOME = [-0.02, -0.01, -0.015, -0.005, -0.01, -0.02, -0.01, -0.015, -0.005, -0.02]


def _bars_from_returns(returns: list[float], *, start_close: float = 100.0) -> list[PriceBar]:
    closes = [start_close]
    for r in returns:
        closes.append(closes[-1] * (1 + r))
    start_date = date(2020, 1, 1)
    return [
        PriceBar(
            ticker=TICKER,
            trade_date=start_date + timedelta(days=i),
            open=c,
            high=c,
            low=c,
            close=c,
            volume=1_000_000,
        )
        for i, c in enumerate(closes)
    ]


def _snapshot_from_bars(bars: list[PriceBar]) -> DatasetSnapshot:
    return DatasetSnapshot(
        id="snap_test_historical_patterns",
        as_of=bars[-1].trade_date,
        lookback_days=30,
        macro_lookback_days=30,
        pattern_lookback_days=len(bars) + 30,
        tickers=[TICKER],
        macro_series_ids=[],
        long_price_history={TICKER: bars},
        long_corporate_events={TICKER: []},
    )


def test_finds_consistent_analogs_and_agrees_on_direction():
    # 5 historical cycles (matched phase + positive outcome) plus a final,
    # current cycle that repeats only the matched phase (its own outcome is
    # what the finding proposes, not yet observed).
    returns: list[float] = []
    for _ in range(5):
        returns += _MATCHED_PHASE + _POSITIVE_OUTCOME
    returns += _MATCHED_PHASE
    bars = _bars_from_returns(returns)
    snapshot = _snapshot_from_bars(bars)

    findings = HistoricalPatternsAgent(
        window=20, forward_horizon=10, top_k=5, min_analogs=4, agreement_threshold=0.7
    ).research(snapshot)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.agent_name == "historical_patterns_agent"
    assert finding.affected_assets == [TICKER]
    assert finding.horizon == Horizon.SWING
    assert "positive" in finding.proposed_hypothesis_statement
    assert any(e == "analogs_matched=5" for e in finding.evidence)
    assert any(e == "directional_agreement=100.00%" for e in finding.evidence)
    assert finding.provenance.inputs[0].ref_id == snapshot.id


def test_abstains_when_analog_outcomes_disagree():
    # Same matched phase every cycle (so distance-0 analogs are still
    # found), but outcomes alternate positive/negative -- 3/5 agreement is
    # below the 0.7 threshold, so the agent must not force a finding.
    outcomes = [_POSITIVE_OUTCOME, _NEGATIVE_OUTCOME, _POSITIVE_OUTCOME, _NEGATIVE_OUTCOME, _POSITIVE_OUTCOME]
    returns = []
    for outcome in outcomes:
        returns += _MATCHED_PHASE + outcome
    returns += _MATCHED_PHASE
    bars = _bars_from_returns(returns)
    snapshot = _snapshot_from_bars(bars)

    findings = HistoricalPatternsAgent(
        window=20, forward_horizon=10, top_k=5, min_analogs=4, agreement_threshold=0.7
    ).research(snapshot)

    assert findings == []


def test_abstains_when_history_too_short():
    bars = _bars_from_returns(_MATCHED_PHASE)  # far fewer bars than window + forward_horizon
    snapshot = _snapshot_from_bars(bars)

    assert HistoricalPatternsAgent().research(snapshot) == []


def test_skips_ticker_with_no_long_price_history():
    snapshot = DatasetSnapshot(
        id="snap_test_no_history",
        as_of=date(2026, 1, 1),
        lookback_days=30,
        macro_lookback_days=30,
        tickers=[TICKER],
        macro_series_ids=[],
    )
    assert HistoricalPatternsAgent().research(snapshot) == []
