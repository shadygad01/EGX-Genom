"""The canonical, point-in-time research panel.

Every downstream stage (Feature Factory, Target Factory, candidate
generation) reads from a `ResearchPanel`, never from a live `DataProvider`
or a raw CSV — the same "agents consume a snapshot, never a live provider"
discipline `data.snapshot.DatasetSnapshot` already enforces, extended to
research/backtesting. `build_research_panel()` is a thin materialization
over `market_memory.MarketMemory.reconstruct()` (the codebase's own
"sanctioned way to reconstruct historical state" — see that module's
docstring), not a parallel data path.

Two index spaces exist deliberately:

- `TickerSeries.dates[i]` is `observation_time` — the calendar date a bar's
  facts describe.
- Every `MacroObservation` kept in `ResearchPanel.macro_series` already
  passed `data.point_in_time.is_knowable()` relative to the panel's outer
  `as_of` (via `MarketMemory`'s own `macro_series_sources` filtering) — but
  that is necessary, not sufficient, for a per-row feature at some earlier
  interior date `t < as_of`: it must be re-checked with `t` as the
  reference date. `macro_series_sources` is threaded through so
  `features.py` can perform that second, per-row check itself
  (`available_time(obs) <= t`), which is what makes a macro feature safe
  to use at any interior row, not only at the panel's own `as_of`.

Universe/sector membership is carried as a **single fixed snapshot for the
whole panel**, not resolved per interior date — `docs/
PATTERN_DISCOVERY_DATA_AUDIT.md` documents why: only one dated EGX30/EGX70
snapshot (2026-07-26) exists in this repository, so there is no historical
reconstitution series to resolve against. Treating membership as fixed is
an explicit, flagged survivorship-bias limitation, not a hidden one — see
`ResearchPanel.universe_limitation_note`.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.data.adjustments import compute_adjusted_closes
from agx_research.data.schemas import CorporateEvent, MacroObservation, PriceBar
from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.market_memory.memory import MarketMemory
from agx_research.patterns.universe_confidence import UniverseConfidence, assess_universe_confidence

UNIVERSE_LIMITATION_NOTE = (
    "Universe/sector membership reflects a single fixed snapshot (the "
    "panel's outer as_of), not a point-in-time reconstruction — no "
    "historical index-reconstitution series exists in this repository "
    "(docs/PATTERN_DISCOVERY_DATA_AUDIT.md). Any pattern discovered here "
    "should be read as conditioned on today's constituents/sectors "
    "applied uniformly across the study period, a real survivorship-bias "
    "exposure this platform does not currently have the data to close."
)


class TickerSeries(BaseModel):
    """One ticker's point-in-time-safe daily series, ascending by date.

    All list fields share one index space: `dates[i]` describes the same
    trading day as `close[i]`, `adjusted_close[i]`, `volume[i]`, etc.
    `adjusted_close` is the sole basis for every return calculation
    downstream (never `close`), via `data.adjustments.compute_adjusted_closes`
    — the same split/dividend-adjustment convention every other return
    calculation in this codebase uses.
    """

    ticker: str
    dates: list[date] = Field(default_factory=list)
    open: list[float] = Field(default_factory=list)
    high: list[float] = Field(default_factory=list)
    low: list[float] = Field(default_factory=list)
    close: list[float] = Field(default_factory=list)
    adjusted_close: list[float] = Field(default_factory=list)
    volume: list[int] = Field(default_factory=list)
    sector: str | None = None

    def index_of(self, as_of: date) -> int | None:
        """The row index whose date equals `as_of`, or None if absent."""
        try:
            return self.dates.index(as_of)
        except ValueError:
            return None


class ResearchPanel(BaseModel):
    as_of: date
    tickers: list[str]
    series: dict[str, TickerSeries] = Field(default_factory=dict)
    sectors: dict[str, str] = Field(default_factory=dict)
    macro_series: dict[str, list[MacroObservation]] = Field(default_factory=dict)
    macro_series_sources: dict[str, str] = Field(default_factory=dict)
    financial_statements: dict[str, list[FinancialStatementLineItem]] = Field(default_factory=dict)
    universe_limitation_note: str = UNIVERSE_LIMITATION_NOTE
    universe_confidence: UniverseConfidence = UniverseConfidence.NONE

    def all_dates(self) -> list[date]:
        """The sorted union of every trading date any ticker has a bar for —
        the shared cross-sectional calendar cross-sectional features walk."""
        observed: set[date] = set()
        for ticker_series in self.series.values():
            observed.update(ticker_series.dates)
        return sorted(observed)


def _build_ticker_series(
    ticker: str,
    bars: list[PriceBar],
    events: list[CorporateEvent],
    sector: str | None,
) -> TickerSeries:
    sorted_bars = sorted(bars, key=lambda b: b.trade_date)
    adjusted = compute_adjusted_closes(sorted_bars, events)
    return TickerSeries(
        ticker=ticker,
        dates=[b.trade_date for b in sorted_bars],
        open=[b.open for b in sorted_bars],
        high=[b.high for b in sorted_bars],
        low=[b.low for b in sorted_bars],
        close=[b.close for b in sorted_bars],
        adjusted_close=[adjusted[b.trade_date] for b in sorted_bars],
        volume=[b.volume for b in sorted_bars],
        sector=sector,
    )


def build_research_panel(
    memory: MarketMemory,
    *,
    as_of: date,
    tickers: list[str] | None = None,
) -> ResearchPanel:
    """Materialize a `ResearchPanel` as of `as_of`.

    `memory` should be constructed with a generous `pattern_lookback_days`
    (see `data.snapshot.build_snapshot`'s own docstring on why this needs
    its own, much wider window than every other agent's `price_history`) —
    without it, `long_price_history`/`long_corporate_events` stay empty and
    this falls back to the standard, much shorter `lookback_days` window,
    which will honestly still work but with less depth. `tickers`, when
    given, is intersected with what actually has price history rather than
    assumed; when omitted, the panel uses the reconstructed universe
    snapshot's constituents (see `ResearchPanel.universe_limitation_note`).
    """
    state = memory.reconstruct(as_of)
    snapshot = state.dataset_snapshot

    candidate_tickers = tickers if tickers is not None else sorted(state.constituents)
    series: dict[str, TickerSeries] = {}
    for ticker in candidate_tickers:
        bars = snapshot.long_price_history.get(ticker) or snapshot.price_history.get(ticker) or []
        if len(bars) < 2:
            continue
        events = (
            snapshot.long_corporate_events.get(ticker)
            or snapshot.corporate_events.get(ticker)
            or []
        )
        series[ticker] = _build_ticker_series(ticker, bars, events, state.sectors.get(ticker))

    return ResearchPanel(
        as_of=as_of,
        tickers=sorted(series),
        series=series,
        sectors=dict(state.sectors),
        macro_series=dict(snapshot.macro_series),
        macro_series_sources=dict(memory.macro_series_sources or {}),
        financial_statements=dict(snapshot.financial_statements),
        universe_confidence=assess_universe_confidence(as_of),
    )


__all__ = [
    "UNIVERSE_LIMITATION_NOTE",
    "ResearchPanel",
    "TickerSeries",
    "build_research_panel",
]
