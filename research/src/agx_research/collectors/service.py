"""CollectionService: run a Collector, score quality, materialize, register.

The end-to-end path a real source follows:

    Collector.fetch() -> RawDocument(s) [persisted in RawDocumentRepository]
        -> Collector.parse() -> CollectionBatch
        -> assess_quality() -> QualityAssessment
        -> if confidence_score >= min_confidence:
               materialize into the local CSV layout (LocalCsvDataProvider
               reads it immediately afterward -- no new provider needed)
        -> derive candidate Events from the batch's own records
           (source-tagged, not routed through DatasetSnapshot adapters)
        -> EventPlatform.register() -- identity, dedup, corroboration,
           conflict resolution, lifecycle, all exactly as for any other event

A batch scoring below the confidence floor is recorded (via its
RawDocument's validation_history) but never materialized or registered —
"no downstream system may ignore data quality" means low-quality data
doesn't quietly become knowledge, it's visibly withheld.

A source whose `SourceSpec.evidence_tier` is DISCOVERY (GDELT today) never
reaches news.csv/the Event Platform through this path at all, regardless
of confidence score: its news items go to news_discovery.csv instead, and
`collectors.discovery_reconciliation.reconcile_discovery_news()` is the
only way one is promoted into news.csv, once a PRIMARY source
independently reports something about the same ticker nearby in time.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from agx_research.collectors.base import Collector
from agx_research.collectors.provenance_index import ProvenanceIndexRepository
from agx_research.collectors.quality import QualityAssessment, assess_quality
from agx_research.collectors.raw import ProcessingStep, RawDocument, RawDocumentRepository
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.events.entity import EntityKind, EntityRef
from agx_research.events.event import EventSeverity, EventType
from agx_research.events.service import EventPlatform, build_candidate_event
from agx_research.events.taxonomy import EventSubtype
from agx_research.sources.health import HealthMonitor
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.reputation import SourceMetricsRepository, compute_reputation
from agx_research.sources.spec import EvidenceTier, SourceSpec


@dataclass
class CollectionRunResult:
    source_id: str
    documents_fetched: int
    batches_materialized: int
    batches_withheld: int
    price_bars_written: int
    macro_observations_written: int
    news_items_written: int
    corporate_events_written: int
    index_constituents_written: int
    financial_statement_line_items_written: int
    events_registered: int
    assessments: list[QualityAssessment]
    provider_documents: dict[str, int] = field(default_factory=dict)
    provider_yields: dict[str, int] = field(default_factory=dict)
    fetch_warnings: list[str] = field(default_factory=list)
    sector_classifications_written: int = 0
    news_discovery_items_written: int = 0


def collection_yield(result: CollectionRunResult) -> int:
    """Total usable canonical records this run actually produced -- the one
    definition of "yield" every health/status/decision computation in this
    platform shares, so a collector that fetched successfully but parsed
    nothing is never mistaken for one that actually produced data.

    Discovery-tier writes (`news_discovery_items_written`) count toward
    yield too -- a discovery-tier collector's fetch was still real,
    successful work, even though none of it reaches news.csv/evidence
    without a later primary-source match.
    """
    return (
        result.price_bars_written + result.macro_observations_written
        + result.news_items_written + result.corporate_events_written
        + result.index_constituents_written + result.financial_statement_line_items_written
        + result.news_discovery_items_written + result.sector_classifications_written
    )


def _write_price_bars(
    data_dir: Path, ticker: str, bars, *, on_written=None
) -> int:
    path = data_dir / "prices" / f"{ticker}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["date"]] = row
    for bar in bars:
        existing[bar.trade_date.isoformat()] = {
            "date": bar.trade_date.isoformat(),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        if on_written:
            on_written(bar.trade_date)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for date_key in sorted(existing):
            writer.writerow(existing[date_key])
    return len(bars)


def _write_macro_observations(
    data_dir: Path, series_id: str, observations, *, on_written=None
) -> int:
    path = data_dir / "macro" / f"{series_id}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["date"]] = row["value"]
    for obs in observations:
        existing[obs.observation_date.isoformat()] = str(obs.value)
        if on_written:
            on_written(obs.observation_date)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "value"])
        for date_key in sorted(existing):
            writer.writerow([date_key, existing[date_key]])
    return len(observations)


def _write_corporate_events(
    data_dir: Path, ticker: str, events, *, on_written=None
) -> int:
    path = data_dir / "corporate_events.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[tuple[str, str, str], dict] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[(row["ticker"], row["date"], row["event_type"])] = row
    for event in events:
        key = (event.ticker, event.event_date.isoformat(), event.event_type)
        existing[key] = {
            "ticker": event.ticker,
            "date": event.event_date.isoformat(),
            "event_type": event.event_type,
            "description": event.description,
            "details_json": json.dumps(event.details) if event.details else "",
        }
        if on_written:
            on_written(event.event_type, event.event_date)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["ticker", "date", "event_type", "description", "details_json"]
        )
        writer.writeheader()
        for key in sorted(existing):
            writer.writerow(existing[key])
    return len(events)


def _write_financial_statement_line_items(
    data_dir: Path, ticker: str, items, *, on_written=None
) -> int:
    path = data_dir / "financial_statements" / f"{ticker}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[tuple[str, str, str], dict] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[(row["period_end_date"], row["statement_type"], row["line_item"])] = row
    for item in items:
        key = (item.period_end_date.isoformat(), item.statement_type, item.line_item)
        existing[key] = {
            "period_end_date": item.period_end_date.isoformat(),
            "period_type": item.period_type,
            "statement_type": item.statement_type,
            "line_item": item.line_item,
            "value": item.value,
            "currency": item.currency,
        }
        if on_written:
            on_written(item.statement_type, item.line_item, item.period_end_date)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "period_end_date", "period_type", "statement_type", "line_item", "value", "currency",
            ],
        )
        writer.writeheader()
        for key in sorted(existing):
            writer.writerow(existing[key])
    return len(items)


def _write_index_constituents(
    data_dir: Path, index: str, constituents, *, on_written=None
) -> int:
    path = data_dir / "universe" / f"{index}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[tuple[str, str], dict] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[(row["ticker"], row["as_of_date"])] = row
    for constituent in constituents:
        key = (constituent.ticker, constituent.as_of_date.isoformat())
        existing[key] = {
            "ticker": constituent.ticker,
            "company_name": constituent.company_name,
            "as_of_date": constituent.as_of_date.isoformat(),
        }
        if on_written:
            on_written(constituent.ticker, constituent.as_of_date)
    with path.open("w", newline="", encoding="utf-8") as f:
        optional_fields = ("isin", "reuters_code", "weight_percent", "source_url")
        discovered = {field for row in existing.values() for field in row}
        fieldnames = ["ticker", "company_name", "as_of_date"]
        fieldnames.extend(field for field in optional_fields if field in discovered)
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for key in sorted(existing):
            writer.writerow(existing[key])
    return len(constituents)


def _write_sector_classifications(data_dir: Path, classifications, *, on_written=None) -> int:
    # Deliberately NOT under data_dir/"universe/" -- see
    # universe.sector.CollectedSectorProvider's docstring for the real,
    # live-evidenced incident (2026-08-02) this avoids:
    # CollectedUniverseProvider.constituents() globs every CSV in
    # universe/ expecting an as_of_date column.
    path = data_dir / "sectors" / "sector_membership.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["ticker"]] = row
    for item in classifications:
        # Keyed by ticker only (not also observed_date): a sector rarely
        # changes, so the latest collected classification simply replaces
        # any earlier one -- the same "one current fact per ticker" shape
        # `CollectedSectorProvider` reads, not a growing history.
        existing[item.ticker] = {
            "ticker": item.ticker,
            "sector": item.sector,
            "source_id": item.source_id,
            "observed_date": item.observed_date.isoformat(),
        }
        if on_written:
            on_written(item.ticker, item.sector, item.observed_date)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["ticker", "sector", "source_id", "observed_date"]
        )
        writer.writeheader()
        for key in sorted(existing):
            writer.writerow(existing[key])
    return len(classifications)


def _append_news_to(path: Path, items) -> int:
    # Merged idempotently by (date, source, headline), matching every
    # sibling writer above (_write_price_bars/_write_macro_observations/
    # _write_corporate_events) -- collecting the same feed twice (e.g. a
    # mock run followed by a replay run reading the same archive) must not
    # duplicate rows, since a downstream agent may treat each row as one
    # independent observation.
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[tuple[str, str, str], dict] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[(row["date"], row["source"], row["headline"])] = row
    for item in items:
        key = (item.published_at.isoformat(), item.source, item.headline)
        existing[key] = {
            "date": item.published_at.isoformat(),
            "source": item.source,
            "headline": item.headline,
            "tickers": "|".join(item.tickers),
            "body": item.body or "",
        }
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "source", "headline", "tickers", "body"])
        writer.writeheader()
        for key in sorted(existing):
            writer.writerow(existing[key])
    return len(items)


def append_news(data_dir: Path, items) -> int:
    """Materialize PRIMARY-tier news items into news.csv -- the file
    LocalCsvDataProvider/DatasetSnapshot reads. Never call this for a
    DISCOVERY-tier source's items; use `append_discovery_news` instead
    (see `sources.spec.EvidenceTier`).
    """
    return _append_news_to(data_dir / "news.csv", items)


def append_discovery_news(data_dir: Path, items) -> int:
    """Materialize DISCOVERY-tier news items (candidates only) into
    news_discovery.csv -- never read by DatasetSnapshot/agents directly.
    `collectors.discovery_reconciliation.reconcile_discovery_news()` is the
    only path that promotes a row from here into news.csv.
    """
    return _append_news_to(data_dir / "news_discovery.csv", items)


def _news_event_candidates(batch, spec: SourceSpec, raw_document_id: str):
    candidates = []
    for item in batch.news_items:
        entities = [
            EntityRef(kind=EntityKind.COMPANY, canonical_id=t, raw_mention=t)
            for t in item.tickers
        ] or [EntityRef(kind=EntityKind.UNKNOWN, canonical_id="unresolved", raw_mention=item.headline)]
        candidates.append(
            build_candidate_event(
                event_type=EventType.NEWS,
                subtype=EventSubtype.COMPANY_NEWS if item.tickers else EventSubtype.MACRO_NEWS,
                entities=entities,
                event_date=item.published_at,
                source=spec.id,
                confidence=spec.reliability_score,
                severity=EventSeverity.LOW,
                metadata={"headline": item.headline, "raw_document_id": raw_document_id},
                provenance=Provenance(
                    produced_by=f"collectors.{spec.id}",
                    produced_at=datetime.now(),
                    inputs=[ProvenanceRef(kind="raw_document", ref_id=raw_document_id)],
                ),
                discriminator=item.headline,
            )
        )
    return candidates


class CollectionService:
    def __init__(
        self,
        data_dir: Path | str,
        *,
        raw_documents: RawDocumentRepository | None = None,
        event_platform: EventPlatform | None = None,
        provenance_index: ProvenanceIndexRepository | None = None,
        metrics: SourceMetricsRepository | None = None,
        health_monitor: HealthMonitor | None = None,
        registry: SourceRegistry | None = None,
        min_confidence: float = 0.5,
    ):
        self.data_dir = Path(data_dir)
        self.raw_documents = raw_documents or RawDocumentRepository()
        self.event_platform = event_platform or EventPlatform()
        self.provenance_index = provenance_index or ProvenanceIndexRepository()
        self.metrics = metrics or SourceMetricsRepository()
        self.health_monitor = health_monitor or HealthMonitor()
        self.registry = registry
        self.min_confidence = min_confidence

    def run(self, collector: Collector, *, expected_records: int) -> CollectionRunResult:
        latencies_before = len(getattr(collector.fetcher, "request_latencies", []))
        try:
            documents = collector.fetch()
        except Exception as exc:
            # A fetch-level failure (timeout, DNS, connection refused, ...)
            # must still be recorded in metrics/health -- previously this
            # exception propagated straight out of `run()` before any of
            # `_record_run_outcome`'s bookkeeping ran, so a source whose
            # `fetch()` always raises never accumulated `consecutive_failures`
            # and could never reach `HealthStatus.DOWN` no matter how many
            # times it failed.
            self._record_fetch_failure(collector, error=f"{type(exc).__name__}: {exc}")
            raise
        new_latencies = getattr(collector.fetcher, "request_latencies", [])[latencies_before:]
        latency_seconds = sum(new_latencies) / len(new_latencies) if new_latencies else None
        result = CollectionRunResult(
            source_id=collector.spec.id,
            documents_fetched=len(documents),
            batches_materialized=0,
            batches_withheld=0,
            price_bars_written=0,
            macro_observations_written=0,
            news_items_written=0,
            corporate_events_written=0,
            index_constituents_written=0,
            financial_statement_line_items_written=0,
            events_registered=0,
            assessments=[],
            provider_documents={},
            provider_yields={},
            fetch_warnings=list(getattr(collector, "fetch_warnings", [])),
        )

        provider_for_document = getattr(collector, "provider_for_document", None)
        if callable(provider_for_document):
            for document in documents:
                provider = provider_for_document(document)
                if provider:
                    result.provider_documents[provider] = (
                        result.provider_documents.get(provider, 0) + 1
                    )

        for document in documents:
            # Idempotent: a document already archived (e.g. replayed via
            # ArchiveReplayCollector) is not re-appended as a duplicate version.
            if self.raw_documents.latest(document.id) is None:
                self.raw_documents.add(document, persist=False)

            parser_raised = False
            try:
                batch = collector.parse(document)
            except Exception:
                parser_raised = True
                batch = None

            if parser_raised:
                self._record_run_outcome(
                    collector, document, succeeded=False, expected_records=expected_records,
                    records_produced=0, parser_raised=True, latency_seconds=latency_seconds,
                )
                if callable(provider_for_document):
                    provider = provider_for_document(document)
                    if provider:
                        self._record_provider_outcome(
                            provider, succeeded=False, expected_records=expected_records,
                            records_produced=0, parser_raised=True,
                            schema_version=document.schema_version,
                            latency_seconds=latency_seconds,
                        )
                result.batches_withheld += 1
                continue

            assessment = assess_quality(
                batch,
                expected_records=expected_records,
                source_reliability=collector.spec.reliability_score,
                freshness_score=collector.spec.freshness_score,
            )
            result.assessments.append(assessment)

            step = ProcessingStep(
                step="quality_assessment",
                performed_by=f"{collector.name}@{collector.version}",
                performed_at=datetime.now(),
                detail=f"confidence={assessment.confidence_score:.3f}: {assessment.notes}",
            )
            self.raw_documents.record_step(
                document.id, kind="validation", step=step, persist=False
            )

            produced = (
                len(batch.price_bars) + len(batch.macro_observations) + len(batch.news_items)
                + len(batch.corporate_events) + len(batch.index_constituents)
                + len(batch.financial_statement_line_items) + len(batch.sector_classifications)
            )
            materialized = assessment.confidence_score >= self.min_confidence
            provider = provider_for_document(document) if callable(provider_for_document) else None

            corroborated = 0
            new_candidates = 0
            if materialized:
                result.batches_materialized += 1
                if provider:
                    result.provider_yields[provider] = (
                        result.provider_yields.get(provider, 0) + produced
                    )
                by_ticker: dict[str, list] = {}
                for bar in batch.price_bars:
                    by_ticker.setdefault(bar.ticker, []).append(bar)
                for ticker, bars in by_ticker.items():
                    result.price_bars_written += _write_price_bars(
                        self.data_dir, ticker, bars,
                        on_written=lambda d, t=ticker: self._trace(
                            "price", t, d, collector, document
                        ),
                    )

                by_series: dict[str, list] = {}
                for obs in batch.macro_observations:
                    by_series.setdefault(obs.series_id, []).append(obs)
                for series_id, observations in by_series.items():
                    result.macro_observations_written += _write_macro_observations(
                        self.data_dir, series_id, observations,
                        on_written=lambda d, s=series_id: self._trace(
                            "macro", s, d, collector, document
                        ),
                    )

                if batch.news_items and collector.spec.evidence_tier == EvidenceTier.DISCOVERY:
                    # Never news.csv, never the Event Platform, regardless of
                    # confidence -- a DISCOVERY-tier source's items are
                    # candidates only. reconcile_discovery_news() is the sole
                    # promotion path, and it requires an independent PRIMARY
                    # source (see sources.spec.EvidenceTier).
                    result.news_discovery_items_written += append_discovery_news(
                        self.data_dir, batch.news_items
                    )
                elif batch.news_items:
                    result.news_items_written += append_news(self.data_dir, batch.news_items)
                    candidates = _news_event_candidates(batch, collector.spec, document.id)
                    for candidate in candidates:
                        registered = self.event_platform.register(candidate)
                        if registered.version > 1:
                            corroborated += 1
                        else:
                            new_candidates += 1
                        self._trace(
                            "news", registered.id, registered.event_date, collector, document,
                        )
                    result.events_registered += len(candidates)

                if batch.corporate_events:
                    by_event_ticker: dict[str, list] = {}
                    for event in batch.corporate_events:
                        by_event_ticker.setdefault(event.ticker, []).append(event)
                    for ticker, events in by_event_ticker.items():
                        result.corporate_events_written += _write_corporate_events(
                            self.data_dir, ticker, events,
                            on_written=lambda event_type, d, t=ticker: self._trace(
                                "corporate_event", f"{t}|{event_type}", d, collector, document
                            ),
                        )
                    # Materialized here only -- `events_from_corporate_events`
                    # (events.adapters) is the single place these become
                    # registered Events, once a DatasetSnapshot reads this
                    # same corporate_events.csv. Registering here too would
                    # duplicate that path rather than compose with it.

                if batch.index_constituents:
                    by_index: dict[str, list] = {}
                    for constituent in batch.index_constituents:
                        by_index.setdefault(constituent.index, []).append(constituent)
                    for index, constituents in by_index.items():
                        result.index_constituents_written += _write_index_constituents(
                            self.data_dir, index, constituents,
                            on_written=lambda ticker, d, i=index: self._trace(
                                "index_constituent", f"{i}|{ticker}", d, collector, document
                            ),
                        )

                if batch.financial_statement_line_items:
                    by_stmt_ticker: dict[str, list] = {}
                    for item in batch.financial_statement_line_items:
                        by_stmt_ticker.setdefault(item.ticker, []).append(item)
                    for ticker, items in by_stmt_ticker.items():
                        result.financial_statement_line_items_written += (
                            _write_financial_statement_line_items(
                                self.data_dir, ticker, items,
                                on_written=lambda stmt, line, d, t=ticker: self._trace(
                                    "financial_statement", f"{t}|{stmt}|{line}", d, collector, document
                                ),
                            )
                        )

                if batch.sector_classifications:
                    result.sector_classifications_written += _write_sector_classifications(
                        self.data_dir, batch.sector_classifications,
                        on_written=lambda ticker, sector, d: self._trace(
                            "sector_classification", f"{ticker}|{sector}", d, collector, document
                        ),
                    )
            else:
                result.batches_withheld += 1

            self._record_run_outcome(
                collector, document, succeeded=True, expected_records=expected_records,
                records_produced=produced, materialized=materialized, assessment=assessment,
                corroborated_candidates=corroborated, new_candidates=new_candidates,
                latency_seconds=latency_seconds,
            )
            if provider:
                self._record_provider_outcome(
                    provider, succeeded=True, expected_records=expected_records,
                    records_produced=produced, assessment=assessment,
                    schema_version=document.schema_version,
                    latency_seconds=latency_seconds,
                )

        # One persisted snapshot per source run, not once per document. A
        # full-Universe price source can return hundreds of large raw pages;
        # rewriting the growing JSON repository for every add/validation
        # revision is quadratic and can dominate a production deployment.
        self.raw_documents.flush()
        # Provenance follows the same run-level transaction boundary.
        # FRED currently returns seven large series documents; flushing the
        # 35MB provenance index after each one multiplies deployment I/O with
        # no durability benefit because the source run is the transaction.
        self.provenance_index.flush()
        return result

    def _record_fetch_failure(self, collector: Collector, *, error: str) -> None:
        metrics = self.metrics.record_run(
            collector.spec.id,
            succeeded=False,
            records_expected=0,
            records_produced=0,
            schema_version=collector.spec.schema_version,
        )
        health, _alerts = self.health_monitor.evaluate_run(
            collector.spec.id, metrics, fetch_succeeded=False, fetch_error=error,
        )
        if self.registry is not None:
            self.registry.update_health(collector.spec.id, health)

    def _trace(self, artifact_type: str, key: str, record_date, collector: Collector, document: RawDocument) -> None:
        self.provenance_index.record(
            artifact_type=artifact_type,
            key=key,
            record_date=record_date,
            source_id=collector.spec.id,
            collector=collector.name,
            collector_version=collector.version,
            raw_document_id=document.id,
            content_hash=document.content_hash,
            schema_version=document.schema_version,
            persist=False,
        )

    def _record_run_outcome(
        self,
        collector: Collector,
        document: RawDocument,
        *,
        succeeded: bool,
        expected_records: int,
        records_produced: int,
        materialized: bool = False,
        parser_raised: bool = False,
        assessment: QualityAssessment | None = None,
        corroborated_candidates: int = 0,
        new_candidates: int = 0,
        latency_seconds: float | None = None,
    ) -> None:
        prior = self.metrics.latest(collector.spec.id)
        had_produced_before = bool(prior and prior.records_produced_total > 0)
        metrics = self.metrics.record_run(
            collector.spec.id,
            succeeded=succeeded,
            records_expected=expected_records,
            records_produced=records_produced,
            confidence_score=assessment.confidence_score if assessment else None,
            freshness_score=assessment.freshness_score if assessment else None,
            coverage_score=assessment.coverage_score if assessment else None,
            latency_seconds=latency_seconds,
            materialized=materialized,
            corroborated_candidates=corroborated_candidates,
            new_candidates=new_candidates,
            schema_version=document.schema_version,
        )
        health, _alerts = self.health_monitor.evaluate_run(
            collector.spec.id,
            metrics,
            fetch_succeeded=succeeded,
            parser_raised=parser_raised,
            records_produced=records_produced,
            had_produced_before=had_produced_before,
            freshness_score=assessment.freshness_score if assessment else None,
        )
        if self.registry is not None:
            self.registry.update_health(collector.spec.id, health)
            reputation = compute_reputation(metrics)
            if reputation.composite is not None:
                self.registry.record_measured_quality(collector.spec.id, reputation.composite)

    def _record_provider_outcome(
        self,
        provider_id: str,
        *,
        succeeded: bool,
        expected_records: int,
        records_produced: int,
        schema_version: str | None,
        parser_raised: bool = False,
        assessment: QualityAssessment | None = None,
        latency_seconds: float | None = None,
    ) -> None:
        """A provider leg wired inside a composite collector (`SourceSpec.
        integrated_via`, e.g. yahoo_finance/stockanalysis/mubasher inside
        `EgxCompositePriceCollector`) is an operationally distinct source
        with its own registry entry. Each raw document is already
        attributable to exactly one provider (`Collector.provider_for_document`),
        so its measured outcome can be recorded against that provider's own
        id instead of leaving its `health_status`/`reputation_score` at
        `UNKNOWN`/`None` forever regardless of how much real traffic it
        actually served -- the exact "measurement never reaches the
        sub-source" gap this closes.
        """
        if self.registry is None or self.registry.latest(provider_id) is None:
            return
        prior = self.metrics.latest(provider_id)
        had_produced_before = bool(prior and prior.records_produced_total > 0)
        metrics = self.metrics.record_run(
            provider_id,
            succeeded=succeeded,
            records_expected=expected_records,
            records_produced=records_produced,
            confidence_score=assessment.confidence_score if assessment else None,
            freshness_score=assessment.freshness_score if assessment else None,
            coverage_score=assessment.coverage_score if assessment else None,
            latency_seconds=latency_seconds,
            materialized=succeeded and not parser_raised and records_produced > 0,
            schema_version=schema_version,
        )
        health, _alerts = self.health_monitor.evaluate_run(
            provider_id,
            metrics,
            fetch_succeeded=succeeded,
            parser_raised=parser_raised,
            records_produced=records_produced,
            had_produced_before=had_produced_before,
            freshness_score=assessment.freshness_score if assessment else None,
        )
        self.registry.update_health(provider_id, health)
        reputation = compute_reputation(metrics)
        if reputation.composite is not None:
            self.registry.record_measured_quality(provider_id, reputation.composite)
