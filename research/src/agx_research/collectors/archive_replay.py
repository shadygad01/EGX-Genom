"""ArchiveReplayCollector: "Archive Replay" as a first-class collector type.

Its `fetch()` returns documents already sitting in a `RawDocumentRepository`
instead of hitting the network, and its `parse()` delegates to whatever real
collector currently owns that source's parsing logic. Because it still
implements the plain `Collector` interface, `CollectionService.run()` needs
no special case to replay history -- feeding an `ArchiveReplayCollector` into
`run()` re-parses every stored document with today's parser and re-runs
quality assessment/materialization/provenance exactly as a live run would.

This is what makes "changing parsers must never require recollecting data"
(`docs/DATA_ACQUISITION.md`'s Historical Replay requirement) true: fix a bug
in `StooqPriceCollector.parse`, bump its `collector_version`, then replay
every historical Stooq `RawDocument` through the fixed parser -- no new
fetch, same archived bytes.
"""

from __future__ import annotations

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, RawDocumentRepository


class ArchiveReplayCollector(Collector):
    name = "ArchiveReplayCollector"
    version = "1.0.0"

    def __init__(
        self,
        real_collector: Collector,
        raw_documents: RawDocumentRepository,
        *,
        since=None,
    ):
        # Deliberately skip Collector.__init__'s own IMPLEMENTED gate re-check
        # here: real_collector's construction already enforced it, and replay
        # must work even if a source's live status later changes (e.g. a key
        # expired) -- history that was already legitimately collected stays
        # replayable regardless of today's collectability.
        self.spec = real_collector.spec
        self.fetcher = real_collector.fetcher
        self.real_collector = real_collector
        self.raw_documents = raw_documents
        self.since = since

    def fetch(self) -> list[RawDocument]:
        documents = [
            d for d in self.raw_documents.all_latest() if d.source_id == self.spec.id
        ]
        if self.since is not None:
            documents = [d for d in documents if d.fetched_at >= self.since]
        return sorted(documents, key=lambda d: d.fetched_at)

    def parse(self, document: RawDocument) -> CollectionBatch:
        return self.real_collector.parse(document)
