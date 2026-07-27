"""Wikidata official-website lookup: a free, structured, no-key alternative
path to a real EGX30/EGX70 constituent's own homepage that does not depend
on `egx_official` being reachable.

`acquisition_intelligence.target.generate_company_ir_targets`'s docstring
names two honest paths to a real per-company domain hint: the company's
own public disclosure, or `discover_company_directory_links` reading an
already-resolved directory homepage (e.g. EGX's own listed-companies page).
This module is a third, independent path: Wikidata's own declared `P856`
("official website") property for an entity, queried through its public,
documented, no-key SPARQL endpoint -- the same confidence tier as the
Wayback Machine APIs `acquisition_intelligence.historical` already uses for
verification, and reusable even while `egx_official` itself stays
unreachable, since it never depends on the exchange's own site at all.

Matching reuses `discovery.engine.significant_tokens`'s exact name-token-
overlap discipline (no duplicated matching logic, same rule everywhere): a
match still requires every significant token of a company's known display
name to appear in a label Wikidata itself returned for a real P856 hit.
A result here still only becomes a `domain_hints` entry -- it is always
re-probed independently by
`acquisition_intelligence.domain_resolution.HeuristicDomainResolver` before
anything is trusted (AD-24 holds unchanged); this module never asserts a
company's domain, only reports what a real, already-fetched Wikidata
response actually contained.
"""

from __future__ import annotations

from typing import Callable
from urllib.parse import quote, urlsplit

from agx_research.discovery.engine import significant_tokens

FetchJson = Callable[[str], object]

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Q79 = Egypt (P17 = country of the entity); Q4830453 = business (P31/P279*
# = instance of a subclass of business) -- both stable, widely-documented
# Wikidata IDs, not a guess. SERVICE wikibase:label pulls each hit's best
# English label so it can be matched against `companies`' display names.
EGYPT_COMPANIES_WEBSITES_QUERY = """
SELECT ?companyLabel ?website WHERE {
  ?company wdt:P17 wd:Q79.
  ?company wdt:P31/wdt:P279* wd:Q4830453.
  ?company wdt:P856 ?website.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
""".strip()


def build_wikidata_query_url(query: str = EGYPT_COMPANIES_WEBSITES_QUERY) -> str:
    return f"{WIKIDATA_SPARQL_ENDPOINT}?query={quote(query)}&format=json"


def parse_wikidata_company_websites(payload: dict) -> dict[str, str]:
    """`payload` is the SPARQL endpoint's own JSON response shape
    (`results.bindings`, each a `{"companyLabel": {"value": ...}, "website":
    {"value": ...}}` dict per the SPARQL 1.1 Query Results JSON Format).
    A binding missing either field is skipped, not guessed at -- only a
    real response's actual shape is trusted.
    """
    websites: dict[str, str] = {}
    for binding in (payload.get("results") or {}).get("bindings", []):
        label = (binding.get("companyLabel") or {}).get("value")
        website = (binding.get("website") or {}).get("value")
        if label and website:
            websites[label] = website
    return websites


def match_wikidata_websites_to_companies(
    labels_to_websites: dict[str, str], companies: dict[str, str]
) -> dict[str, str]:
    """Ticker -> hostname (homepage-level, matching every other
    `domain_hints` value in `acquisition_intelligence`) for the first
    Wikidata label matching each company's known display name by
    significant-token overlap -- identical discipline to
    `discover_company_directory_links`, applied to SPARQL result labels
    instead of anchor text.
    """
    significant = {ticker: significant_tokens(name) for ticker, name in companies.items()}
    found: dict[str, str] = {}
    for label, website in labels_to_websites.items():
        label_tokens = significant_tokens(label)
        if not label_tokens:
            continue
        for ticker, tokens in significant.items():
            if ticker in found or not tokens:
                continue
            if tokens.issubset(label_tokens):
                hostname = urlsplit(website).netloc
                if hostname:
                    found[ticker] = hostname
    return found


class WikidataOfficialWebsiteClient:
    def __init__(self, fetch_json: FetchJson):
        self.fetch_json = fetch_json

    def lookup(self, companies: dict[str, str]) -> dict[str, str]:
        """Ticker -> hostname for every company in `companies` that a real
        Wikidata SPARQL response both reports a `P856` official website for
        and whose label matches. Returns `{}` (never raises) if the
        endpoint is unreachable or the response is empty/malformed -- the
        same honest degrade-to-no-hint every other network-dependent step
        in this package uses; callers fall back to whatever other hint
        source (or none) they already had.
        """
        payload = self.fetch_json(build_wikidata_query_url())
        if not isinstance(payload, dict):
            return {}
        labels_to_websites = parse_wikidata_company_websites(payload)
        return match_wikidata_websites_to_companies(labels_to_websites, companies)
