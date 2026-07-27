"""MacroAgent must align a lower-frequency macro series onto every
trading day via forward-fill, not just the (rare) days its raw
observation date happens to match exactly -- see agents/macro.py's
module docstring for why."""

from datetime import date, timedelta

from agx_research.agents.macro import MacroAgent, _forward_fill_onto
from agx_research.data.schemas import MacroObservation, PriceBar
from agx_research.data.snapshot import DatasetSnapshot

TICKER = "TST"
SERIES = "TESTSERIES"


def _bars_with_returns(returns: list[float]) -> list[PriceBar]:
    """21 daily bars (day0..day20) whose adjusted returns equal `returns`
    exactly (a pure close-to-close price series, no corporate events)."""
    close = 100.0
    bars = [PriceBar(ticker=TICKER, trade_date=date(2026, 1, 1), open=close, high=close, low=close, close=close, volume=1000)]
    for i, r in enumerate(returns, start=1):
        close = close * (1 + r)
        bars.append(
            PriceBar(
                ticker=TICKER,
                trade_date=date(2026, 1, 1) + timedelta(days=i),
                open=close, high=close, low=close, close=close, volume=1000,
            )
        )
    return bars


def _snapshot(returns: list[float], macro_obs: list[MacroObservation]) -> DatasetSnapshot:
    bars = _bars_with_returns(returns)
    return DatasetSnapshot(
        id="snap_test",
        as_of=bars[-1].trade_date,
        lookback_days=30,
        macro_lookback_days=30,
        tickers=[TICKER],
        macro_series_ids=[SERIES],
        price_history={TICKER: bars},
        macro_series={SERIES: macro_obs},
    )


def test_forward_fill_helper_carries_last_value_forward_never_backward():
    changes = {date(2026, 1, 5): 0.10, date(2026, 1, 10): -0.20}
    trading_dates = [date(2026, 1, d) for d in (1, 5, 6, 9, 10, 12)]
    aligned = _forward_fill_onto(changes, trading_dates)
    # Nothing before the first observation date is assigned.
    assert date(2026, 1, 1) not in aligned
    assert aligned[date(2026, 1, 5)] == 0.10
    assert aligned[date(2026, 1, 6)] == 0.10  # carried forward, no new observation yet
    assert aligned[date(2026, 1, 9)] == 0.10  # still carried forward
    assert aligned[date(2026, 1, 10)] == -0.20  # new observation takes over
    assert aligned[date(2026, 1, 12)] == -0.20


def test_macro_agent_finds_correlation_from_a_low_frequency_series():
    # 3 raw observation dates (day5/10/15) only intersect 3 trading days by
    # exact-date match -- below the agent's own 4-observation minimum, so a
    # pre-forward-fill agent would find nothing here at all. Forward-fill
    # extends each step value across every trading day until the next
    # observation, covering day5..day20 (16 trading days).
    macro_obs = [
        MacroObservation(series_id=SERIES, observation_date=date(2026, 1, 1) + timedelta(days=d), value=v)
        for d, v in ((0, 100.0), (5, 110.0), (10, 90.0), (15, 120.0))
    ]
    step_changes = {
        date(2026, 1, 6): 0.10,           # (110-100)/100
        date(2026, 1, 11): -18.0 / 110,   # (90-110)/110
        date(2026, 1, 16): 30.0 / 90,     # (120-90)/90
    }
    # Returns for day1..day20: 0 before the first step applies, exactly
    # matching the forward-filled macro change afterward -> correlation 1.0.
    returns = []
    for i in range(1, 21):
        day = date(2026, 1, 1) + timedelta(days=i)
        applicable = [v for d, v in step_changes.items() if d <= day]
        returns.append(applicable[-1] if applicable else 0.0)

    snapshot = _snapshot(returns, macro_obs)
    findings = MacroAgent(correlation_threshold=0.9).research(snapshot)
    assert findings
    finding = findings[0]
    assert finding.affected_assets == [TICKER]
    observations = int(next(e for e in finding.evidence if e.startswith("observations=")).split("=")[1])
    # Far more than the 3 raw observation dates -- proof forward-fill, not
    # exact-date matching, produced this finding.
    assert observations > 3
