"""The AGX command-line entry point: `python -m agx_research.cli ...`.

Transport/operations only — every research decision lives in the modules
this invokes. Reviewed universe snapshots are ingested into `--data-dir`,
then the collected-data provider is the only membership source read by the
pipeline. The stores persist so runs accumulate and are replayable.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from agx_research.acquisition_intelligence.continuity import AcquisitionContinuityMonitor
from agx_research.acquisition_intelligence.engine import AcquisitionIntelligenceEngine
from agx_research.acquisition_intelligence.live import (
    build_live_fetch_text,
    build_live_prober,
    build_live_robots_checker,
    build_live_wayback_client,
)
from agx_research.acquisition_intelligence.target import (
    generate_company_ir_targets,
    seed_target_organizations,
)
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.collectors.raw import RawDocumentRepository
from agx_research.collectors.fred import FredCsvCollector
from agx_research.collectors.rss import RssNewsCollector
from agx_research.collectors.service import CollectionService
from agx_research.collectors.stooq import StooqPriceCollector
from agx_research.dashboard import validate_dashboard_artifacts, write_dashboard_artifacts
from agx_research.dashboard.validate import DashboardArtifactError
from agx_research.data.mock_provider import MockDataProvider
from agx_research.events.repository import EventRepository
from agx_research.events.service import EventPlatform
from agx_research.infrastructure.backup import create_backup, restore_backup, verify_backup
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory
from agx_research.meta.decision_ledger import DecisionLedger
from agx_research.meta.publication_gate import (
    ExternalPublicationEvidence,
    LegalPublicationApproval,
    evaluate_publication_gate,
)
from agx_research.production import ExecutionMode, ProductionPipeline, StageStatus
from agx_research.runtime.engine import RunRecordRepository
from agx_research.sources.catalog import seed_registry
from agx_research.sources.registry import SourceRegistry
from agx_research.universe.bootstrap import materialize_universe_seed
from agx_research.universe.collected import CollectedUniverseProvider
from agx_research.universe.sector import StaticSectorProvider

_DEFAULT_MOCK_DATA = Path(__file__).resolve().parents[2] / "data" / "mock"
_DEFAULT_UNIVERSE_SEED = Path(__file__).resolve().parents[2] / "data" / "universe"

MACRO_SERIES_IDS = ["BRENT_USD", "EGP_USD"]


def build_market_memory(data_dir: Path, mock_data: Path) -> MarketMemory:
    """Used by `export-dashboard`/`status`-adjacent subcommands that read
    the static `--mock-data` fixture directory directly. The full production
    pipeline (`run`, see `production.pipeline.ProductionPipeline`) builds its
    own `MarketMemory` pointed at `--data-dir` instead, since that's where
    its own Collector Execution stage materializes data -- the whole point
    of the production pipeline is that collected data is what research
    actually reads, which this narrower helper's fixed `mock_data` source
    can't provide.
    """
    return MarketMemory(
        MockDataProvider(mock_data),
        CollectedUniverseProvider(data_dir),
        StaticSectorProvider(),
        macro_series_ids=MACRO_SERIES_IDS,
        lookback_days=30,
        event_platform=EventPlatform(repository=EventRepository(data_dir / "events.json")),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agx", description="AGX research platform runtime")
    parser.add_argument("--data-dir", type=Path, default=Path("agx_data"))
    parser.add_argument("--mock-data", type=Path, default=_DEFAULT_MOCK_DATA)
    parser.add_argument(
        "--universe-seed-dir",
        type=Path,
        default=_DEFAULT_UNIVERSE_SEED,
        help="Reviewed CSV snapshots to ingest into <data-dir>/universe before use",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser(
        "run",
        help="Run the complete production pipeline end to end: source registry -> discovery -> "
        "collector selection/execution -> raw archive -> canonical transformation -> validation -> "
        "event platform -> market memory -> knowledge base -> research pipeline -> genome -> "
        "investment case generator -> dashboard artifacts -> Mission Control -> execution report",
    )
    run_parser.add_argument("--date", required=True, help="ISO date, e.g. 2026-06-14")
    run_parser.add_argument("--end-date", help="Optional ISO end date for a range")
    run_parser.add_argument(
        "--mode",
        choices=["live", "mock", "replay"],
        default="live",
        help="live: fetch real data from the network (default, production mode) -- Stooq/FRED/"
        "World Bank against real endpoints, real robots.txt/rate-limit/retry; a source with no "
        "verified live endpoint (EGX official, company IR, news outlets, ...) reports UNAVAILABLE "
        "with its reason rather than being silently skipped, and every other collector keeps "
        "running regardless. mock/replay are TESTING-ONLY and must never be used by a production "
        "deployment: mock fetches through synthetic-but-real-wire-format fixtures; replay re-runs "
        "the exact same pipeline against already-archived RawDocuments from a prior run in this "
        "--data-dir, proving the pipeline cannot tell live data from replayed data.",
    )
    run_parser.add_argument(
        "--dashboard-out",
        type=Path,
        help="Where to write dashboard/Mission Control/execution-report JSON artifacts "
        "(default: <data-dir>/dashboard)",
    )

    sub.add_parser("status", help="Show run ledger and knowledge summary")

    backup_parser = sub.add_parser("backup", help="Create an integrity-checked backup")
    backup_parser.add_argument("--output", type=Path, required=True)

    verify_parser = sub.add_parser("verify-backup", help="Verify a backup's integrity")
    verify_parser.add_argument("--input", type=Path, required=True)

    restore_parser = sub.add_parser("restore", help="Restore a verified backup")
    restore_parser.add_argument("--input", type=Path, required=True)
    restore_parser.add_argument("--target", type=Path, required=True)

    collect_parser = sub.add_parser(
        "collect", help="Run a single IMPLEMENTED source's collector and materialize its data"
    )
    collect_parser.add_argument(
        "--source", required=True, help="Source id, e.g. stooq, fred, rss_generic"
    )
    collect_parser.add_argument(
        "--symbols", help="stooq only: AGX_TICKER=stooq_symbol,... e.g. COMI=comi.eg,MFPC=mfpc.eg"
    )
    collect_parser.add_argument("--series", help="fred only: comma-separated FRED series ids")
    collect_parser.add_argument("--feed-url", help="rss_generic only: the feed URL to collect")
    collect_parser.add_argument(
        "--ticker-hints", help="rss_generic only: comma-separated tickers to match"
    )
    collect_parser.add_argument("--expected-records", type=int, required=True)
    collect_parser.add_argument("--min-confidence", type=float, default=0.5)

    discover_parser = sub.add_parser(
        "discover-sources",
        help="Run the Acquisition Intelligence Engine against the target-organization "
        "catalog: resolve a domain, discover candidate acquisition methods, verify "
        "legality/stability/historical availability, rank, select, auto-generate a "
        "SourceSpec, register it, and begin qualification -- no manually supplied URLs. "
        "Also recovers any DOWN source by searching for an alternative method.",
    )
    discover_parser.add_argument(
        "--target",
        help="Only run this target organization id (default: every non-per-constituent target)",
    )
    discover_parser.add_argument(
        "--recover-only",
        action="store_true",
        help="Skip fresh targets; only re-run continuity recovery for sources currently DOWN",
    )

    export_dashboard_parser = sub.add_parser(
        "export-dashboard",
        help="Write the web dashboard's JSON artifacts (knowledge, events, "
        "recommendations, market state, runtime metrics, system status, source registry)",
    )
    export_dashboard_parser.add_argument(
        "--date",
        help="ISO date to reconstruct market_state.json/recommendations.json as of "
        "(defaults to the most recent run in --data-dir's run ledger, if any)",
    )
    export_dashboard_parser.add_argument("--out", type=Path, required=True)

    validate_dashboard_parser = sub.add_parser(
        "validate-dashboard", help="Validate a directory of exported dashboard artifacts"
    )
    validate_dashboard_parser.add_argument("--dir", type=Path, required=True)

    publication_parser = sub.add_parser(
        "publication-status",
        help="Validate publication evidence, benchmark performance and legal approval "
        "against archived raw documents; exits 2 while any gate remains blocked",
    )
    publication_parser.add_argument("--date", required=True, help="Gate evaluation date (ISO)")

    args = parser.parse_args(argv)

    if args.command == "run":
        args.data_dir.mkdir(parents=True, exist_ok=True)
        materialize_universe_seed(args.universe_seed_dir, args.data_dir)
        start = date.fromisoformat(args.date)
        end = date.fromisoformat(args.end_date) if args.end_date else start
        pipeline = ProductionPipeline(data_dir=args.data_dir)
        report = pipeline.run(
            start,
            end,
            mode=ExecutionMode(args.mode),
            dashboard_out=args.dashboard_out,
        )
        print(
            f"Production pipeline v{report.pipeline_version} [{args.mode}]: "
            f"{report.overall_status.value} in {report.duration_seconds:.2f}s "
            f"({len(report.artifacts_generated)} artifact(s), "
            f"knowledge {report.knowledge_before}->{report.knowledge_after}, "
            f"genome {report.genome_before}->{report.genome_after})"
        )
        if report.errors:
            for error in report.errors:
                print(f"  ERROR: {error}", file=sys.stderr)
        return 0 if report.overall_status != StageStatus.FAILED else 1

    if args.command == "status":
        runs = RunRecordRepository(args.data_dir / "runs.json").all_latest()
        knowledge = KnowledgeStore(args.data_dir / "knowledge.json").all_latest()
        print(
            json.dumps(
                {
                    "runs": len(runs),
                    "succeeded": sum(1 for r in runs if r.status.value == "succeeded"),
                    "failed": sum(1 for r in runs if r.status.value == "failed"),
                    "knowledge_objects": len(knowledge),
                    "by_status": {
                        status: sum(1 for k in knowledge if k.status.value == status)
                        for status in {k.status.value for k in knowledge}
                    },
                },
                indent=2,
            )
        )
        return 0

    if args.command == "backup":
        manifest = create_backup(args.data_dir, args.output)
        print(f"Backed up {len(manifest['files'])} store(s) to {args.output}")
        return 0

    if args.command == "verify-backup":
        manifest = verify_backup(args.input)
        print(f"OK: {len(manifest['files'])} file(s) verified")
        return 0

    if args.command == "restore":
        manifest = restore_backup(args.input, args.target)
        print(f"Restored {len(manifest['files'])} store(s) to {args.target}")
        return 0

    if args.command == "collect":
        args.data_dir.mkdir(parents=True, exist_ok=True)
        registry = seed_registry()
        spec = registry.latest(args.source)
        if spec is None:
            print(f"Unknown source id: {args.source}", file=sys.stderr)
            return 1

        if spec.collector == "StooqPriceCollector":
            if not args.symbols:
                print("--symbols is required for stooq", file=sys.stderr)
                return 1
            symbols = dict(pair.split("=", 1) for pair in args.symbols.split(","))
            collector = StooqPriceCollector(spec, symbols=symbols)
        elif spec.collector == "FredCsvCollector":
            if not args.series:
                print("--series is required for fred", file=sys.stderr)
                return 1
            collector = FredCsvCollector(spec, series_ids=args.series.split(","))
        elif spec.collector == "RssNewsCollector":
            if not args.feed_url:
                print("--feed-url is required for rss_generic", file=sys.stderr)
                return 1
            hints = args.ticker_hints.split(",") if args.ticker_hints else None
            collector = RssNewsCollector(spec, feed_url=args.feed_url, ticker_hints=hints)
        else:
            print(
                f"No collector wired for source {args.source} (status={spec.status.value})",
                file=sys.stderr,
            )
            return 1

        service = CollectionService(args.data_dir, min_confidence=args.min_confidence)
        result = service.run(collector, expected_records=args.expected_records)
        print(
            json.dumps(
                {
                    "source_id": result.source_id,
                    "documents_fetched": result.documents_fetched,
                    "batches_materialized": result.batches_materialized,
                    "batches_withheld": result.batches_withheld,
                    "price_bars_written": result.price_bars_written,
                    "macro_observations_written": result.macro_observations_written,
                    "news_items_written": result.news_items_written,
                    "events_registered": result.events_registered,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "discover-sources":
        args.data_dir.mkdir(parents=True, exist_ok=True)
        materialize_universe_seed(args.universe_seed_dir, args.data_dir)
        registry = seed_registry(SourceRegistry(args.data_dir / "source_registry.json"))
        fetcher = HttpFetcher()
        engine = AcquisitionIntelligenceEngine(
            prober=build_live_prober(fetcher),
            fetch_text=build_live_fetch_text(fetcher),
            robots_checker=build_live_robots_checker(fetcher),
            registry=registry,
            wayback=build_live_wayback_client(),
        )
        # Every EGX30 constituent gets its own Investor Relations target --
        # Priority 2/3, expanded from the `company_ir` marker entry. Prefers
        # the collected universe (Universe Engine, `universe.collected`)
        # materialized into `--data-dir`; scales automatically, no code
        # change needed.
        universe_provider = CollectedUniverseProvider(args.data_dir)
        universe = universe_provider.constituents(date.today())
        all_targets = [*seed_target_organizations(), *generate_company_ir_targets(universe)]

        results = []
        if not args.recover_only:
            if args.target:
                selected = [t for t in all_targets if t.id == args.target and not t.per_constituent]
                results.extend(engine.run_for_target(t) for t in selected)
            else:
                # Priority order: whichever named/official source resolves
                # first (e.g. EGX itself) gets a chance to supply real
                # per-company IR hints for the rest via its own directory.
                fresh_targets = [t for t in all_targets if not t.per_constituent]
                results.extend(engine.run_catalog(fresh_targets, companies=universe))

        monitor = AcquisitionContinuityMonitor(engine, all_targets)
        results.extend(monitor.check_and_recover(registry))

        for result in results:
            outcome = "REGISTERED" if result.registered else "no-op"
            print(f"{result.target_id}: {outcome} -- {result.reason}")
        if not results:
            print("No targets selected (check --target and --recover-only).")
        return 0

    if args.command == "export-dashboard":
        materialize_universe_seed(args.universe_seed_dir, args.data_dir)
        if args.date:
            as_of = date.fromisoformat(args.date)
        else:
            runs = RunRecordRepository(args.data_dir / "runs.json").all_latest()
            succeeded = [r for r in runs if r.status.value == "succeeded"]
            as_of = max((r.run_date for r in succeeded), default=None)

        memory = build_market_memory(args.data_dir, args.mock_data)
        registry = seed_registry(SourceRegistry(args.data_dir / "source_registry.json"))
        counts = write_dashboard_artifacts(
            knowledge_store=KnowledgeStore(args.data_dir / "knowledge.json"),
            event_repository=EventRepository(args.data_dir / "events.json"),
            runs=RunRecordRepository(args.data_dir / "runs.json"),
            memory=memory,
            as_of=as_of,
            out_dir=args.out,
            registry=registry,
        )
        print(
            json.dumps({"as_of": as_of.isoformat() if as_of else None, "counts": counts}, indent=2)
        )
        return 0

    if args.command == "validate-dashboard":
        try:
            counts = validate_dashboard_artifacts(args.dir)
        except DashboardArtifactError as exc:
            print(f"Dashboard artifact validation failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(counts, indent=2))
        return 0

    if args.command == "publication-status":
        as_of = date.fromisoformat(args.date)
        input_errors: list[str] = []
        external = None
        legal = None
        external_path = args.data_dir / "publication_evidence.json"
        legal_path = args.data_dir / "legal_publication_approval.json"
        if external_path.exists():
            try:
                external = ExternalPublicationEvidence.model_validate_json(
                    external_path.read_text(encoding="utf-8")
                )
            except (ValueError, OSError) as exc:
                input_errors.append(f"publication_evidence.json invalid: {exc}")
        else:
            input_errors.append("publication_evidence.json missing")
        if legal_path.exists():
            try:
                legal = LegalPublicationApproval.model_validate_json(
                    legal_path.read_text(encoding="utf-8")
                )
            except (ValueError, OSError) as exc:
                input_errors.append(f"legal_publication_approval.json invalid: {exc}")
        else:
            input_errors.append("legal_publication_approval.json missing")

        registry_path = args.data_dir / "source_registry.json"
        # Status inspection must be read-only. Use the persisted registry when
        # it exists; otherwise evaluate against an in-memory seeded registry
        # without creating files in the inspected production directory.
        registry = seed_registry(
            SourceRegistry(registry_path) if registry_path.exists() else SourceRegistry()
        )
        report = evaluate_publication_gate(
            DecisionLedger(args.data_dir / "decision_ledger.json").performance_summary(),
            as_of=as_of,
            external=external,
            legal=legal,
            raw_documents=RawDocumentRepository(
                args.data_dir / "raw_documents.json"
            ).all_latest(),
            legally_cleared_source_ids={
                source.id for source in registry.all_latest()
                if source.legal_use_status.value == "cleared"
            },
            input_errors=input_errors,
        )
        payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
        try:
            payload.encode(sys.stdout.encoding or "utf-8")
        except UnicodeEncodeError:
            # Windows terminals commonly expose cp1252 even though the report
            # intentionally contains Arabic. Preserve readable JSON and the
            # meaningful 0/2 exit code instead of crashing during output.
            sys.stdout.buffer.write(payload.encode("utf-8") + b"\n")
        else:
            print(payload)
        return 0 if report.publication_ready else 2

    return 1


if __name__ == "__main__":
    sys.exit(main())
