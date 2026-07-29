"""Resumable EGX30+EGX70 Financial Source Registry builder (TD-39).

Usage: uv run python scripts/build_financial_source_registry.py [--data-dir DIR]

Reads the reviewed universe snapshots (`data/universe/EGX30.csv`/`EGX70.csv`)
and whatever evidenced domain hints exist today (`egx30_web_search_domain_hints.json`,
TD-38), attempts one real discovery pass per not-yet-`VALIDATED` company
(`discovery.company_financial_discovery.discover_company_financial_sources`),
and persists results into `CompanyFinancialSourceRegistry`
(`<data-dir>/company_financial_sources.json`).

Safe to re-run: `VALIDATED` companies are skipped ("never restart completed
work, resume from the last validated company"); everything else
(`PENDING`/`HOMEPAGE_UNRESOLVED`/`BLOCKED`) is always re-attempted, since a
later run -- e.g. with network egress this sandbox may lack, see TD-39 --
might succeed where this one couldn't. A company with no evidenced homepage
hint is recorded `HOMEPAGE_UNRESOLVED`, never given a guessed domain.

Writes a coverage summary (`company_financial_sources_summary.json`)
alongside the registry every run.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from agx_research.collectors.fetcher import HttpFetcher
from agx_research.discovery.company_financial_discovery import discover_company_financial_sources
from agx_research.discovery.company_financial_registry import (
    CompanyFinancialSourceRecord,
    CompanyFinancialSourceRegistry,
    CompanyRegistryStatus,
)
from agx_research.discovery.web_search_hints import load_web_search_domain_hints

_UNIVERSE_DIR = Path(__file__).resolve().parent.parent / "data" / "universe"
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "registry"

_UNRESOLVED_REASON = "No evidenced homepage hint available yet (see TD-38/TD-39)."


def _read_universe_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    data_dir = Path(argv[argv.index("--data-dir") + 1]) if "--data-dir" in argv else _DEFAULT_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)

    registry = CompanyFinancialSourceRegistry(data_dir / "company_financial_sources.json")
    fetcher = HttpFetcher()
    hints = load_web_search_domain_hints(_UNIVERSE_DIR / "egx30_web_search_domain_hints.json")

    companies: list[tuple[str, dict]] = []
    for index_name, filename in (("EGX30", "EGX30.csv"), ("EGX70", "EGX70.csv")):
        for row in _read_universe_csv(_UNIVERSE_DIR / filename):
            companies.append((index_name, row))

    processed = 0
    skipped = 0
    for index_name, row in companies:
        ticker = row["ticker"].strip()
        if registry.is_resumable_skip(ticker):
            skipped += 1
            continue

        existing = registry.latest(ticker)
        index_membership = sorted(set((existing.index_membership if existing else []) + [index_name]))
        record = CompanyFinancialSourceRecord(
            id=ticker,
            ticker=ticker,
            company_name=row["company_name"].strip(),
            isin=(row.get("isin") or "").strip() or None,
            index_membership=index_membership,
        )

        hostname = hints.get(ticker)
        if hostname is None:
            result = record.model_copy(update={
                "status": CompanyRegistryStatus.HOMEPAGE_UNRESOLVED,
                "blocked_reason": _UNRESOLVED_REASON,
            })
        else:
            result = discover_company_financial_sources(fetcher, record, f"https://{hostname}")
            result = result.model_copy(update={"homepage_hint_source": "web_search"})

        registry.record(result)
        processed += 1
        detail = f" -- {result.blocked_reason}" if result.blocked_reason else ""
        print(f"{ticker} ({index_name}): {result.status.value}{detail}")

    summary = {
        "companies_total": len(companies),
        "processed_this_run": processed,
        "skipped_already_validated": skipped,
        "by_status": {status.value: len(registry.by_status(status)) for status in CompanyRegistryStatus},
        "documents_discovered_total": sum(len(r.documents) for r in registry.all_latest()),
    }
    (data_dir / "company_financial_sources_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
