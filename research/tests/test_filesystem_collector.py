import pytest

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.base import CollectionBatch
from agx_research.collectors.filesystem import FilesystemCollector
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="fs_source", name="Filesystem Source", category=SourceCategory.OFFICIAL,
        access_method=AccessMethod.CSV_DOWNLOAD, status=SourceStatus.IMPLEMENTED,
        reliability_score=0.9, freshness_score=0.5,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


class EchoingFilesystemCollector(FilesystemCollector):
    name = "EchoingFilesystemCollector"
    version = "1.0.0"

    def parse(self, document) -> CollectionBatch:
        marker = document.content_text if not document.is_binary else "<binary>"
        return CollectionBatch(
            source_id=document.source_id, raw_document_id=document.id, parse_warnings=[marker]
        )


def test_fetch_wraps_text_files_as_text_raw_documents(tmp_path):
    (tmp_path / "a.csv").write_text("date,value\n2026-06-01,1.0\n")
    (tmp_path / "b.csv").write_text("date,value\n2026-06-02,2.0\n")

    collector = EchoingFilesystemCollector(make_spec(), tmp_path, pattern="*.csv")
    documents = collector.fetch()

    assert len(documents) == 2
    assert all(not d.is_binary for d in documents)
    assert documents[0].original_url.startswith("file://")


def test_fetch_wraps_binary_files_via_archive(tmp_path):
    (tmp_path / "report.pdf").write_bytes(b"\x89PDF-fake-binary-\x00\x01\x02")
    archive = RawArchive(tmp_path / "archive")

    collector = EchoingFilesystemCollector(make_spec(), tmp_path, pattern="*.pdf", archive=archive)
    [document] = collector.fetch()

    assert document.is_binary
    assert archive.retrieve(document.content_hash) == b"\x89PDF-fake-binary-\x00\x01\x02"


def test_binary_file_without_archive_configured_raises(tmp_path):
    (tmp_path / "report.pdf").write_bytes(b"\x89binary\x00\x01")
    collector = EchoingFilesystemCollector(make_spec(), tmp_path, pattern="*.pdf")
    with pytest.raises(ValueError):
        collector.fetch()


def test_pattern_excludes_non_matching_files(tmp_path):
    (tmp_path / "a.csv").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    collector = EchoingFilesystemCollector(make_spec(), tmp_path, pattern="*.csv")
    documents = collector.fetch()
    assert len(documents) == 1


def test_collector_rejects_non_implemented_source(tmp_path):
    spec = make_spec(status=SourceStatus.PLANNED)
    with pytest.raises(ValueError):
        EchoingFilesystemCollector(spec, tmp_path)
