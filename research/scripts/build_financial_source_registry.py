"""Resumable EGX30+EGX70 Financial Source Registry builder (TD-39, TD-66).

Usage: uv run python scripts/build_financial_source_registry.py [--data-dir DIR]

Reads the reviewed universe snapshots (`data/universe/EGX30.csv`/`EGX70.csv`)
and runs `discovery.company_entity_resolution.EntityResolutionEngine`'s full
multi-strategy resolution (web-search snapshot + live Wikidata + live GLEIF,
in that confidence order, all three contributing candidates rather than one
strategy silently winning) for every not-yet-`VALIDATED` company, then
persists results into `CompanyFinancialSourceRegistry`
(`<data-dir>/company_financial_sources.json`).

Multi-strategy, not single-strategy (TD-66): before this, this script only
ever consulted the static `egx30_web_search_domain_hints.json` snapshot --
`WikidataOfficialWebsiteClient` existed and was tested but was never wired
in here, so a company whose only real hint was a Wikidata `P856` claim was
recorded `HOMEPAGE_UNRESOLVED` even though a real hint existed. Now every
company gets every strategy's candidates, in confidence order, so
`HeuristicDomainResolver` (inside the engine, unchanged) has a real
fallback chain rather than a single hint. `GleifLegalEntityClient` adds a
capability this script never had before: a company's canonical legal name
and known aliases, independent of whether its website resolves at all.

Safe to re-run: `VALIDATED` companies are skipped ("never restart completed
work, resume from the last validated company"); everything else
(`PENDING`/`HOMEPAGE_UNRESOLVED`/`BLOCKED`) is always re-attempted, since a
later run -- e.g. with network egress this sandbox may lack, see TD-39 --
might succeed where this one couldn't. A company no strategy produces a
reachable domain for is recorded `HOMEPAGE_UNRESOLVED`, never given a
guessed domain.

Writes a coverage summary (`company_financial_sources_summary.json`)
alongside the registry every run, now including a per-strategy website-
resolution breakdown and the legal-entity resolution rate.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from agx_research.acquisition_intelligence.domain_resolution import HeuristicDomainResolver
from agx_research.acquisition_intelligence.live import (
    build_live_gleif_client,
    build_live_prober,
    build_live_wikidata_client,
)
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.discovery.company_entity_resolution import EntityResolutionEngine
from agx_research.discovery.company_financial_registry import (
    CompanyFinancialSourceRegistry,
    CompanyRegistryStatus,
)
from agx_research.discovery.resolution_memory import ResolutionMemory
from agx_research.discovery.web_search_hints import (
    WebSearchHintStrategy,
    load_web_search_domain_hints,
)

_UNIVERSE_DIR = Path(__file__).resolve().parent.parent / "data" / "universe"
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "registry"


def _read_universe_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    data_dir = Path(argv[argv.index("--data-dir") + 1]) if "--data-dir" in argv else _DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)

    registry = CompanyFinancialSourceRegistry(data_dir / "company_financial_sources.json")
    resolution_memory = ResolutionMemory(data_dir / "resolution_memory.json")
    fetcher = HttpFetcher()
    web_search_hints = load_web_search_domain_hints(_UNIVERSE_DIR / "egx30_web_search_domain_hints.json")

    engine = EntityResolutionEngine(
        # Confidence order: Wikidata first (independently machine-verifiable
        # structured data), then the reviewed web-search snapshot -- matches
        # cli.py discover-sources's existing preference, generalized here to
        # keep both candidates instead of discarding the loser.
        website_strategies=[
            build_live_wikidata_client(),
            WebSearchHintStrategy(web_search_hints),
        ],
        legal_entity_client=build_live_gleif_client(),
        domain_resolver=HeuristicDomainResolver(build_live_prober(fetcher)),
        fetcher=fetcher,
    )

    companies: dict[str, str] = {}
    index_membership_by_ticker: dict[str, set[str]] = {}
    isin_by_ticker: dict[str, str | None] = {}
    for index_name, filename in (("EGX30", "EGX30.csv"), ("EGX70", "EGX70.csv")):
        for row in _read_universe_csv(_UNIVERSE_DIR / filename):
            ticker = row["ticker"].strip()
            companies[ticker] = row["company_name"].strip()
            index_membership_by_ticker.setdefault(ticker, set()).add(index_name)
            isin_by_ticker[ticker] = (row.get("isin") or "").strip() or None

    existing_records = {ticker: rec for ticker in companies if (rec := registry.latest(ticker)) is not None}
    skipped = sum(1 for r in existing_records.values() if r.status == CompanyRegistryStatus.VALIDATED)

    report = engine.resolve(companies, existing_records=existing_records)

    for record in report.records:
        existing = existing_records.get(record.ticker)
        index_membership = sorted(
            (set(existing.index_membership) if existing else set())
            | index_membership_by_ticker.get(record.ticker, set())
        )
        # A GLEIF miss this run (rate-limited, transient failure, no match)
        # must not erase a legal name/alias set a previous run already
        # resolved -- carry the existing value forward unless this run
        # found something new to replace it with.
        result = record.financial_record.model_copy(
            update={
                "isin": isin_by_ticker.get(record.ticker),
                "index_membership": index_membership,
                "legal_name": record.legal_name or (existing.legal_name if existing else None),
                "legal_name_source": record.legal_name_source or (existing.legal_name_source if existing else None),
                "aliases": record.aliases or (existing.aliases if existing else []),
                "lei": record.lei or (existing.lei if existing else None),
            }
        )
        registry.record(result)
        # Persisted regardless of outcome -- a rejected domain or a GLEIF
        # miss this run is still permanent knowledge, not discarded the
        # moment `result` is computed. See discovery.resolution_memory's
        # module docstring for why this is a separate store from `registry`
        # rather than folded into `CompanyFinancialSourceRecord`.
        if record.resolution_memory is not None:
            resolution_memory.record(record.resolution_memory)
        detail = f" -- {result.blocked_reason}" if result.blocked_reason else ""
        legal = f" [legal_name via {record.legal_name_source}]" if record.legal_name else ""
        print(f"{record.ticker}: {result.status.value}{detail}{legal}")

    summary = {
        "companies_total": len(companies),
        "processed_this_run": report.total,
        "skipped_already_validated": skipped,
        "by_status": {status.value: len(registry.by_status(status)) for status in CompanyRegistryStatus},
        "documents_discovered_total": sum(len(r.documents) for r in registry.all_latest()),
        "website_resolution_rate": round(report.website_resolution_rate, 4),
        "website_resolutions_by_source": report.website_resolutions_by_source(),
        "legal_name_resolution_rate": round(report.legal_name_resolution_rate, 4),
        "ir_entry_point_resolution_rate": round(report.ir_entry_point_resolution_rate, 4),
    }
    (data_dir / "company_financial_sources_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
