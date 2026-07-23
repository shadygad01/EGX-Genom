from datetime import datetime

import pytest

from agx_research.collectors.raw import (
    ProcessingStep,
    RawDocumentRepository,
    build_raw_document,
    content_sha256,
    derive_document_id,
)


def make_document(**overrides):
    defaults = dict(
        source_id="stooq",
        collector="StooqPriceCollector",
        collector_version="1.0.0",
        original_url="https://stooq.com/q/d/l/?s=comi.eg&i=d",
        content_text="Date,Open,High,Low,Close,Volume\n2026-06-01,1,1,1,1,1\n",
        schema_version="1.0",
        license="unknown",
    )
    defaults.update(overrides)
    return build_raw_document(**defaults)


def test_content_hash_is_deterministic():
    assert content_sha256("abc") == content_sha256("abc")
    assert content_sha256("abc") != content_sha256("abd")


def test_document_id_is_stable_for_identical_refetch():
    a = make_document()
    b = make_document()
    assert a.id == b.id
    assert a.content_hash == b.content_hash


def test_changed_content_at_same_url_becomes_new_document_id():
    a = make_document(content_text="x")
    b = make_document(content_text="y")
    assert a.original_url == b.original_url
    assert a.id != b.id


def test_different_source_same_content_is_a_different_document():
    a = make_document(source_id="stooq")
    b = make_document(source_id="other")
    assert a.id != b.id


def test_derive_document_id_has_expected_prefix():
    doc_id = derive_document_id("s", "u", "h")
    assert doc_id.startswith("rawdoc_")


def test_repository_record_step_appends_without_mutating_history():
    repo = RawDocumentRepository()
    document = repo.add(make_document())
    step = ProcessingStep(
        step="quality_assessment",
        performed_by="tester",
        performed_at=datetime.now(),
        detail="ok",
    )
    updated = repo.record_step(document.id, kind="validation", step=step)
    assert updated.version == 2
    assert len(updated.validation_history) == 1
    assert updated.normalization_history == []

    original = repo.history(document.id)[0]
    assert original.validation_history == []


def test_record_step_normalization_kind_uses_normalization_history():
    repo = RawDocumentRepository()
    document = repo.add(make_document())
    step = ProcessingStep(
        step="ticker_mapping", performed_by="tester", performed_at=datetime.now()
    )
    updated = repo.record_step(document.id, kind="normalization", step=step)
    assert len(updated.normalization_history) == 1
    assert updated.validation_history == []


def test_record_step_unknown_document_raises():
    repo = RawDocumentRepository()
    step = ProcessingStep(step="x", performed_by="tester", performed_at=datetime.now())
    with pytest.raises(KeyError):
        repo.record_step("rawdoc_missing", kind="validation", step=step)
