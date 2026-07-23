"""PdfDocumentCollector: the shared mechanics every PDF-based source
(Company IR reports, MoF/CAPMAS bulletins, Suez Canal Authority statistics)
needs -- fetch bytes, archive them immutably, extract text -- so a concrete
collector only has to implement *where the numbers are in the text*, never
how to fetch or extract a PDF.

`parse()` stays abstract: turning PDF text into `PriceBar`/`MacroObservation`/
`NewsItem` values is unavoidably source-specific (a regulator's bulletin
layout has nothing in common with an IR quarterly report), so inventing a
generic parse here would either be a no-op or fabricate a wrong extraction
"strategy". This is the framework piece the charter's collector-types list
asks for; the source-specific subclass is deliberately left for whichever
concrete PDF source's endpoint gets verified first.
"""

from __future__ import annotations

from abc import abstractmethod
from io import BytesIO

from pypdf import PdfReader

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_binary_raw_document
from agx_research.sources.spec import SourceSpec


class PdfDocumentCollector(Collector):
    def __init__(self, spec: SourceSpec, urls: list[str], *, archive: RawArchive, fetcher=None):
        super().__init__(spec, fetcher)
        self.urls = urls
        self.archive = archive

    def fetch(self) -> list[RawDocument]:
        documents = []
        for url in self.urls:
            content = self.fetcher.fetch_bytes(url, self.spec)
            documents.append(
                build_binary_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    original_url=url,
                    content=content,
                    schema_version=self.spec.schema_version,
                    license=self.spec.license,
                    archive=self.archive,
                )
            )
        return documents

    def extract_text(self, document: RawDocument) -> str:
        """Pure function of an archived document -- replayable forever from
        the same bytes, exactly like every other collector's `parse`.
        """
        content = self.archive.retrieve(document.content_hash)
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @abstractmethod
    def parse(self, document: RawDocument) -> CollectionBatch:
        """Subclasses: call `self.extract_text(document)` then locate the
        source's specific values in the resulting text.
        """
