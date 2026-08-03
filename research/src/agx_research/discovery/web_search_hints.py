"""A third, independent `domain_hints` source for
`acquisition_intelligence.target.generate_company_ir_targets()`, alongside
`discovery.wikidata_lookup.WikidataOfficialWebsiteClient` and
`discover_company_directory_links()` (see `docs/TECHNICAL_DEBT.md` TD-38).

Unlike those two, this one is not a live network call: it reads a reviewed,
evidenced JSON snapshot (`research/data/universe/egx30_web_search_domain_hints.json`)
produced by a real web search for each company's own name, the same category
of "public disclosure, not a guess" input `target.generate_company_ir_targets`'s
own docstring already names as an honest hint source. Nothing here is ever
trusted directly downstream: `acquisition_intelligence.domain_resolution.
HeuristicDomainResolver` still independently probes every hint for
reachability before treating it as a real domain, exactly like every other
`domain_hints` entry.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_web_search_domain_hints(path: Path | str) -> dict[str, str]:
    """Ticker -> hostname for every entry in the reviewed hints file.

    Returns an empty dict (never raises) if `path` doesn't exist, so a
    missing or not-yet-collected hints file degrades the same honest way
    every other optional hint source in this package already does --
    "no hint", not an error.
    """
    file_path = Path(path)
    if not file_path.exists():
        return {}
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    hints = payload.get("hints") or {}
    return {
        ticker: entry["hostname"]
        for ticker, entry in hints.items()
        if isinstance(entry, dict) and entry.get("hostname")
    }


class WebSearchHintStrategy:
    """Adapts `load_web_search_domain_hints`'s static snapshot to the
    `discovery.company_entity_resolution.WebsiteHintStrategy` shape, so it
    can be composed alongside `WikidataOfficialWebsiteClient` and any
    other live strategy in one `EntityResolutionEngine` instead of being
    special-cased at each call site."""

    name = "web_search"

    def __init__(self, hints: dict[str, str]):
        self._hints = hints

    def lookup(self, companies: dict[str, str]) -> dict[str, str]:
        return {ticker: hostname for ticker, hostname in self._hints.items() if ticker in companies}
