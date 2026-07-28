"""Source Discovery Engine: finds candidate sources, trusts none of them.

Responsibilities per `docs/DATA_ACQUISITION.md`'s program scope: discover new
sources, RSS feeds, APIs, Investor Relations pages, PDF repositories,
structured datasets, macro/government datasets, historical archives. This
module only ever *reads* HTML/text already fetched by the caller (it takes
no fetcher, no network dependency, so it is fully unit-testable against
recorded fixture pages) and returns `SourceCandidate` objects. It has no
import of `SourceRegistry` at all -- structurally, a discovery run cannot
register or trust anything; that always requires the separate, explicit
`qualification.register_candidate` step with human-supplied catalog fields.

Uses stdlib `html.parser.HTMLParser` only (no BeautifulSoup dependency) --
tolerant of malformed HTML by design, since real pages are never perfectly
well-formed.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from agx_research.discovery.candidate import DiscoveryMethod, SourceCandidate
from agx_research.discovery.financial_document import (
    FinancialDocumentCategory,
    classify_financial_document,
)
from agx_research.sources.spec import AccessMethod

_STRUCTURED_EXTENSIONS = {
    ".csv": AccessMethod.CSV_DOWNLOAD,
    ".xlsx": AccessMethod.CSV_DOWNLOAD,
    ".xls": AccessMethod.CSV_DOWNLOAD,
    ".json": AccessMethod.JSON_API,
    ".xml": AccessMethod.XBRL,
}
_FEED_TYPES = {"application/rss+xml", "application/atom+xml", "application/feed+json"}


class _PageLinkParser(HTMLParser):
    """Collects every <a href> (with its inner text) and <link rel=alternate>
    on a page in one pass."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self._open_anchor: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        if tag == "a" and attr_dict.get("href"):
            attr_dict["text"] = ""
            self.anchors.append(attr_dict)
            self._open_anchor = attr_dict  # HTML anchors don't nest; last-opened wins
        elif tag == "link" and attr_dict.get("href"):
            self.links.append(attr_dict)

    def handle_data(self, data: str) -> None:
        if self._open_anchor is not None:
            self._open_anchor["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._open_anchor = None


def _parse_page(html: str) -> _PageLinkParser:
    parser = _PageLinkParser()
    parser.feed(html)
    return parser


def discover_rss_feeds(html: str, page_url: str) -> list[SourceCandidate]:
    """<link rel="alternate" type="application/rss+xml|atom+xml" href=...> autodiscovery."""
    parser = _parse_page(html)
    candidates = []
    for link in parser.links:
        rel = link.get("rel", "").lower()
        link_type = link.get("type", "").lower()
        if "alternate" in rel and link_type in _FEED_TYPES:
            url = urljoin(page_url, link["href"])
            candidates.append(
                SourceCandidate(
                    discovered_url=url,
                    origin_page_url=page_url,
                    discovery_method=DiscoveryMethod.RSS_AUTODISCOVERY,
                    access_method_guess=AccessMethod.RSS_FEED,
                    title_hint=link.get("title", ""),
                    evidence=f'<link rel="alternate" type="{link_type}" href="{link["href"]}">',
                )
            )
    return candidates


def discover_pdf_repository(html: str, page_url: str, *, min_pdf_links: int = 3) -> list[SourceCandidate]:
    """A page linking several PDFs is catalogued as one PDF-repository candidate
    (the page itself), not one candidate per PDF -- matches how Company IR /
    regulatory disclosure pages are actually modeled as a single source.
    """
    parser = _parse_page(html)
    pdf_links = [a["href"] for a in parser.anchors if a["href"].lower().split("?")[0].endswith(".pdf")]
    if len(pdf_links) < min_pdf_links:
        return []
    return [
        SourceCandidate(
            discovered_url=page_url,
            origin_page_url=page_url,
            discovery_method=DiscoveryMethod.PDF_REPOSITORY_SCAN,
            access_method_guess=AccessMethod.PDF_DOWNLOAD,
            evidence=f"{len(pdf_links)} PDF link(s) found on page",
            notes="; ".join(urljoin(page_url, href) for href in pdf_links[:5]),
        )
    ]


def discover_structured_datasets(html: str, page_url: str) -> list[SourceCandidate]:
    """CSV/XLS/JSON/XML download links -- one candidate per distinct file,
    since each is typically an independent dataset (unlike PDFs, which cluster
    into one repository per page).
    """
    parser = _parse_page(html)
    candidates = []
    seen: set[str] = set()
    for a in parser.anchors:
        href = a["href"]
        path = urlsplit(href).path.lower()
        for ext, access_method in _STRUCTURED_EXTENSIONS.items():
            if path.endswith(ext):
                url = urljoin(page_url, href)
                if url in seen:
                    break
                seen.add(url)
                candidates.append(
                    SourceCandidate(
                        discovered_url=url,
                        origin_page_url=page_url,
                        discovery_method=DiscoveryMethod.STRUCTURED_DATASET_SCAN,
                        access_method_guess=access_method,
                        evidence=f'<a href="{href}">',
                    )
                )
                break
    return candidates


_FINANCIAL_DOCUMENT_EXTENSIONS = {
    ".pdf": AccessMethod.PDF_DOWNLOAD,
    ".xlsx": AccessMethod.CSV_DOWNLOAD,
    ".xls": AccessMethod.CSV_DOWNLOAD,
    ".csv": AccessMethod.CSV_DOWNLOAD,
    ".json": AccessMethod.JSON_API,
    ".xml": AccessMethod.XBRL,
}


def discover_financial_documents(
    html: str, page_url: str
) -> list[tuple[SourceCandidate, FinancialDocumentCategory]]:
    """Anchors whose URL or visible text matches a known financial-document
    keyword (annual/quarterly report, financial statements, investor
    relations, ...), classified by `financial_document.classify_financial_document`.

    Deliberately narrower than `discover_pdf_repository`/
    `discover_structured_datasets`: those notice *that* a page links
    downloadable files at all; this notices *which specific report* a link
    is, so only keyword-matched anchors become candidates -- an unlabeled
    PDF link is still a real discoverable file (those two functions already
    catch it), just not one this function can honestly categorize.
    """
    parser = _parse_page(html)
    results: list[tuple[SourceCandidate, FinancialDocumentCategory]] = []
    seen: set[str] = set()
    for anchor in parser.anchors:
        href = anchor["href"]
        text = anchor.get("text", "").strip()
        category = classify_financial_document(href, text)
        if category is None:
            continue
        url = urljoin(page_url, href)
        if url in seen:
            continue
        seen.add(url)
        path = urlsplit(url).path.lower()
        access_method = AccessMethod.HTML_SCRAPE
        for ext, method in _FINANCIAL_DOCUMENT_EXTENSIONS.items():
            if path.endswith(ext):
                access_method = method
                break
        results.append((
            SourceCandidate(
                discovered_url=url,
                origin_page_url=page_url,
                discovery_method=DiscoveryMethod.FINANCIAL_DOCUMENT_SCAN,
                access_method_guess=access_method,
                title_hint=text,
                evidence=f'<a href="{href}">{text[:80]}</a>',
            ),
            category,
        ))
    return results


_API_DOC_MARKERS = ("swagger.json", "openapi.json", "openapi.yaml", "api-docs", "docs/api")


def discover_api_documentation(html: str, page_url: str) -> list[SourceCandidate]:
    """Links to conventional API-documentation endpoints (OpenAPI/Swagger
    specs, an `/api-docs` path) -- narrow on purpose: these markers are
    widely-adopted conventions, not a guess about any specific source.
    """
    parser = _parse_page(html)
    candidates = []
    seen: set[str] = set()
    for a in parser.anchors:
        href = a["href"]
        if not any(marker in href.lower() for marker in _API_DOC_MARKERS):
            continue
        url = urljoin(page_url, href)
        if url in seen:
            continue
        seen.add(url)
        candidates.append(
            SourceCandidate(
                discovered_url=url,
                origin_page_url=page_url,
                discovery_method=DiscoveryMethod.API_DOCUMENTATION_SCAN,
                access_method_guess=AccessMethod.JSON_API,
                evidence=f'<a href="{href}">',
            )
        )
    return candidates


COMPANY_NAME_STOPWORDS = {
    "company", "companies", "group", "holding", "holdings", "egypt", "egyptian",
    "co", "corp", "corporation", "the", "for", "of", "and", "sae", "s.a.e",
    "production", "production.",
}


def significant_tokens(name: str) -> set[str]:
    """Public (not `discover_company_directory_links`-private) because
    `discovery.wikidata_lookup` reuses the exact same name-token-overlap
    matching discipline against a different page shape (SPARQL result
    labels instead of anchor text) -- same rule, one definition.
    """
    normalized = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    return {tok for tok in normalized.split() if tok and tok not in COMPANY_NAME_STOPWORDS}


def discover_company_directory_links(
    html: str, page_url: str, companies: dict[str, str]
) -> dict[str, str]:
    """Find each company's own homepage link on an already-fetched directory
    page (e.g. an exchange's official list of listed companies) by matching
    anchor text against `companies` (ticker -> display name).

    Never guesses a company's domain: a match requires every one of the
    company name's significant tokens (common corporate suffixes like
    "Company"/"Group"/"Holding"/"Egypt" excluded) to literally appear in an
    anchor's visible text on a page that was actually fetched. This is the
    mechanism that lets Priority 1 (the exchange itself) supply real
    per-company hints for Priority 2/3 (company Investor Relations) once
    the exchange's site is reachable, instead of guessing ~100 corporate
    domains from training-data recall.

    Returns ticker -> resolved absolute URL for every company matched (at
    most once each -- the first anchor found wins, for determinism).
    """
    parser = _parse_page(html)
    significant = {ticker: significant_tokens(name) for ticker, name in companies.items()}
    found: dict[str, str] = {}

    for anchor in parser.anchors:
        text_tokens = significant_tokens(anchor.get("text", ""))
        if not text_tokens:
            continue
        for ticker, tokens in significant.items():
            if ticker in found or not tokens:
                continue
            if tokens.issubset(text_tokens):
                found[ticker] = urljoin(page_url, anchor["href"])

    return found


def is_sitemap_index(sitemap_xml: str) -> bool:
    """A sitemap-index (<sitemapindex> root, per the sitemaps.org protocol)
    lists further sitemap.xml files, not final content URLs -- the caller
    (the network-touching orchestration layer) must fetch and re-scan each
    <loc> entry rather than treat it as a discovered candidate itself. See
    docs/TECHNICAL_DEBT.md TD-18.
    """
    return "<sitemapindex" in sitemap_xml.lower()


def discover_sitemap_urls(sitemap_xml: str, page_url: str) -> list[SourceCandidate]:
    """Minimal <loc> extraction from a sitemap.xml -- a lightweight generic
    parse rather than a full XML sitemap schema, since the only thing this
    engine needs is the list of candidate URLs it points to. Each entry's
    access method is guessed mechanically from its file extension using the
    same mapping `discover_structured_datasets` uses (CSV/XLS/JSON/XML);
    anything else is left as an ordinary page URL (HTML_SCRAPE) -- a sitemap
    entry is never assumed to be a feed just because it was reachable via a
    sitemap.

    The sitemaps.org spec requires every <loc> to be a fully-qualified
    absolute URL, but a real-world sitemap isn't guaranteed to comply (a
    live run against a real site's real sitemap crashed downstream --
    `robots_status()` building `f"{scheme}://{netloc}/robots.txt"` from a
    <loc> entry with neither -- because this function trusted the spec
    instead of verifying it). `urljoin` resolves a relative/malformed entry
    against the sitemap's own URL the same way every other discovery
    function already resolves a page's relative hrefs; an entry that still
    has no scheme+netloc after that (empty, a bare fragment, anything not a
    real URL) is skipped rather than turned into a candidate no caller could
    safely fetch.
    """
    urls = re.findall(r"<loc>(.*?)</loc>", sitemap_xml, flags=re.IGNORECASE | re.DOTALL)
    candidates = []
    for raw_url in urls:
        stripped = raw_url.strip()
        if not stripped:
            continue
        url = urljoin(page_url, stripped)
        parsed = urlsplit(url)
        if not parsed.scheme or not parsed.netloc:
            continue
        path = parsed.path.lower()
        access_method_guess = AccessMethod.HTML_SCRAPE
        for ext, access_method in _STRUCTURED_EXTENSIONS.items():
            if path.endswith(ext):
                access_method_guess = access_method
                break
        candidates.append(
            SourceCandidate(
                discovered_url=url,
                origin_page_url=page_url,
                discovery_method=DiscoveryMethod.SITEMAP_SCAN,
                access_method_guess=access_method_guess,
                evidence="<loc> entry in sitemap.xml",
            )
        )
    return candidates


class DiscoveryEngine:
    """Aggregates every discovery heuristic over a page and dedups by URL.

    Takes already-fetched HTML (caller owns fetching via `HttpFetcher`, which
    already enforces robots.txt/rate limits) -- discovery never fetches on
    its own, so it never bypasses the platform's fetch policy.
    """

    def scan_page(self, html: str, page_url: str) -> list[SourceCandidate]:
        candidates = [
            *discover_rss_feeds(html, page_url),
            *discover_pdf_repository(html, page_url),
            *discover_structured_datasets(html, page_url),
            *discover_api_documentation(html, page_url),
        ]
        return self._dedup(candidates)

    def scan_sitemap(self, sitemap_xml: str, page_url: str) -> list[SourceCandidate]:
        return self._dedup(discover_sitemap_urls(sitemap_xml, page_url))

    def scan_financial_documents(
        self, html: str, page_url: str
    ) -> list[tuple[SourceCandidate, FinancialDocumentCategory]]:
        found = discover_financial_documents(html, page_url)
        seen: set[str] = set()
        result = []
        for candidate, category in found:
            fp = candidate.fingerprint()
            if fp not in seen:
                seen.add(fp)
                result.append((candidate, category))
        return result

    @staticmethod
    def _dedup(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
        seen: set[str] = set()
        result = []
        for candidate in candidates:
            fp = candidate.fingerprint()
            if fp not in seen:
                seen.add(fp)
                result.append(candidate)
        return result
