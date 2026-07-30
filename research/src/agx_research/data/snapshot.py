"""Point-in-time, content-hashed dataset bundles.

Agents, experiments, and validators consume a `DatasetSnapshot` rather than
querying a live `DataProvider` directly. That gives every finding,
experiment result, and hypothesis a concrete, versioned "Dataset" it ran
against (Principle 5), and rules out look-ahead bias by construction:
nothing in a snapshot is dated after its `as_of`, and the same query always
produces the same `id` (a content hash), so re-running research later
against a `DataProvider` that has since been extended or revised is
detectable rather than silently changing past results.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta

from pydantic import BaseModel, Field

from agx_research.data.point_in_time import is_knowable
from agx_research.data.provider import DataProvider
from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar
from agx_research.financials.provider import FinancialStatementProvider
from agx_research.financials.schema import FinancialStatementLineItem


class DatasetSnapshot(BaseModel):
    """`version` is always 1: `id` is a content hash, so genuinely different
    content always gets a different id rather than a new revision of the
    same one. The field exists so `DatasetSnapshotRepository` (and the
    generic `storage.Repository[T]` it's built on) can treat every entity
    in the system uniformly, per "everything must be versioned."
    """

    id: str
    version: int = 1
    as_of: date
    lookback_days: int
    macro_lookback_days: int
    pattern_lookback_days: int = 0
    tickers: list[str]
    macro_series_ids: list[str]
    price_history: dict[str, list[PriceBar]] = Field(default_factory=dict)
    long_price_history: dict[str, list[PriceBar]] = Field(default_factory=dict)
    corporate_events: dict[str, list[CorporateEvent]] = Field(default_factory=dict)
    long_corporate_events: dict[str, list[CorporateEvent]] = Field(default_factory=dict)
    macro_series: dict[str, list[MacroObservation]] = Field(default_factory=dict)
    news: list[NewsItem] = Field(default_factory=list)
    financial_statements: dict[str, list[FinancialStatementLineItem]] = Field(default_factory=dict)


def build_snapshot(
    provider: DataProvider,
    *,
    tickers: list[str],
    macro_series_ids: list[str],
    as_of: date,
    lookback_days: int,
    macro_lookback_days: int | None = None,
    macro_series_sources: dict[str, str] | None = None,
    pattern_lookback_days: int = 0,
    financials_provider: FinancialStatementProvider | None = None,
    financials_lookback_days: int = 730,
) -> DatasetSnapshot:
    """Materialize a content-hashed snapshot of everything available as of `as_of`.

    `macro_lookback_days` (default: `lookback_days`) windows only
    `macro_series` — annual/quarterly official statistics (World Bank, UN
    SDG, CAPMAS) need a much longer window than the daily price/news/event
    window to ever contain an observation at all; using one shared window
    for both silently starved every macro series (a real, live-confirmed
    gap, not a hypothetical one).

    `macro_series_sources` (series_id -> source, e.g. `"worldbank"`),
    when given, additionally drops any macro observation not yet
    knowable as of `as_of` per `data.point_in_time.is_knowable` — closing
    a distinct gap from the window above: being inside the lookback
    *window* doesn't mean a value was actually *known* yet (an annual
    figure isn't published the instant its year ends). Omitted or an
    unmapped series id defaults to 0 assumed lag (no filtering change),
    so existing callers (tests, mock data with no real publication delay
    to model) are unaffected.

    `pattern_lookback_days` (default: 0, meaning `long_price_history` stays
    empty) is the same "one field needs its own window" situation as
    `macro_lookback_days`, this time for `historical_patterns_agent`:
    analog-matching over historical regimes needs years of daily bars,
    while every other agent's `price_history` deliberately stays the
    standard, much shorter `lookback_days` window (unchanged default
    behavior, unchanged content hash for any caller that omits this).
    `long_corporate_events` is fetched over the same wide window for the
    same reason `data/adjustments.py` always needs events alongside bars:
    a split/dividend from years ago would otherwise fall outside the
    standard `corporate_events` window and silently corrupt adjusted
    long-history returns with a fake jump.

    `financials_provider` (default: None, meaning `financial_statements`
    stays empty) mirrors `UniverseProvider`'s "separate, small, dedicated
    interface" pattern rather than growing `DataProvider`'s method set --
    see `financials.provider.FinancialStatementProvider`'s own docstring.
    Threading it through here (rather than reading it directly inside an
    agent) is what keeps `FinancialPerformanceAgent` compliant with the
    same "agents never touch a live provider directly" rule every other
    agent already follows: financial statements become part of the
    content-hashed, point-in-time snapshot like every other record type,
    not a side-channel query. `financials_lookback_days` (default 730,
    matching `meta.readiness.assess_decision_readiness`'s own window)
    windows only this field.
    """
    start = as_of - timedelta(days=lookback_days)
    macro_lookback_days = lookback_days if macro_lookback_days is None else macro_lookback_days
    macro_start = as_of - timedelta(days=macro_lookback_days)
    macro_series_sources = macro_series_sources or {}
    pattern_start = as_of - timedelta(days=pattern_lookback_days)

    price_history = {t: provider.get_price_history(t, start, as_of) for t in tickers}
    long_price_history = (
        {t: provider.get_price_history(t, pattern_start, as_of) for t in tickers}
        if pattern_lookback_days > 0
        else {}
    )
    corporate_events = {t: provider.get_corporate_events(t, start, as_of) for t in tickers}
    long_corporate_events = (
        {t: provider.get_corporate_events(t, pattern_start, as_of) for t in tickers}
        if pattern_lookback_days > 0
        else {}
    )
    macro_series = {
        s: [
            obs
            for obs in provider.get_macro_series(s, macro_start, as_of)
            if is_knowable(obs.observation_date, as_of, source=macro_series_sources.get(s))
        ]
        for s in macro_series_ids
    }
    news = provider.get_news(None, start, as_of)
    financials_start = as_of - timedelta(days=financials_lookback_days)
    financial_statements = (
        {
            t: financials_provider.get_line_items(t, financials_start, as_of)
            for t in tickers
        }
        if financials_provider is not None
        else {}
    )

    canonical = json.dumps(
        {
            "as_of": as_of.isoformat(),
            "lookback_days": lookback_days,
            "macro_lookback_days": macro_lookback_days,
            "pattern_lookback_days": pattern_lookback_days,
            "tickers": sorted(tickers),
            "macro_series_ids": sorted(macro_series_ids),
            "price_history": {
                t: [b.model_dump(mode="json") for b in bars] for t, bars in price_history.items()
            },
            "long_price_history": {
                t: [b.model_dump(mode="json") for b in bars]
                for t, bars in long_price_history.items()
            },
            "corporate_events": {
                t: [e.model_dump(mode="json") for e in events]
                for t, events in corporate_events.items()
            },
            "long_corporate_events": {
                t: [e.model_dump(mode="json") for e in events]
                for t, events in long_corporate_events.items()
            },
            "macro_series": {
                s: [o.model_dump(mode="json") for o in obs] for s, obs in macro_series.items()
            },
            "news": [n.model_dump(mode="json") for n in news],
            "financial_statements": {
                t: [i.model_dump(mode="json") for i in items]
                for t, items in financial_statements.items()
            },
        },
        sort_keys=True,
    )
    snapshot_id = "snap_" + hashlib.sha256(canonical.encode()).hexdigest()[:16]

    return DatasetSnapshot(
        id=snapshot_id,
        as_of=as_of,
        lookback_days=lookback_days,
        macro_lookback_days=macro_lookback_days,
        pattern_lookback_days=pattern_lookback_days,
        tickers=tickers,
        macro_series_ids=macro_series_ids,
        price_history=price_history,
        long_price_history=long_price_history,
        corporate_events=corporate_events,
        long_corporate_events=long_corporate_events,
        macro_series=macro_series,
        news=news,
        financial_statements=financial_statements,
    )
