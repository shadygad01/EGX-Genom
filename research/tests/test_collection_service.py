"""CollectionService end-to-end: fetch -> parse -> assess -> materialize or
withhold -> register events. Uses a stub Collector (no real fetch/parse
logic) so the test targets the service's own materialization/withholding/
idempotency behavior, not any specific collector's parsing.
"""

from datetime import date

from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, RawDocumentRepository, build_raw_document
from agx_research.collectors.service import CollectionService
from agx_research.data.mock_provider import LocalCsvDataProvider
from agx_research.data.schemas import MacroObservation, NewsItem, PriceBar
from agx_research.events.service import EventPlatform
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="stub_source",
        name="Stub Source",
        category=SourceCategory.MARKET_DATA,
        access_method=AccessMethod.CSV_DOWNLOAD,
        status=SourceStatus.IMPLEMENTED,
        reliability_score=0.9,
        freshness_score=1.0,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


class StubCollector(Collector):
    name = "StubCollector"
    version = "1.0.0"

    def __init__(self, spec, batches: dict[str, CollectionBatch], fetcher=None):
        super().__init__(spec, fetcher)
        self._batches = batches

    def fetch(self) -> list[RawDocument]:
        documents = []
        for url in sorted(self._batches):
            documents.append(
                build_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    original_url=url,
                    content_text=f"content for {url}",
                    schema_version=self.spec.schema_version,
                    license=self.spec.license,
                )
            )
        return documents

    def parse(self, document: RawDocument) -> CollectionBatch:
        for url, batch in self._batches.items():
            if document.original_url == url:
                return batch.model_copy(update={"raw_document_id": document.id})
        raise AssertionError("no batch registered for this document")


def good_batch(**overrides):
    defaults = dict(
        source_id="stub_source",
        raw_document_id="placeholder",
        price_bars=[
            PriceBar(ticker="COMI", trade_date=date(2026, 6, 1), open=10, high=11, low=9, close=10.5, volume=100)
        ],
    )
    defaults.update(overrides)
    return CollectionBatch(**defaults)


def test_high_quality_batch_is_materialized_and_written_to_csv(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    collector = StubCollector(make_spec(), {"https://x/1": good_batch()})

    result = service.run(collector, expected_records=1)

    assert result.batches_materialized == 1
    assert result.batches_withheld == 0
    assert result.price_bars_written == 1
    assert (tmp_path / "prices" / "COMI.csv").exists()

    provider = LocalCsvDataProvider(tmp_path)
    bars = provider.get_price_history("COMI", date(2026, 1, 1), date(2026, 12, 31))
    assert len(bars) == 1
    assert bars[0].close == 10.5


def test_low_quality_batch_is_withheld_not_materialized(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.95)
    # reliability 0.9 alone caps confidence below 0.95 even with clean data
    collector = StubCollector(make_spec(reliability_score=0.1), {"https://x/1": good_batch()})

    result = service.run(collector, expected_records=1)

    assert result.batches_materialized == 0
    assert result.batches_withheld == 1
    assert result.price_bars_written == 0
    assert not (tmp_path / "prices" / "COMI.csv").exists()


def test_raw_document_and_quality_assessment_recorded_even_when_withheld(tmp_path):
    raw_documents = RawDocumentRepository()
    service = CollectionService(tmp_path, raw_documents=raw_documents, min_confidence=0.95)
    collector = StubCollector(make_spec(reliability_score=0.1), {"https://x/1": good_batch()})

    result = service.run(collector, expected_records=1)

    [document_id] = [d.id for d in raw_documents.all_latest()]
    stored = raw_documents.latest(document_id)
    assert stored.version == 2  # quality_assessment step recorded
    assert len(stored.validation_history) == 1
    assert len(result.assessments) == 1


def test_reingesting_same_price_data_is_idempotent_by_date(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    collector = StubCollector(make_spec(), {"https://x/1": good_batch()})
    service.run(collector, expected_records=1)
    service.run(collector, expected_records=1)  # re-collect identical data

    provider = LocalCsvDataProvider(tmp_path)
    bars = provider.get_price_history("COMI", date(2026, 1, 1), date(2026, 12, 31))
    assert len(bars) == 1  # merged by date, not duplicated


def test_macro_observations_materialized_to_series_csv(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        macro_observations=[MacroObservation(series_id="DGS10", observation_date=date(2026, 6, 1), value=4.2)],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})

    result = service.run(collector, expected_records=1)

    assert result.macro_observations_written == 1
    provider = LocalCsvDataProvider(tmp_path)
    obs = provider.get_macro_series("DGS10", date(2026, 1, 1), date(2026, 12, 31))
    assert len(obs) == 1
    assert obs[0].value == 4.2


def test_news_items_materialized_and_registered_as_events(tmp_path):
    event_platform = EventPlatform()
    service = CollectionService(tmp_path, event_platform=event_platform, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        news_items=[
            NewsItem(published_at=date(2026, 6, 1), source="rss_generic", headline="COMI news", tickers=["COMI"])
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})

    result = service.run(collector, expected_records=1)

    assert result.news_items_written == 1
    assert result.events_registered == 1
    assert (tmp_path / "news.csv").exists()
    assert len(event_platform.repository.all_latest()) == 1


def test_mixed_batches_some_withheld_some_materialized(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.6)
    collector = StubCollector(
        make_spec(reliability_score=0.9),
        {
            "https://x/good": good_batch(),
            "https://x/bad": good_batch(parse_warnings=["a", "b", "c", "d", "e"]),
        },
    )

    result = service.run(collector, expected_records=1)

    assert result.documents_fetched == 2
    assert result.batches_materialized + result.batches_withheld == 2
    assert result.batches_materialized >= 1  # the clean batch always clears the floor


def test_materializing_a_price_bar_writes_a_traceable_provenance_record(tmp_path):
    from agx_research.collectors.provenance_index import ProvenanceIndexRepository

    provenance_index = ProvenanceIndexRepository()
    service = CollectionService(tmp_path, provenance_index=provenance_index, min_confidence=0.5)
    collector = StubCollector(make_spec(), {"https://x/1": good_batch()})

    service.run(collector, expected_records=1)

    record = provenance_index.trace("price", "COMI", date(2026, 6, 1))
    assert record is not None
    assert record.source_id == "stub_source"
    assert record.collector == "StubCollector"
    assert record.raw_document_id  # traces back to a real RawDocument id


def test_run_records_source_metrics_and_updates_registry_health_and_reputation(tmp_path):
    from agx_research.sources.registry import SourceRegistry
    from agx_research.sources.reputation import SourceMetricsRepository
    from agx_research.sources.spec import HealthStatus

    registry = SourceRegistry()
    registry.add(make_spec())
    metrics_repo = SourceMetricsRepository()
    service = CollectionService(
        tmp_path, registry=registry, metrics=metrics_repo, min_confidence=0.5
    )
    collector = StubCollector(make_spec(), {"https://x/1": good_batch()})

    service.run(collector, expected_records=1)

    metrics = metrics_repo.latest("stub_source")
    assert metrics is not None
    assert metrics.runs_total == 1
    updated_spec = registry.latest("stub_source")
    assert updated_spec.health_status == HealthStatus.HEALTHY
    assert updated_spec.data_quality_score is not None


def test_parser_exception_is_withheld_and_recorded_not_propagated(tmp_path):
    class RaisingCollector(StubCollector):
        def parse(self, document):
            raise ValueError("boom")

    service = CollectionService(tmp_path, min_confidence=0.5)
    collector = RaisingCollector(make_spec(), {"https://x/1": good_batch()})

    result = service.run(collector, expected_records=1)

    assert result.batches_withheld == 1
    assert result.batches_materialized == 0
