"""ProvenanceIndex: the per-value trace the charter's Provenance Layer
requires -- every materialized price bar / macro observation / news item
must walk back to its source, collector, artifact, transformation,
timestamp, hash, and schema version.

`RawDocument` already carries source/collector/hash/schema_version/timestamp
at the *document* level, but before this module existed, materialization
(`collectors.service.CollectionService`) only preserved that link for news
items (via event metadata) -- price bars and macro observations were written
straight into CSV with no link back to the `RawDocument` that produced them.
This module closes that gap: one `ProvenanceRecord` per materialized value,
keyed by (artifact_type, key, record_date), so any cell in the data layer is
one lookup away from full lineage. Re-materializing the same value (e.g. a
corrected re-fetch, or a replay with a newer parser) appends a new version
rather than losing the old lineage -- `history()` shows every transformation
a value has ever gone through.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel

from agx_research.storage.repository import JsonFileRepository


class ProvenanceRecord(BaseModel):
    id: str  # f"{artifact_type}:{key}:{record_date.isoformat()}"
    version: int = 1
    artifact_type: str  # "price" | "macro" | "news"
    key: str  # ticker, series_id, or a news item's fingerprint
    record_date: date
    source_id: str
    collector: str
    collector_version: str
    raw_document_id: str
    content_hash: str
    schema_version: str
    materialized_at: datetime


def provenance_record_id(artifact_type: str, key: str, record_date: date) -> str:
    return f"{artifact_type}:{key}:{record_date.isoformat()}"


class ProvenanceIndexRepository(JsonFileRepository[ProvenanceRecord]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(ProvenanceRecord, persist_path)

    def record(
        self,
        *,
        artifact_type: str,
        key: str,
        record_date: date,
        source_id: str,
        collector: str,
        collector_version: str,
        raw_document_id: str,
        content_hash: str,
        schema_version: str,
        materialized_at: datetime | None = None,
        persist: bool = True,
    ) -> ProvenanceRecord:
        record_id = provenance_record_id(artifact_type, key, record_date)
        current = self.latest(record_id)
        record = ProvenanceRecord(
            id=record_id,
            version=(current.version + 1) if current else 1,
            artifact_type=artifact_type,
            key=key,
            record_date=record_date,
            source_id=source_id,
            collector=collector,
            collector_version=collector_version,
            raw_document_id=raw_document_id,
            content_hash=content_hash,
            schema_version=schema_version,
            materialized_at=materialized_at or datetime.now(),
        )
        if persist:
            return self.add(record)
        self._revisions.setdefault(record.id, []).append(record)
        return record

    def flush(self) -> None:
        """Persist records accumulated with ``persist=False`` in one write.

        Macro APIs can materialize hundreds of observations per document.
        Rewriting the complete JSON index for every cell is quadratic and
        eventually fails on Windows; CollectionService batches those writes
        and flushes once after the materialized batch is complete.
        """
        self._save()

    def trace(self, artifact_type: str, key: str, record_date: date) -> ProvenanceRecord | None:
        return self.latest(provenance_record_id(artifact_type, key, record_date))
