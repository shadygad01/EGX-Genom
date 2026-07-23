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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agx_research.collectors.base import Collector
from agx_research.collectors.quality import QualityAssessment, assess_quality
from agx_research.collectors.raw import ProcessingStep, RawDocumentRepository
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.events.entity import EntityKind, EntityRef
from agx_research.events.event import EventSeverity, EventType
from agx_research.events.service import EventPlatform, build_candidate_event
from agx_research.events.taxonomy import EventSubtype
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
    events_registered: int
    assessments: list[QualityAssessment]


def _write_price_bars(data_dir: Path, ticker: str, bars) -> int:
    path = data_dir / "prices" / f"{ticker}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    if path.exists():
        with path.open(newline="") as f:
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
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for date_key in sorted(existing):
            writer.writerow(existing[date_key])
    return len(bars)


def _write_macro_observations(data_dir: Path, series_id: str, observations) -> int:
    path = data_dir / "macro" / f"{series_id}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, str] = {}
    if path.exists():
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                existing[row["date"]] = row["value"]
    for obs in observations:
        existing[obs.observation_date.isoformat()] = str(obs.value)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "value"])
        for date_key in sorted(existing):
            writer.writerow([date_key, existing[date_key]])
    return len(observations)


def _append_news(data_dir: Path, items) -> int:
    path = data_dir / "news.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="") as f:
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
        min_confidence: float = 0.5,
    ):
        self.data_dir = Path(data_dir)
        self.raw_documents = raw_documents or RawDocumentRepository()
        self.event_platform = event_platform or EventPlatform()
        self.min_confidence = min_confidence

    def run(self, collector: Collector, *, expected_records: int) -> CollectionRunResult:
        documents = collector.fetch()
        result = CollectionRunResult(
            source_id=collector.spec.id,
            documents_fetched=len(documents),
            batches_materialized=0,
            batches_withheld=0,
            price_bars_written=0,
            macro_observations_written=0,
            news_items_written=0,
            events_registered=0,
            assessments=[],
        )

        for document in documents:
            self.raw_documents.add(document)
            batch = collector.parse(document)
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

            if assessment.confidence_score < self.min_confidence:
                result.batches_withheld += 1
                continue

            result.batches_materialized += 1
            by_ticker: dict[str, list] = {}
            for bar in batch.price_bars:
                by_ticker.setdefault(bar.ticker, []).append(bar)
            for ticker, bars in by_ticker.items():
                result.price_bars_written += _write_price_bars(self.data_dir, ticker, bars)

            by_series: dict[str, list] = {}
            for obs in batch.macro_observations:
                by_series.setdefault(obs.series_id, []).append(obs)
            for series_id, observations in by_series.items():
                result.macro_observations_written += _write_macro_observations(
                    self.data_dir, series_id, observations
                )

            if batch.news_items:
                result.news_items_written += _append_news(self.data_dir, batch.news_items)
                candidates = _news_event_candidates(batch, collector.spec, document.id)
                for candidate in candidates:
                    self.event_platform.register(candidate)
                result.events_registered += len(candidates)

        return result
