"""Reusable diagnostic: fetch real company PDF earnings-release/financial-
statement URLs and print their extracted text, so a real, evidence-based
parser can be written or extended for a Family B PDF financial-statement
collector (see docs/COLLECTOR_TEMPLATE_TAXONOMY.md, "Family B — PDF report
repository", and TD-32/AD-61's repayment trigger).

URLs in TARGETS below come from
`research/data/registry/company_financial_sources.json` on the
`discovery/latest` branch (a real, live GitHub Actions discovery run) --
not guessed. This script performs REAL network fetches (respecting
robots.txt via the existing `HttpFetcher`); it must only be run in an
environment with real egress (a GitHub Actions runner), never assumed to
work from a sandboxed session with no outbound access.

This is diagnostic only: it does NOT write to sources/catalog.py, creates
no SourceSpec revision, and produces no dashboard artifact. The throwaway
SourceSpec below is never persisted to the SourceRegistry -- marking it
`IMPLEMENTED` only satisfies `Collector.__init__`'s constructor guard for
this one ephemeral object; it does not relax `AD-16`'s real rule that a
catalogued source only becomes `IMPLEMENTED` after independently verified
reachability. Writing a real collector/parser and promoting a catalog entry
to `IMPLEMENTED` stays a separate, reviewed commit made after inspecting
this script's real output.

To inspect a new company: add its real, already-discovered URLs to
TARGETS (never a guessed URL), run via
`uv run python scripts/probe_pdf_text.py` from `research/` in an
environment with real egress (e.g. `.github/workflows/probe-pdf-text.yml`,
`workflow_dispatch`), then read the real extracted text before writing or
extending any parser.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.base import CollectionBatch
from agx_research.collectors.fetcher import FetchDisallowed, FetchError, HttpFetcher
from agx_research.collectors.pdf import PdfDocumentCollector
from agx_research.collectors.raw import RawDocument
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


class _ProbeCollector(PdfDocumentCollector):
    """Concrete only so this diagnostic can instantiate the abstract
    `PdfDocumentCollector` -- this probe only ever calls `fetch()`/
    `extract_text()`, never `parse()`, so the override below is
    unreachable in normal use; it exists solely to satisfy Python's ABC
    machinery, not to represent any real parsing capability."""

    name = "ProbeCollector"
    version = "0.0.0-diagnostic"

    def parse(self, document: RawDocument) -> CollectionBatch:
        raise NotImplementedError("diagnostic-only collector; parse() is intentionally unused")

# Narrowest, most tractable Family B targets per the taxonomy doc's roadmap
# step 2: the 4-company "Quarterly Earnings Release PDF" sub-pattern, one
# recent quarterly file per company plus one more-detailed statement where
# discovered as a distinct document.
TARGETS: dict[str, list[str]] = {
    "JUFO": [
        "https://www.juhayna.com/app/uploads/2026/05/ER-1Q26-ENG-1.pdf",
        "https://www.juhayna.com/app/uploads/2025/11/1575794448_181_11881190_jufoar18financialsv3.4highresolution.pdf",
    ],
    "RMDA": [
        "https://ramedapharma-ir.com/wp-content/uploads/2026/05/Rameda-1Q26-Earnings-Release.pdf",
    ],
    "ORWE": [
        "https://orientalweavers.com/wp-content/uploads/2026/06/1Q-2026-Earnings-Release.pdf",
        "https://orientalweavers.com/wp-content/uploads/2026/05/OW-Consolidated-Financial-Statement-31-3-2026.pdf",
    ],
    "TMGH": [
        "https://talaatmoustafa.com/upload/TMG%20Holding%201Q26%20ER%20-%20EN.pdf",
        "http://Talaatmoustafa.com/upload/TMG%20seperate%20financials%20as%20of%2031%20March%202026%20-%20English%20version.pdf",
    ],
}


def _diagnostic_spec(ticker: str, url: str) -> SourceSpec:
    return SourceSpec(
        id=f"probe_{ticker.lower()}",
        name=f"{ticker} PDF probe (diagnostic only -- never catalogued or persisted)",
        category=SourceCategory.COMPANY,
        access_method=AccessMethod.PDF_DOWNLOAD,
        status=SourceStatus.IMPLEMENTED,
        base_url=url,
        reliability_score=0.5,
        freshness_score=0.5,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        archive = RawArchive(Path(tmp) / "raw_archive")
        fetcher = HttpFetcher()
        for ticker, urls in TARGETS.items():
            print(f"\n{'=' * 88}\n{ticker}\n{'=' * 88}")
            for url in urls:
                spec = _diagnostic_spec(ticker, url)
                collector = _ProbeCollector(spec, [url], archive=archive, fetcher=fetcher)
                try:
                    documents = collector.fetch()
                except (FetchDisallowed, FetchError) as exc:
                    print(f"\n--- {url}\nFETCH FAILED: {exc}")
                    continue
                for document in documents:
                    text = collector.extract_text(document)
                    print(f"\n--- {url}\nextracted {len(text)} chars; first 4000:\n{text[:4000]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
