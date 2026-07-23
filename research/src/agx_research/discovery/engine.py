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

from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from agx_research.discovery.candidate import DiscoveryMethod, SourceCandidate
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
    """Collects every <a href> and <link rel=alternate> on a page in one pass."""

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        if tag == "a" and attr_dict.get("href"):
            self.anchors.append(attr_dict)
        elif tag == "link" and attr_dict.get("href"):
            self.links.append(attr_dict)


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


def discover_sitemap_urls(sitemap_xml: str, page_url: str) -> list[SourceCandidate]:
    """Minimal <loc> extraction from a sitemap.xml -- a lightweight generic
    parse rather than a full XML sitemap schema, since the only thing this
    engine needs is the list of candidate URLs it points to.
    """
    import re

    urls = re.findall(r"<loc>(.*?)</loc>", sitemap_xml, flags=re.IGNORECASE | re.DOTALL)
    return [
        SourceCandidate(
            discovered_url=url.strip(),
            origin_page_url=page_url,
            discovery_method=DiscoveryMethod.SITEMAP_SCAN,
            access_method_guess=AccessMethod.HTML_SCRAPE,
            evidence="<loc> entry in sitemap.xml",
        )
        for url in urls
        if url.strip()
    ]


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
