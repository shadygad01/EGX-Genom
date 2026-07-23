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

from agx_research.data.provider import DataProvider
from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar


class DatasetSnapshot(BaseModel):
    id: str
    as_of: date
    lookback_days: int
    tickers: list[str]
    macro_series_ids: list[str]
    price_history: dict[str, list[PriceBar]] = Field(default_factory=dict)
    corporate_events: dict[str, list[CorporateEvent]] = Field(default_factory=dict)
    macro_series: dict[str, list[MacroObservation]] = Field(default_factory=dict)
    news: list[NewsItem] = Field(default_factory=list)


def build_snapshot(
    provider: DataProvider,
    *,
    tickers: list[str],
    macro_series_ids: list[str],
    as_of: date,
    lookback_days: int,
) -> DatasetSnapshot:
    """Materialize a content-hashed snapshot of everything available as of `as_of`."""
    start = as_of - timedelta(days=lookback_days)

    price_history = {t: provider.get_price_history(t, start, as_of) for t in tickers}
    corporate_events = {t: provider.get_corporate_events(t, start, as_of) for t in tickers}
    macro_series = {s: provider.get_macro_series(s, start, as_of) for s in macro_series_ids}
    news = provider.get_news(None, start, as_of)

    canonical = json.dumps(
        {
            "as_of": as_of.isoformat(),
            "lookback_days": lookback_days,
            "tickers": sorted(tickers),
            "macro_series_ids": sorted(macro_series_ids),
            "price_history": {
                t: [b.model_dump(mode="json") for b in bars] for t, bars in price_history.items()
            },
            "corporate_events": {
                t: [e.model_dump(mode="json") for e in events]
                for t, events in corporate_events.items()
            },
            "macro_series": {
                s: [o.model_dump(mode="json") for o in obs] for s, obs in macro_series.items()
            },
            "news": [n.model_dump(mode="json") for n in news],
        },
        sort_keys=True,
    )
    snapshot_id = "snap_" + hashlib.sha256(canonical.encode()).hexdigest()[:16]

    return DatasetSnapshot(
        id=snapshot_id,
        as_of=as_of,
        lookback_days=lookback_days,
        tickers=tickers,
        macro_series_ids=macro_series_ids,
        price_history=price_history,
        corporate_events=corporate_events,
        macro_series=macro_series,
        news=news,
    )
