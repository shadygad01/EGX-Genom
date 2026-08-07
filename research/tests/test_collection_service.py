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
from agx_research.data.schemas import CorporateEvent, MacroObservation, NewsItem, PriceBar
from agx_research.events.service import EventPlatform
from agx_research.financials.schema import FinancialStatementLineItem
from agx_research.sources.spec import (
    AccessMethod,
    EvidenceTier,
    SourceCategory,
    SourceSpec,
    SourceStatus,
)
from agx_research.universe.constituent import IndexConstituent


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


def test_reingesting_identical_price_data_does_not_regrow_provenance_index(tmp_path):
    """A full-history source (e.g. Yahoo's `range=max` leg inside
    `EgxCompositePriceCollector`) re-sends every historical bar on every
    run, and `egx-collector.timer` fires every minute -- without this
    unchanged-value guard, `ProvenanceIndexRepository` grew by one new
    version per historical bar on every single run regardless of whether
    anything actually changed (a real, measured unbounded-growth defect;
    see `scripts/profile_egx_collector_memory.py`'s `growth --static`
    scenario)."""
    from agx_research.collectors.provenance_index import ProvenanceIndexRepository

    provenance_index = ProvenanceIndexRepository()
    service = CollectionService(tmp_path, provenance_index=provenance_index, min_confidence=0.5)
    collector = StubCollector(make_spec(), {"https://x/1": good_batch()})
    service.run(collector, expected_records=1)
    service.run(collector, expected_records=1)  # re-collect byte-identical data

    record = provenance_index.trace("price", "COMI", date(2026, 6, 1))
    assert record.version == 1  # unchanged value, never re-traced
    assert len(provenance_index.history(record.id)) == 1


def test_reingesting_changed_price_data_is_still_traced(tmp_path):
    """The guard above must only suppress *identical* re-materialization --
    a genuinely corrected/changed value must still get a new provenance
    version, same as before this change."""
    from agx_research.collectors.provenance_index import ProvenanceIndexRepository

    provenance_index = ProvenanceIndexRepository()
    service = CollectionService(tmp_path, provenance_index=provenance_index, min_confidence=0.5)
    collector = StubCollector(make_spec(), {"https://x/1": good_batch()})
    service.run(collector, expected_records=1)

    corrected = StubCollector(make_spec(), {"https://x/1": good_batch(
        price_bars=[
            PriceBar(ticker="COMI", trade_date=date(2026, 6, 1), open=10, high=11, low=9, close=11.0, volume=100)
        ],
    )})
    service.run(corrected, expected_records=1)

    record = provenance_index.trace("price", "COMI", date(2026, 6, 1))
    assert record.version == 2  # close actually changed (10.5 -> 11.0)


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


def test_discovery_tier_news_never_reaches_news_csv_or_the_event_platform(tmp_path):
    # GDELT (and any future DISCOVERY-tier source) must never independently
    # become evidence -- see sources.spec.EvidenceTier.
    event_platform = EventPlatform()
    service = CollectionService(tmp_path, event_platform=event_platform, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        news_items=[
            NewsItem(published_at=date(2026, 6, 1), source="gdelt", headline="COMI mentioned", tickers=["COMI"])
        ],
    )
    collector = StubCollector(make_spec(evidence_tier=EvidenceTier.DISCOVERY), {"https://x/1": batch})

    result = service.run(collector, expected_records=1)

    assert result.news_items_written == 0
    assert result.news_discovery_items_written == 1
    assert result.events_registered == 0
    assert not (tmp_path / "news.csv").exists()
    assert (tmp_path / "news_discovery.csv").exists()
    assert len(event_platform.repository.all_latest()) == 0


def test_arabic_news_is_persisted_as_utf8(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    headline = "البورصة المصرية ترتفع في ختام التعاملات"
    batch = good_batch(
        price_bars=[],
        news_items=[
            NewsItem(
                published_at=date(2026, 7, 26),
                source="alborsa",
                headline=headline,
                tickers=["COMI"],
            )
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/ar": batch})

    result = service.run(collector, expected_records=1)

    assert result.news_items_written == 1
    assert headline in (tmp_path / "news.csv").read_text(encoding="utf-8")
    [stored] = LocalCsvDataProvider(tmp_path).get_news(
        "COMI", date(2026, 7, 26), date(2026, 7, 26)
    )
    assert stored.headline == headline


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


class _ProviderTaggedCollector(StubCollector):
    """A composite collector where every document is attributable to one
    provider leg, mirroring `EgxCompositePriceCollector.provider_for_document`.
    """

    def __init__(self, spec, batches, provider_by_url):
        super().__init__(spec, batches)
        self._provider_by_url = provider_by_url

    def provider_for_document(self, document: RawDocument) -> str | None:
        return self._provider_by_url.get(document.original_url)


def test_provider_leg_health_and_reputation_are_measured_directly(tmp_path):
    """Provider legs wired inside a composite collector (`SourceSpec.
    integrated_via`, e.g. yahoo_finance/stockanalysis/mubasher inside
    `EgxCompositePriceCollector`) must have their own health/reputation
    measured from the documents actually attributed to them -- not stay
    `HealthStatus.UNKNOWN`/`data_quality_score=None` forever regardless of
    how much real traffic they served, which is misleading in the Source
    Intelligence dashboard.
    """
    from agx_research.sources.registry import SourceRegistry
    from agx_research.sources.reputation import SourceMetricsRepository
    from agx_research.sources.spec import HealthStatus

    registry = SourceRegistry()
    registry.add(make_spec())
    registry.add(make_spec(id="good_provider", integrated_via="stub_source"))
    registry.add(make_spec(id="bad_provider", integrated_via="stub_source"))
    metrics_repo = SourceMetricsRepository()
    service = CollectionService(
        tmp_path, registry=registry, metrics=metrics_repo, min_confidence=0.5
    )
    collector = _ProviderTaggedCollector(
        make_spec(),
        {
            "https://x/good": good_batch(),
            "https://x/bad": good_batch(price_bars=[], parse_warnings=["nothing usable"]),
        },
        provider_by_url={"https://x/good": "good_provider", "https://x/bad": "bad_provider"},
    )

    service.run(collector, expected_records=1)

    good_metrics = metrics_repo.latest("good_provider")
    assert good_metrics is not None
    assert good_metrics.runs_total == 1
    good_spec = registry.latest("good_provider")
    assert good_spec.health_status == HealthStatus.HEALTHY
    assert good_spec.data_quality_score is not None

    bad_metrics = metrics_repo.latest("bad_provider")
    assert bad_metrics is not None
    assert bad_metrics.materialized_total == 0  # zero yield, never materialized
    bad_spec = registry.latest("bad_provider")
    assert bad_spec.health_status != HealthStatus.UNKNOWN  # measured, not left unknown

    # The parent composite's own metrics are unaffected in count by the
    # per-provider bookkeeping -- one run per document, same as before.
    parent_metrics = metrics_repo.latest("stub_source")
    assert parent_metrics.runs_total == 2


class _FetchRaisingCollector(StubCollector):
    """`fetch()` always raises -- simulates a real connection/timeout
    failure (e.g. FRED's `fredgraph.csv` timing out), never reaching
    `parse()` at all."""

    def fetch(self):
        raise TimeoutError("simulated: connection timed out")


def test_fetch_failure_is_recorded_in_metrics_and_health_not_silently_dropped(tmp_path):
    """The real bug this fixes: previously, an exception from `fetch()`
    propagated straight out of `CollectionService.run()` before any metrics/
    health bookkeeping ran, so a source whose `fetch()` always raised never
    accumulated `consecutive_failures` and could never reach
    `HealthStatus.DOWN` no matter how many times it failed.
    """
    import pytest

    from agx_research.sources.registry import SourceRegistry
    from agx_research.sources.reputation import SourceMetricsRepository
    from agx_research.sources.spec import HealthStatus

    registry = SourceRegistry()
    registry.add(make_spec())
    metrics_repo = SourceMetricsRepository()
    service = CollectionService(
        tmp_path, registry=registry, metrics=metrics_repo, min_confidence=0.5
    )
    collector = _FetchRaisingCollector(make_spec(), {})

    for _ in range(3):
        with pytest.raises(TimeoutError):
            service.run(collector, expected_records=1)

    metrics = metrics_repo.latest("stub_source")
    assert metrics is not None
    assert metrics.runs_total == 3
    assert metrics.consecutive_failures == 3
    updated_spec = registry.latest("stub_source")
    assert updated_spec.health_status == HealthStatus.DOWN


class _FakeTimedFetcher:
    """Stands in for `HttpFetcher`: only the `request_latencies` list matters
    to `CollectionService`, which reads new entries appended during
    `Collector.fetch()` to derive a real (never fabricated) latency for
    sources that actually issue timed requests -- see
    `collectors.fetcher.HttpFetcher`."""

    def __init__(self):
        self.request_latencies: list[float] = []


class _TimedStubCollector(StubCollector):
    """Like `StubCollector`, but simulates issuing two timed HTTP requests
    during `fetch()`, the way a real `HttpFetcher`-backed collector would."""

    def fetch(self):
        self.fetcher.request_latencies.extend([1.0, 3.0])
        return super().fetch()


def test_real_fetch_latency_is_recorded_into_source_metrics(tmp_path):
    from agx_research.sources.reputation import SourceMetricsRepository

    metrics_repo = SourceMetricsRepository()
    fetcher = _FakeTimedFetcher()
    service = CollectionService(tmp_path, metrics=metrics_repo, min_confidence=0.5)
    collector = _TimedStubCollector(make_spec(), {"https://x/1": good_batch()}, fetcher=fetcher)

    service.run(collector, expected_records=1)

    metrics = metrics_repo.latest("stub_source")
    assert metrics.latency_count == 1
    assert metrics.latency_seconds_sum == 2.0  # average of [1.0, 3.0]


def test_no_latency_recorded_when_fetcher_never_timed_a_request(tmp_path):
    from agx_research.sources.reputation import SourceMetricsRepository

    metrics_repo = SourceMetricsRepository()
    service = CollectionService(tmp_path, metrics=metrics_repo, min_confidence=0.5)
    collector = StubCollector(make_spec(), {"https://x/1": good_batch()})  # default HttpFetcher, unused

    service.run(collector, expected_records=1)

    metrics = metrics_repo.latest("stub_source")
    assert metrics.latency_count == 0  # never fabricated when nothing was actually timed


def test_corporate_events_materialized_to_csv(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        corporate_events=[
            CorporateEvent(
                ticker="COMI", event_date=date(2026, 6, 1),
                event_type="DIVIDEND", description="COMI declares dividend",
            )
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})

    result = service.run(collector, expected_records=1)

    assert result.corporate_events_written == 1
    provider = LocalCsvDataProvider(tmp_path)
    events = provider.get_corporate_events("COMI", date(2026, 1, 1), date(2026, 12, 31))
    assert len(events) == 1
    assert events[0].event_type == "DIVIDEND"


def test_corporate_events_do_not_directly_register_events(tmp_path):
    # events_from_corporate_events (events.adapters), fed by a DatasetSnapshot
    # reading corporate_events.csv, is the single place these become
    # registered Events -- CollectionService materializes only, so the same
    # disclosure is never registered through two separate paths.
    event_platform = EventPlatform()
    service = CollectionService(tmp_path, event_platform=event_platform, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        corporate_events=[
            CorporateEvent(
                ticker="COMI", event_date=date(2026, 6, 1),
                event_type="DIVIDEND", description="COMI declares dividend",
            )
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})

    service.run(collector, expected_records=1)

    assert len(event_platform.repository.all_latest()) == 0


def test_index_constituents_materialized_to_csv(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        index_constituents=[
            IndexConstituent(
                index="EGX30", ticker="COMI", company_name="Commercial International Bank",
                as_of_date=date(2026, 6, 1),
            )
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})

    result = service.run(collector, expected_records=1)

    assert result.index_constituents_written == 1
    from agx_research.universe.collected import CollectedUniverseProvider

    provider = CollectedUniverseProvider(tmp_path, index="EGX30")
    assert provider.constituents(date(2026, 6, 14)) == {"COMI": "Commercial International Bank"}


def test_reingesting_same_index_constituents_is_idempotent(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        index_constituents=[
            IndexConstituent(
                index="EGX30", ticker="COMI", company_name="Commercial International Bank",
                as_of_date=date(2026, 6, 1),
            )
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})
    service.run(collector, expected_records=1)
    service.run(collector, expected_records=1)

    path = tmp_path / "universe" / "EGX30.csv"
    rows = path.read_text().strip().splitlines()
    assert len(rows) == 2  # header + one row, not duplicated


def test_financial_statement_line_items_materialized_to_csv(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        financial_statement_line_items=[
            FinancialStatementLineItem(
                ticker="COMI", period_end_date=date(2026, 6, 30), period_type="QUARTERLY",
                statement_type="INCOME_STATEMENT", line_item="revenue", value=1_000_000.0,
            )
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})

    result = service.run(collector, expected_records=1)

    assert result.financial_statement_line_items_written == 1
    from agx_research.financials.collected import CollectedFinancialStatementProvider

    provider = CollectedFinancialStatementProvider(tmp_path)
    items = provider.get_line_items("COMI", date(2026, 1, 1), date(2026, 12, 31))
    assert len(items) == 1
    assert items[0].line_item == "revenue"
    assert items[0].value == 1_000_000.0


def test_reingesting_same_financial_statement_line_items_is_idempotent(tmp_path):
    service = CollectionService(tmp_path, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        financial_statement_line_items=[
            FinancialStatementLineItem(
                ticker="COMI", period_end_date=date(2026, 6, 30), period_type="QUARTERLY",
                statement_type="INCOME_STATEMENT", line_item="revenue", value=1_000_000.0,
            )
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})
    service.run(collector, expected_records=1)
    service.run(collector, expected_records=1)

    path = tmp_path / "financial_statements" / "COMI.csv"
    rows = path.read_text().strip().splitlines()
    assert len(rows) == 2  # header + one row, not duplicated


def test_sector_classifications_materialized_and_readable_via_collected_provider(tmp_path):
    from agx_research.universe.sector import CollectedSectorProvider, SectorClassification

    service = CollectionService(tmp_path, min_confidence=0.5)
    batch = good_batch(
        price_bars=[],
        sector_classifications=[
            SectorClassification(
                ticker="ARCC", sector="Building Materials",
                source_id="chief_egx_financials", observed_date=date(2026, 8, 2),
            )
        ],
    )
    collector = StubCollector(make_spec(), {"https://x/1": batch})

    result = service.run(collector, expected_records=1)

    assert result.sector_classifications_written == 1
    provider = CollectedSectorProvider(tmp_path)
    assert provider.sector_of("ARCC", date(2026, 8, 2)) == "Building Materials"
    # A ticker nothing has collected falls back to the static placeholder,
    # never worse coverage than before this provider existed.
    assert provider.sector_of("COMI", date(2026, 8, 2)) == "Banks"
    assert provider.sector_of("TOTALLY_UNKNOWN", date(2026, 8, 2)) is None


def test_reingesting_same_sector_classification_is_idempotent_and_latest_wins(tmp_path):
    from agx_research.universe.sector import CollectedSectorProvider, SectorClassification

    service = CollectionService(tmp_path, min_confidence=0.5)
    collector = StubCollector(make_spec(), {"https://x/1": good_batch(
        price_bars=[],
        sector_classifications=[
            SectorClassification(
                ticker="ARCC", sector="Building Materials",
                source_id="chief_egx_financials", observed_date=date(2026, 8, 2),
            )
        ],
    )})
    service.run(collector, expected_records=1)
    service.run(collector, expected_records=1)

    path = tmp_path / "sectors" / "sector_membership.csv"
    rows = path.read_text().strip().splitlines()
    assert len(rows) == 2  # header + one row, not duplicated

    provider = CollectedSectorProvider(tmp_path)
    assert provider.sector_of("ARCC", date(2026, 8, 2)) == "Building Materials"


def test_sector_membership_csv_never_lands_inside_universe_dir(tmp_path):
    """Real, live-evidenced regression (2026-08-02 production incident):
    `CollectedUniverseProvider.constituents()` globs *every* CSV under
    `universe/` and requires an `as_of_date` column -- a sector CSV with a
    different schema sitting there crashed the entire live pipeline with
    `KeyError: 'as_of_date'` at collector_execution and every stage after
    it. Collecting both real index constituents and real sector data into
    the same data_dir must never break universe lookup again."""
    from agx_research.universe.collected import CollectedUniverseProvider
    from agx_research.universe.constituent import IndexConstituent
    from agx_research.universe.sector import SectorClassification

    service = CollectionService(tmp_path, min_confidence=0.5)
    service.run(StubCollector(make_spec(), {"https://x/1": good_batch(
        price_bars=[],
        index_constituents=[
            IndexConstituent(
                index="EGX30", ticker="ARCC", company_name="Arabian Cement",
                as_of_date=date(2026, 8, 2),
            )
        ],
    )}), expected_records=1)
    service.run(StubCollector(make_spec(), {"https://x/2": good_batch(
        price_bars=[],
        sector_classifications=[
            SectorClassification(
                ticker="ARCC", sector="Building Materials",
                source_id="chief_egx_financials", observed_date=date(2026, 8, 2),
            )
        ],
    )}), expected_records=1)

    assert not (tmp_path / "universe" / "sector_membership.csv").exists()
    assert CollectedUniverseProvider(tmp_path).constituents(date(2026, 8, 2)) == {
        "ARCC": "Arabian Cement"
    }


def test_parser_exception_is_withheld_and_recorded_not_propagated(tmp_path):
    class RaisingCollector(StubCollector):
        def parse(self, document):
            raise ValueError("boom")

    service = CollectionService(tmp_path, min_confidence=0.5)
    collector = RaisingCollector(make_spec(), {"https://x/1": good_batch()})

    result = service.run(collector, expected_records=1)

    assert result.batches_withheld == 1
    assert result.batches_materialized == 0
