"""The Collector contract: fetch raw documents, parse canonical candidates.

No source-specific logic exists outside a collector, and collectors only
*produce candidates* — canonical `PriceBar`/`MacroObservation`/`NewsItem`
values in a `CollectionBatch`, each traceable to its `RawDocument`. What
happens next (quality scoring, materialization, Event Platform
registration with identity/dedup/corroboration/conflict/lifecycle/graph)
is the platform's job, never the collector's.

`fetch` is separated from `parse` so parsing is a pure function of a
RawDocument — replayable forever from stored raw bytes, and testable
offline against recorded-format fixtures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel, Field

from agx_research.collectors.fetcher import HttpFetcher
from agx_research.collectors.raw import RawDocument
from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar
from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.sources.spec import SourceSpec, SourceStatus
from agx_research.universe.constituent import IndexConstituent
from agx_research.universe.sector import SectorClassification


class CollectionBatch(BaseModel):
    source_id: str
    raw_document_id: str
    price_bars: list[PriceBar] = Field(default_factory=list)
    macro_observations: list[MacroObservation] = Field(default_factory=list)
    news_items: list[NewsItem] = Field(default_factory=list)
    corporate_events: list[CorporateEvent] = Field(default_factory=list)
    index_constituents: list[IndexConstituent] = Field(default_factory=list)
    financial_statement_line_items: list[FinancialStatementLineItem] = Field(default_factory=list)
    # A collector's own line_item vocabulary for one ticker occasionally needs
    # correcting (e.g. a generic label discovered to conflate two distinct
    # accounting concepts). `_write_financial_statement_line_items` merges by
    # (period_end_date, statement_type, line_item), so a renamed line_item
    # would otherwise leave the old key behind forever as stale, unrefreshed
    # data. Declaring the old (period_end_date, statement_type, line_item)
    # key here drops it from storage instead -- scoped to exactly the ticker/
    # period this batch already covers, never a blanket wipe of history a
    # different collector (or an earlier run) contributed.
    superseded_line_items: list[tuple[date, str, str]] = Field(default_factory=list)
    sector_classifications: list[SectorClassification] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)


class Collector(ABC):
    name: str
    version: str

    def __init__(self, spec: SourceSpec, fetcher: HttpFetcher | None = None):
        if spec.status != SourceStatus.IMPLEMENTED:
            raise ValueError(
                f"Source {spec.id} has status {spec.status.value}; only IMPLEMENTED "
                "sources may be collected (NEEDS_KEY/TOS_REVIEW/PLANNED block by design)."
            )
        self.spec = spec
        self.fetcher = fetcher or HttpFetcher()

    @abstractmethod
    def fetch(self) -> list[RawDocument]:
        """Fetch the source and wrap every payload as a RawDocument."""

    @abstractmethod
    def parse(self, document: RawDocument) -> CollectionBatch:
        """Pure function of a RawDocument -> canonical candidates. Replayable."""
