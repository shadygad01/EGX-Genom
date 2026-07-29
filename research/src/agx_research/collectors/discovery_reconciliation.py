"""Discovery-tier news reconciliation: the only path that promotes a
DISCOVERY-tier source's news item into news.csv/evidence.

See `sources.spec.EvidenceTier`'s docstring for the full rationale: a
DISCOVERY-tier collector (GDELT today) never writes to news.csv or
registers an Event directly -- `collectors.service.CollectionService`
already enforces that structurally, writing its items to
news_discovery.csv instead. This module is the single reconciliation
step: a discovery candidate is promoted only once a PRIMARY-tier source
independently reports *something* about the same ticker within
`window_days` of the same date -- "GDELT must resolve to a primary
source before it counts as evidence" is a real, checkable condition here,
not a downstream filter an agent could bypass.

A promoted row keeps its own source/headline (still attributed to GDELT,
still traceable via provenance) -- promotion means "corroborated by an
independent primary-source report nearby in time," not "rewritten as if
a primary source said this." Matching is by ticker + date proximity only
(no headline/content comparison), a declared heuristic like the
codebase's other keyword-based classifiers -- it cannot tell whether the
primary source's report and the GDELT pickup are about the *same* fact,
only that a primary source was independently covering the same company
around the same time.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from agx_research.collectors.service import append_news
from agx_research.data.schemas import NewsItem

_FIELDNAMES = ["date", "source", "headline", "tickers", "body"]


@dataclass
class ReconciliationResult:
    candidates_checked: int
    promoted: int
    still_pending: int


def _read_news_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def reconcile_discovery_news(data_dir: Path, *, window_days: int = 2) -> ReconciliationResult:
    """Promote DISCOVERY-tier candidates in news_discovery.csv into
    news.csv, one at a time, whenever a PRIMARY-tier row already in
    news.csv mentions at least one of the same tickers within
    `window_days` of the candidate's date.

    A candidate with no resolved ticker can never be promoted -- there is
    nothing to match it against, and "resolve to a primary source" is
    meaningless without a shared entity.
    """
    discovery_path = data_dir / "news_discovery.csv"
    news_path = data_dir / "news.csv"
    discovery_rows = _read_news_csv(discovery_path)
    if not discovery_rows:
        return ReconciliationResult(candidates_checked=0, promoted=0, still_pending=0)

    primary_rows = _read_news_csv(news_path)
    # {ticker: dates a PRIMARY source reported *something* about it} --
    # a real primary-source report, not what it said.
    primary_dates_by_ticker: dict[str, list[date]] = {}
    for row in primary_rows:
        row_date = date.fromisoformat(row["date"])
        for ticker in (row["tickers"] or "").split("|"):
            if ticker:
                primary_dates_by_ticker.setdefault(ticker, []).append(row_date)

    promoted_items: list[NewsItem] = []
    remaining_rows: list[dict] = []
    for row in discovery_rows:
        tickers = [t for t in (row["tickers"] or "").split("|") if t]
        row_date = date.fromisoformat(row["date"])
        matched = False
        for ticker in tickers:
            for primary_date in primary_dates_by_ticker.get(ticker, []):
                if abs((row_date - primary_date).days) <= window_days:
                    matched = True
                    break
            if matched:
                break
        if matched:
            promoted_items.append(
                NewsItem(
                    published_at=row_date,
                    source=row["source"],
                    headline=row["headline"],
                    tickers=tickers,
                    body=row["body"] or None,
                )
            )
        else:
            remaining_rows.append(row)

    if promoted_items:
        append_news(data_dir, promoted_items)
        # Promoted rows graduate out of the discovery pool -- they now
        # live in news.csv and must not be re-checked (or re-promoted)
        # forever.
        with discovery_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
            writer.writeheader()
            for row in remaining_rows:
                writer.writerow(row)

    return ReconciliationResult(
        candidates_checked=len(discovery_rows),
        promoted=len(promoted_items),
        still_pending=len(remaining_rows),
    )
