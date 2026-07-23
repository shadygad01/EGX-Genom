"""FilesystemCollector: ingest files a human has already placed on disk.

The one collector type in the charter's list that has nothing to do with
network access -- it exists for datasets that arrive by manual download
(a CAPMAS bulletin saved by hand pending an automated endpoint, a bulk
historical archive a user drops in) or, in a real deployment, a directory a
separate legitimate process populates. Every matched file becomes a
`RawDocument` exactly like a network fetch would: text files inline, binary
files (PDF/Excel/images) via the same `RawArchive` every other binary
collector uses -- filesystem origin doesn't get a lighter provenance
standard than a network one.

`parse()` stays abstract for the same reason `PdfDocumentCollector.parse`
does: the file *format* varies per use, so a generic parse would either be a
no-op or a fabricated guess.
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.base import CollectionBatch, Collector
from agx_research.collectors.raw import RawDocument, build_binary_raw_document, build_raw_document
from agx_research.sources.spec import SourceSpec


class FilesystemCollector(Collector):
    def __init__(
        self,
        spec: SourceSpec,
        directory: Path | str,
        *,
        pattern: str = "*",
        archive: RawArchive | None = None,
        fetcher=None,
    ):
        super().__init__(spec, fetcher)
        self.directory = Path(directory)
        self.pattern = pattern
        self.archive = archive

    def fetch(self) -> list[RawDocument]:
        documents = []
        for path in sorted(self.directory.glob(self.pattern)):
            if not path.is_file():
                continue
            raw_bytes = path.read_bytes()
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                if self.archive is None:
                    raise ValueError(
                        f"{path} is not valid UTF-8 (binary file) but no RawArchive "
                        "was configured to store it."
                    ) from None
                documents.append(
                    build_binary_raw_document(
                        source_id=self.spec.id,
                        collector=self.name,
                        collector_version=self.version,
                        original_url=path.resolve().as_uri(),
                        content=raw_bytes,
                        schema_version=self.spec.schema_version,
                        license=self.spec.license,
                        archive=self.archive,
                    )
                )
                continue
            documents.append(
                build_raw_document(
                    source_id=self.spec.id,
                    collector=self.name,
                    collector_version=self.version,
                    original_url=path.resolve().as_uri(),
                    content_text=text,
                    schema_version=self.spec.schema_version,
                    license=self.spec.license,
                )
            )
        return documents

    @abstractmethod
    def parse(self, document: RawDocument) -> CollectionBatch:
        """Subclasses interpret the file format this instance is configured for."""
