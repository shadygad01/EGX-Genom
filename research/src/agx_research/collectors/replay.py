"""Historical Replay Engine: rebuild materialized data (and, transitively,
the knowledge that depends on it) from the Raw Archive alone, without a
single new network fetch. Thin orchestration over `ArchiveReplayCollector` +
`CollectionService.run()` -- the real replay mechanics already live there;
this module is the "replay everything we've ever collected" entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agx_research.collectors.archive_replay import ArchiveReplayCollector
from agx_research.collectors.base import Collector
from agx_research.collectors.raw import RawDocumentRepository
from agx_research.collectors.service import CollectionRunResult, CollectionService


@dataclass
class ReplayReport:
    results: dict[str, CollectionRunResult] = field(default_factory=dict)
    skipped_sources: list[str] = field(default_factory=list)  # no archived documents at all


class HistoricalReplayEngine:
    def __init__(self, raw_documents: RawDocumentRepository, service: CollectionService):
        self.raw_documents = raw_documents
        self.service = service

    def replay_source(
        self, real_collector: Collector, *, expected_records: int, since=None
    ) -> CollectionRunResult:
        replay_collector = ArchiveReplayCollector(real_collector, self.raw_documents, since=since)
        return self.service.run(replay_collector, expected_records=expected_records)

    def replay_all(
        self, collectors_by_source_id: dict[str, Collector], *, expected_records: int = 1
    ) -> ReplayReport:
        """Rebuild every source with a live collector wired in. Sources with no
        archived documents are reported as skipped, not silently dropped.
        """
        report = ReplayReport()
        archived_source_ids = {d.source_id for d in self.raw_documents.all_latest()}
        for source_id, collector in collectors_by_source_id.items():
            if source_id not in archived_source_ids:
                report.skipped_sources.append(source_id)
                continue
            report.results[source_id] = self.replay_source(
                collector, expected_records=expected_records
            )
        return report
