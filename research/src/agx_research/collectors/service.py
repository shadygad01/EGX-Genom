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
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
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
from agx_research.sources.spec import SourceSpec


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


def collection_yield(result: CollectionRunResult) -> int:
    """Total usable canonical records this run actually produced -- the one
    definition of "yield" every health/status/decision computation in this
    platform shares, so a collector that fetched successfully but parsed
    nothing is never mistaken for one that actually produced data.
    """
    return (
        result.price_bars_written + result.macro_observations_written
        + result.news_items_written + result.corporate_events_written
        + result.index_constituents_written + result.financial_statement_line_items_written
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
        writer = csv.DictWriter(f, fieldnames=["ticker", "company_name", "as_of_date"])
        writer.writeheader()
        for key in sorted(existing):
            writer.writerow(existing[key])
    return len(constituents)


def _append_news(data_dir: Path, items) -> int:
    path = data_dir / "news.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["date", "source", "headline", "tickers", "body"])
        for item in items:
            writer.writerow(
                [
                    item.published_at.isoformat(),
                    item.source,
                    item.headline,
                    "|".join(item.tickers),
                    item.body or "",
                ]
            )
    return len(items)


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
        )

        for document in documents:
            # Idempotent: a document already archived (e.g. replayed via
            # ArchiveReplayCollector) is not re-appended as a duplicate version.
            if self.raw_documents.latest(document.id) is None:
                self.raw_documents.add(document)

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
            self.raw_documents.record_step(document.id, kind="validation", step=step)

            produced = (
                len(batch.price_bars) + len(batch.macro_observations) + len(batch.news_items)
                + len(batch.corporate_events) + len(batch.index_constituents)
                + len(batch.financial_statement_line_items)
            )
            materialized = assessment.confidence_score >= self.min_confidence

            corroborated = 0
            new_candidates = 0
            if materialized:
                result.batches_materialized += 1
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

                if batch.news_items:
                    result.news_items_written += _append_news(self.data_dir, batch.news_items)
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
                self.provenance_index.flush()
            else:
                result.batches_withheld += 1

            self._record_run_outcome(
                collector, document, succeeded=True, expected_records=expected_records,
                records_produced=produced, materialized=materialized, assessment=assessment,
                corroborated_candidates=corroborated, new_candidates=new_candidates,
                latency_seconds=latency_seconds,
            )

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
