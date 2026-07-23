"""RawDocument: the provenance envelope around every collected payload.

Every byte AGX ingests is wrapped in one of these before any parsing:
source id, collector name+version, fetch timestamp, original URL, sha256
content hash, schema version, license — plus append-only normalization and
validation histories written by later stages. Parsed values reference
their raw document id, so any value anywhere in AGX walks back to the
exact bytes collected, satisfying the program's provenance requirements.

The document id is derived from (source, url, content hash): re-fetching
identical content is idempotent, while changed content at the same URL
becomes a new document rather than an overwrite.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from agx_research.storage.repository import JsonFileRepository


class ProcessingStep(BaseModel):
    step: str
    performed_by: str
    performed_at: datetime
    detail: str = ""


class RawDocument(BaseModel):
    id: str
    version: int = 1
    source_id: str
    collector: str
    collector_version: str
    fetched_at: datetime
    original_url: str
    content_hash: str
    schema_version: str
    license: str
    content_text: str  # the payload as text (CSV/XML/JSON); binary formats store a reference
    normalization_history: list[ProcessingStep] = Field(default_factory=list)
    validation_history: list[ProcessingStep] = Field(default_factory=list)


def content_sha256(content: bytes | str) -> str:
    data = content.encode() if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


def derive_document_id(source_id: str, url: str, content_hash: str) -> str:
    digest = hashlib.sha256(f"{source_id}|{url}|{content_hash}".encode()).hexdigest()[:20]
    return f"rawdoc_{digest}"


def build_raw_document(
    *,
    source_id: str,
    collector: str,
    collector_version: str,
    original_url: str,
    content_text: str,
    schema_version: str,
    license: str,
    fetched_at: datetime | None = None,
) -> RawDocument:
    content_hash = content_sha256(content_text)
    return RawDocument(
        id=derive_document_id(source_id, original_url, content_hash),
        source_id=source_id,
        collector=collector,
        collector_version=collector_version,
        fetched_at=fetched_at or datetime.now(),
        original_url=original_url,
        content_hash=content_hash,
        schema_version=schema_version,
        license=license,
        content_text=content_text,
    )


class RawDocumentRepository(JsonFileRepository[RawDocument]):
    def __init__(self, persist_path: Path | str | None = None):
        super().__init__(RawDocument, persist_path)

    def record_step(
        self, document_id: str, *, kind: str, step: ProcessingStep
    ) -> RawDocument:
        current = self.latest(document_id)
        if current is None:
            raise KeyError(f"No raw document with id {document_id}")
        field = "normalization_history" if kind == "normalization" else "validation_history"
        return self.add(
            current.model_copy(
                update={
                    "version": current.version + 1,
                    field: [*getattr(current, field), step],
                }
            )
        )
