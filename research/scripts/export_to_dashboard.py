#!/usr/bin/env python3
"""
export_to_dashboard.py
======================
Copies all generated artifacts from research/data/dashboard/
to web/public/data/ so the static site serves them.

Also copies:
  - macro_snapshot.json     → web/public/data/macro_snapshot.json
  - prices manifest         → web/public/data/prices_manifest.json

Run this AFTER:
  1. fetch_live_prices.py
  2. fetch_macro_data.py
  3. build_decision_engine.py
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent   # EGX-Genom root
RESEARCH    = ROOT / "research"
DASHBOARD   = RESEARCH / "data" / "dashboard"
MACRO       = RESEARCH / "data" / "macro"
PRICES_DIR  = RESEARCH / "data" / "prices"
WEB_PUBLIC  = ROOT / "web" / "public" / "data"
WEB_PUBLIC.mkdir(parents=True, exist_ok=True)

# All dashboard JSON artifacts to copy
DASHBOARD_ARTIFACTS = [
    "acquisition_decisions.json",
    "claims.json",
    "collector_status.json",
    "committee_summary.json",
    "dashboard_metrics.json",
    "decision_history.json",
    "decision_performance.json",
    "decision_readiness.json",
    "events.json",
    "execution_report.json",
    "financial_coverage.json",
    "financial_statements.json",
    "genes.json",
    "hypotheses.json",
    "investment_cases.json",
    "knowledge.json",
    "knowledge_graph.json",
    "market_breadth.json",
    "market_regime.json",
    "market_state.json",
    "mission_status.json",
    "papers.json",
    "patterns.json",
    "portfolio_summary.json",
    "recommendations.json",
    "runtime_metrics.json",
    "runtime_status.json",
    "shadow_fund.json",
    "shadow_fund_history.json",
    "source_metrics.json",
    "source_registry.json",
    "source_truth.json",
    "system_maturity.json",
    "system_status.json",
    "ticker_data_gap_report.json",
    "universe.json",
    "warnings.json",
]


def copy_artifact(src: Path, dst: Path) -> tuple[bool, str]:
    if not src.exists():
        return False, "NOT FOUND"
    try:
        shutil.copy2(src, dst)
        size = dst.stat().st_size
        return True, f"{size:,} bytes"
    except Exception as e:
        return False, str(e)


def build_export_manifest(copied: list, skipped: list) -> dict:
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_artifacts": len(DASHBOARD_ARTIFACTS),
        "copied": len(copied),
        "skipped": len(skipped),
        "files": copied,
        "missing": skipped,
    }


def main():
    print("=== EGX Dashboard Export ===\n")
    print(f"Source: {DASHBOARD}")
    print(f"Target: {WEB_PUBLIC}\n")

    copied = []
    skipped = []

    # ── 1. Copy all dashboard artifacts ──────────────────────────────────
    for artifact in DASHBOARD_ARTIFACTS:
        src = DASHBOARD / artifact
        dst = WEB_PUBLIC / artifact
        ok, info = copy_artifact(src, dst)
        if ok:
            print(f"  [OK]  {artifact:45s} {info}")
            copied.append(artifact)
        else:
            print(f"  [--]  {artifact:45s} {info}")
            skipped.append(artifact)

    # ── 2. Copy macro snapshot ────────────────────────────────────────────
    macro_src = MACRO / "macro_snapshot.json"
    macro_dst = WEB_PUBLIC / "macro_snapshot.json"
    ok, info = copy_artifact(macro_src, macro_dst)
    print(f"\n  [{'OK' if ok else '--'}]  macro_snapshot.json{' '*26} {info}")
    if ok:
        copied.append("macro_snapshot.json")
    else:
        skipped.append("macro_snapshot.json")

    # ── 3. Copy prices manifest if it exists ─────────────────────────────
    manifest_src = PRICES_DIR / "_manifest.json"
    if manifest_src.exists():
        manifest_dst = WEB_PUBLIC / "prices_manifest.json"
        shutil.copy2(manifest_src, manifest_dst)
        print(f"  [OK]  prices_manifest.json")
        copied.append("prices_manifest.json")

    # ── 4. Validate key decision files ───────────────────────────────────
    print("\n=== Validation ===")
    for key_file in ["recommendations.json", "market_breadth.json", "market_regime.json",
                     "macro_snapshot.json", "decision_readiness.json", "acquisition_decisions.json"]:
        path = WEB_PUBLIC / key_file
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                count = len(data)
                status = f"{count} records" + (" [EMPTY!]" if count == 0 else " [OK]")
            elif isinstance(data, dict):
                status = f"dict with {len(data)} keys [OK]"
            else:
                status = "unknown format"
            print(f"  {key_file:45s} {status}")
        else:
            print(f"  {key_file:45s} MISSING")

    # ── 5. Save export manifest ───────────────────────────────────────────
    manifest = build_export_manifest(copied, skipped)
    manifest_path = WEB_PUBLIC / "export_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n=== DONE ===")
    print(f"Copied:  {len(copied)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    main()
