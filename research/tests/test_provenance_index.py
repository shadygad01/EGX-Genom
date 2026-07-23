from datetime import date

from agx_research.collectors.provenance_index import ProvenanceIndexRepository


def test_record_and_trace_roundtrip():
    repo = ProvenanceIndexRepository()
    repo.record(
        artifact_type="price", key="COMI", record_date=date(2026, 6, 1),
        source_id="stooq", collector="StooqPriceCollector", collector_version="1.0.0",
        raw_document_id="rawdoc_abc", content_hash="hash1", schema_version="1.0",
    )
    record = repo.trace("price", "COMI", date(2026, 6, 1))
    assert record is not None
    assert record.source_id == "stooq"
    assert record.raw_document_id == "rawdoc_abc"


def test_unknown_value_traces_to_none():
    repo = ProvenanceIndexRepository()
    assert repo.trace("price", "UNKNOWN", date(2026, 1, 1)) is None


def test_re_materialization_appends_new_version_not_overwrite():
    repo = ProvenanceIndexRepository()
    repo.record(
        artifact_type="price", key="COMI", record_date=date(2026, 6, 1),
        source_id="stooq", collector="StooqPriceCollector", collector_version="1.0.0",
        raw_document_id="rawdoc_abc", content_hash="hash1", schema_version="1.0",
    )
    updated = repo.record(
        artifact_type="price", key="COMI", record_date=date(2026, 6, 1),
        source_id="stooq", collector="StooqPriceCollector", collector_version="1.1.0",
        raw_document_id="rawdoc_def", content_hash="hash2", schema_version="1.0",
    )
    assert updated.version == 2
    history = repo.history(updated.id)
    assert len(history) == 2
    assert history[0].raw_document_id == "rawdoc_abc"
    assert history[1].raw_document_id == "rawdoc_def"
