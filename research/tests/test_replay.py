"""HistoricalReplayEngine: rebuild materialized data from the Raw Archive
alone, with no new fetch, and correctly upgrade output when a collector's
parser changes -- the two guarantees `docs/DATA_ACQUISITION.md`'s Historical
Replay requirement is about.
"""

from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, RawDocumentRepository, build_raw_document
from agx_research.collectors.replay import HistoricalReplayEngine
from agx_research.collectors.service import CollectionService
from agx_research.data.mock_provider import LocalCsvDataProvider
from agx_research.data.schemas import PriceBar
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="replay_source", name="Replay Source", category=SourceCategory.MARKET_DATA,
        access_method=AccessMethod.CSV_DOWNLOAD, status=SourceStatus.IMPLEMENTED,
        reliability_score=0.9, freshness_score=1.0,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


class RecordingCollector(Collector):
    """Real fetch behavior (builds+stores documents via the service on first
    run) and a `parse` whose behavior can be swapped between two "versions"
    to simulate fixing a parser bug.
    """

    name = "RecordingCollector"

    def __init__(self, spec, urls: list[str], version: str = "1.0.0", fetcher=None):
        super().__init__(spec, fetcher)
        self.version = version
        self.urls = urls

    def fetch(self) -> list[RawDocument]:
        return [
            build_raw_document(
                source_id=self.spec.id, collector=self.name, collector_version=self.version,
                original_url=url, content_text=f"payload:{url}",
                schema_version=self.spec.schema_version, license=self.spec.license,
            )
            for url in self.urls
        ]

    def parse(self, document: RawDocument) -> CollectionBatch:
        if self.version == "1.0.0":
            # the "buggy" parser: drops the record entirely
            return CollectionBatch(source_id=document.source_id, raw_document_id=document.id)
        # the "fixed" parser: correctly extracts a price bar
        return CollectionBatch(
            source_id=document.source_id, raw_document_id=document.id,
            price_bars=[
                PriceBar(
                    ticker="COMI", trade_date=date(2026, 6, 1),
                    open=10, high=11, low=9, close=10.5, volume=100,
                )
            ],
        )


def test_replay_source_reports_zero_documents_when_nothing_archived(tmp_path):
    raw_documents = RawDocumentRepository()
    service = CollectionService(tmp_path, raw_documents=raw_documents, min_confidence=0.5)
    engine = HistoricalReplayEngine(raw_documents, service)
    collector = RecordingCollector(make_spec(), urls=[], version="2.0.0")

    result = engine.replay_source(collector, expected_records=1)
    assert result.documents_fetched == 0


def test_replay_rebuilds_data_with_fixed_parser_from_same_archived_bytes(tmp_path):
    raw_documents = RawDocumentRepository()
    service = CollectionService(tmp_path, raw_documents=raw_documents, min_confidence=0.5)

    # First run: buggy parser produces nothing (as if the real collector
    # shipped with a bug).
    buggy = RecordingCollector(make_spec(), urls=["https://x/1"], version="1.0.0")
    first = service.run(buggy, expected_records=1)
    assert first.price_bars_written == 0
    assert not (tmp_path / "prices" / "COMI.csv").exists()

    # No new fetch happens for replay -- the fixed collector only parses the
    # exact same archived RawDocument.
    fixed = RecordingCollector(make_spec(), urls=["https://x/1"], version="2.0.0")
    engine = HistoricalReplayEngine(raw_documents, service)
    replayed = engine.replay_source(fixed, expected_records=1)

    assert replayed.documents_fetched == 1
    assert replayed.price_bars_written == 1
    provider = LocalCsvDataProvider(tmp_path)
    bars = provider.get_price_history("COMI", date(2026, 1, 1), date(2026, 12, 31))
    assert len(bars) == 1
    assert bars[0].close == 10.5


def test_replay_does_not_duplicate_raw_document_versions(tmp_path):
    raw_documents = RawDocumentRepository()
    service = CollectionService(tmp_path, raw_documents=raw_documents, min_confidence=0.5)
    collector = RecordingCollector(make_spec(), urls=["https://x/1"], version="2.0.0")
    service.run(collector, expected_records=1)

    [doc_id] = [d.id for d in raw_documents.all_latest()]
    versions_before = len(raw_documents.history(doc_id))

    engine = HistoricalReplayEngine(raw_documents, service)
    engine.replay_source(collector, expected_records=1)

    versions_after = len(raw_documents.history(doc_id))
    assert versions_after == versions_before + 1  # only the new validation step, no re-add


def test_replay_all_reports_sources_with_no_archive_as_skipped(tmp_path):
    raw_documents = RawDocumentRepository()
    service = CollectionService(tmp_path, raw_documents=raw_documents, min_confidence=0.5)
    collector = RecordingCollector(make_spec(), urls=["https://x/1"], version="2.0.0")
    service.run(collector, expected_records=1)

    other_spec = make_spec(id="never_collected")
    other_collector = RecordingCollector(other_spec, urls=[], version="2.0.0")

    engine = HistoricalReplayEngine(raw_documents, service)
    report = engine.replay_all(
        {"replay_source": collector, "never_collected": other_collector}, expected_records=1
    )

    assert "replay_source" in report.results
    assert "never_collected" in report.skipped_sources
