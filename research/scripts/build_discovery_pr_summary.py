"""Render the weekly Discovery workflow's PR body from its own committed
JSON artifacts -- a pure formatting step, never a second source of truth
about what the run found. Used only by `.github/workflows/discovery.yml`.

Usage: uv run python scripts/build_discovery_pr_summary.py <discovery-dir> <output.md>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    discovery_dir, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    metrics = json.loads((discovery_dir / "discovery_metrics.json").read_text())
    report = json.loads((discovery_dir / "discovery_report.json").read_text())

    verified = [r for r in report if r["verification_result"] == "verified_reachable"]
    ready_for_a_maintainer = [r for r in verified if "flip status to IMPLEMENTED" in r["recommendation"]]
    not_targeted = [r for r in report if r["verification_result"] == "not_targeted"]

    lines = [
        "## Weekly Source Discovery",
        "",
        "Automated, evidenced run of the Acquisition Intelligence Engine against every "
        "`PLANNED`/`CANDIDATE` catalogued source with a `TargetOrganization`. Nothing here "
        "flips a source to `IMPLEMENTED` or edits `sources/catalog.py` -- that stays a "
        "reviewed, manual step (see `docs/DATA_ACQUISITION.md`'s Discovery workflow section).",
        "",
        f"- Sources in report: **{metrics['sources_in_report']}**",
        f"- Checked fresh this run: **{metrics['sources_checked_fresh_this_run']}**",
        f"- Served from cache (still within TTL): **{metrics['sources_served_from_cache']}**",
        f"- Verified reachable: **{metrics['sources_verified_reachable']}**",
        f"- Not yet targeted (no `TargetOrganization` entry): **{len(not_targeted)}**",
        "",
    ]

    if ready_for_a_maintainer:
        lines.append("### Newly verified -- ready for a maintainer to review")
        lines.append("")
        for row in ready_for_a_maintainer:
            lines.append(
                f"- `{row['source_id']}`: {row['discovered_endpoints'][0]} "
                f"(confidence {row['confidence']:.2f})"
            )
        lines.append("")
    elif verified:
        lines.append("### Verified this run (no ready generic collector yet)")
        lines.append("")
        for row in verified:
            lines.append(f"- `{row['source_id']}`: {row['discovered_endpoints'][0]}")
        lines.append("")
    else:
        lines.append("No source newly cleared verification this run.")
        lines.append("")

    lines.append("Full evidence per source: `research/data/discovery/discovery_report.json`.")
    lines.append("Every ranked candidate considered (not just winners): "
                 "`research/data/discovery/endpoint_candidates.json`.")

    registry_summary_path = discovery_dir.parent / "registry" / "company_financial_sources_summary.json"
    if registry_summary_path.exists():
        registry_summary = json.loads(registry_summary_path.read_text())
        by_status = registry_summary["by_status"]
        lines += [
            "",
            "### EGX30/EGX70 Financial Source Registry (TD-39)",
            "",
            f"- Companies total: **{registry_summary['companies_total']}**",
            f"- Discovered (>=1 categorized financial document found): **{by_status.get('discovered', 0)}**",
            f"- Validated (discovered + reviewed): **{by_status.get('validated', 0)}**",
            f"- Blocked (fetch failed or nothing categorizable): **{by_status.get('blocked', 0)}**",
            f"- Homepage unresolved (no evidenced domain hint yet): **{by_status.get('homepage_unresolved', 0)}**",
            f"- Financial documents discovered total: **{registry_summary['documents_discovered_total']}**",
            "",
            "Full per-company detail: `research/data/registry/company_financial_sources.json`.",
        ]

    out_path.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
