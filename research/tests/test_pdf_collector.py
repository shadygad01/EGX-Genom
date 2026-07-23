"""PdfDocumentCollector tests: fetch/archive/extract mechanics only -- parse()
is abstract (source-specific), so a minimal concrete subclass is defined
here purely to exercise the shared machinery. The synthetic PDF is a
hand-built minimal document (valid PDF 1.4 structure, no external tooling)
carrying one short text string, built once by `_build_minimal_pdf`.
"""

import pytest

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.base import CollectionBatch
from agx_research.collectors.pdf import PdfDocumentCollector
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def _build_minimal_pdf(text: str) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 200 200] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 24 Tf 10 100 Td ({text}) Tj ET".encode()
    objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj".encode() + obj + b"endobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n" + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    out += b"startxref\n" + f"{xref_offset}\n".encode() + b"%%EOF"
    return bytes(out)


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="pdf_source", name="PDF Source", category=SourceCategory.COMPANY,
        access_method=AccessMethod.PDF_DOWNLOAD, status=SourceStatus.IMPLEMENTED,
        reliability_score=0.8, freshness_score=0.5,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


class FakeFetcher:
    def __init__(self, content: bytes):
        self.content = content

    def fetch_bytes(self, url, spec):
        return self.content


class MinimalPdfCollector(PdfDocumentCollector):
    name = "MinimalPdfCollector"
    version = "1.0.0"

    def parse(self, document) -> CollectionBatch:
        text = self.extract_text(document)
        return CollectionBatch(
            source_id=document.source_id, raw_document_id=document.id,
            parse_warnings=[text],  # smuggle extracted text out for assertions
        )


def test_fetch_archives_binary_content_and_marks_document_binary(tmp_path):
    content = _build_minimal_pdf("Quarterly Report 2026")
    fetcher = FakeFetcher(content)
    archive = RawArchive(tmp_path)
    collector = MinimalPdfCollector(make_spec(), ["https://ir.example.com/q1.pdf"], archive=archive, fetcher=fetcher)

    [document] = collector.fetch()
    assert document.is_binary
    assert document.content_text == ""
    assert archive.retrieve(document.content_hash) == content


def test_extract_text_recovers_the_original_text(tmp_path):
    content = _build_minimal_pdf("Quarterly Report 2026")
    fetcher = FakeFetcher(content)
    archive = RawArchive(tmp_path)
    collector = MinimalPdfCollector(make_spec(), ["https://ir.example.com/q1.pdf"], archive=archive, fetcher=fetcher)

    [document] = collector.fetch()
    batch = collector.parse(document)
    assert "Quarterly Report 2026" in batch.parse_warnings[0]


def test_collector_rejects_non_implemented_source(tmp_path):
    spec = make_spec(status=SourceStatus.PLANNED)
    with pytest.raises(ValueError):
        MinimalPdfCollector(spec, ["https://x/y.pdf"], archive=RawArchive(tmp_path))
