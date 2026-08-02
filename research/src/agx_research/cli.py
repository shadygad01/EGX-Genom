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
from datetime import date, datetime
from pathlib import Path

from agx_research.acquisition_intelligence.continuity import AcquisitionContinuityMonitor
from agx_research.acquisition_intelligence.discovery_report import (
    DiscoveryHistoryRepository,
    build_discovery_metrics,
    run_discovery_report,
)
from agx_research.acquisition_intelligence.engine import AcquisitionIntelligenceEngine
from agx_research.acquisition_intelligence.live import (
    build_live_fetch_text,
    build_live_prober,
    build_live_robots_checker,
    build_live_wayback_client,
    build_live_wikidata_client,
)
from agx_research.acquisition_intelligence.target import (
    generate_company_ir_targets,
    seed_target_organizations,
)
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.collectors.raw import RawDocumentRepository
from agx_research.collectors.fred import FredCsvCollector
from agx_research.collectors.gdelt import GdeltDocCollector
from agx_research.collectors.rss import RssNewsCollector
from agx_research.collectors.discovery_reconciliation import reconcile_discovery_news
from agx_research.collectors.service import CollectionService
from agx_research.collectors.stooq import StooqPriceCollector
from agx_research.dashboard import validate_dashboard_artifacts, write_dashboard_artifacts
from agx_research.dashboard.validate import DashboardArtifactError
from agx_research.capital_allocation import CapitalAllocationEngine
from agx_research.decision_service.country_risk import assess_country_risk
from agx_research.decision_service.liquidity_floor import compute_illiquid_tickers
from agx_research.decision_service.position import PositionState
from agx_research.decision_service.service import DecisionService, PositionAwareDecision
from agx_research.discovery.web_search_hints import load_web_search_domain_hints
from agx_research.data.mock_provider import LocalCsvDataProvider, MockDataProvider
from agx_research.events.repository import EventRepository
from agx_research.events.service import EventPlatform
from agx_research.financials.collected import CollectedFinancialStatementProvider
from agx_research.infrastructure.backup import create_backup, restore_backup, verify_backup
from agx_research.institutional_validation.runner import run_institutional_validation
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory
from agx_research.meta.decision_ledger import DecisionLedger
from agx_research.meta.publication_gate import (
    ExternalPublicationEvidence,
    LegalPublicationApproval,
    PublicationGateReport,
    apply_publication_gate,
    evaluate_publication_gate,
)
from agx_research.meta.recommendation_service import RecommendationService
from agx_research.production import ExecutionMode, ProductionPipeline, StageStatus
from agx_research.runtime.engine import RunRecordRepository
from agx_research.sources.catalog import seed_registry
from agx_research.sources.registry import SourceRegistry
from agx_research.universe.bootstrap import materialize_universe_seed
from agx_research.universe.collected import CollectedUniverseProvider
from agx_research.universe.sector import CollectedSectorProvider, StaticSectorProvider

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


def build_publication_gate_report(data_dir: Path, as_of: date) -> PublicationGateReport:
    """The one real assembly of a `PublicationGateReport` -- shared by
    `publication-status` (reports it) and `decide` (applies it via
    `apply_publication_gate()` before scoring a portfolio). Before this was
    shared, `decide` never called `apply_publication_gate()` at all, so
    every `HorizonDecision.publication_status` silently stayed at its
    `MetaDecisionEngine` default (`RESEARCH_ONLY`) and `max_position_pct`
    stayed `0.0` regardless of real evidence strength -- `agx decide`
    always produced `no_action`/zero target weight, with no reason in the
    decision's own `explanation` naming the real cause (the fail-closed
    publication gate, not "no positive expectancy"). Read-only: uses the
    persisted registry/ledger/evidence files when they exist, never writes
    to the inspected `--data-dir`.
    """
    input_errors: list[str] = []
    external = None
    legal = None
    external_path = data_dir / "publication_evidence.json"
    legal_path = data_dir / "legal_publication_approval.json"
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
            legal = LegalPublicationApproval.model_validate_json(legal_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            input_errors.append(f"legal_publication_approval.json invalid: {exc}")
    else:
        input_errors.append("legal_publication_approval.json missing")

    registry_path = data_dir / "source_registry.json"
    registry = seed_registry(SourceRegistry(registry_path) if registry_path.exists() else SourceRegistry())
    return evaluate_publication_gate(
        DecisionLedger(data_dir / "decision_ledger.json").performance_summary(),
        as_of=as_of,
        external=external,
        legal=legal,
        raw_documents=RawDocumentRepository(data_dir / "raw_documents.json").all_latest(),
        legally_cleared_source_ids={
            source.id for source in registry.all_latest() if source.legal_use_status.value == "cleared"
        },
        input_errors=input_errors,
    )


def build_position_aware_decisions(
    data_dir: Path, universe_seed_dir: Path, as_of: date, positions_path: Path | None
) -> list[PositionAwareDecision]:
    """Shared setup for `decide` and `allocate-capital` -- both need the
    exact same real `MarketState`/positions/publication-gated
    recommendations, computed once and fed to
    `DecisionService.decide_portfolio()`. Factored out so
    `allocate-capital` composes `decide`'s own real evidence rather than
    reconstructing it a second time.
    """
    materialize_universe_seed(universe_seed_dir, data_dir)
    market_memory = MarketMemory(
        LocalCsvDataProvider(data_dir),
        CollectedUniverseProvider(data_dir),
        CollectedSectorProvider(data_dir),
        macro_series_ids=MACRO_SERIES_IDS,
        lookback_days=30,
        event_platform=EventPlatform(repository=EventRepository(data_dir / "events.json")),
        financials_provider=CollectedFinancialStatementProvider(data_dir),
    )
    market_state = market_memory.reconstruct(as_of)
    snapshot = market_state.dataset_snapshot

    positions: dict[str, PositionState] = {}
    if positions_path is not None:
        raw_positions = json.loads(positions_path.read_text(encoding="utf-8"))
        positions = {
            ticker: PositionState(ticker=ticker, **fields) for ticker, fields in raw_positions.items()
        }

    knowledge_store = KnowledgeStore(data_dir / "knowledge.json")
    recommendation_service = RecommendationService(knowledge_store, event_platform=market_memory.event_platform)
    tickers = sorted(set(snapshot.tickers) | set(positions))
    recommendations = recommendation_service.recommend(tickers, as_of)
    # Same real publication gate `agx publication-status` reports on -- see
    # `build_publication_gate_report`'s own docstring for why this must
    # run before scoring.
    gate_report = build_publication_gate_report(data_dir, as_of)
    recommendations = apply_publication_gate(recommendations, gate_report)

    country_risk = assess_country_risk(snapshot.macro_series, as_of)
    illiquid_tickers = compute_illiquid_tickers(snapshot)

    return DecisionService().decide_portfolio(
        recommendations,
        positions,
        as_of,
        country_risk=country_risk,
        illiquid_tickers=illiquid_tickers,
        corporate_events=snapshot.corporate_events,
        knowledge_store=knowledge_store,
    )


def _print_json(payload_obj: object) -> None:
    payload = json.dumps(payload_obj, ensure_ascii=False, indent=2)
    try:
        payload.encode(sys.stdout.encoding or "utf-8")
    except UnicodeEncodeError:
        sys.stdout.buffer.write(payload.encode("utf-8") + b"\n")
    else:
        print(payload)


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

    sub.add_parser(
        "shadow-fund",
        help="Show the Shadow Fund's current state (holdings, cash, NAV, risk, attribution) -- "
        "read-only; the fund itself only advances as a stage inside `agx run`, never on demand "
        "(see shadow_fund/engine.py's module docstring for why an autonomous virtual portfolio "
        "is safe to advance inside the scheduled pipeline, unlike a real investor's decisions).",
    )

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
        "--ticker-hints", help="rss_generic/gdelt only: comma-separated tickers to match"
    )
    collect_parser.add_argument(
        "--query", help="gdelt only: the GDELT DOC 2.0 query string, e.g. 'Egypt OR EGX'"
    )
    collect_parser.add_argument(
        "--start-date",
        help="gdelt only: ISO date; with --end-date, switches gdelt to historical "
        "windowed backfill (absolute startdatetime/enddatetime) instead of the "
        "relative --timespan the daily live run uses",
    )
    collect_parser.add_argument("--end-date", help="gdelt only: ISO date, inclusive")
    collect_parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="gdelt historical backfill only: days per windowed request (default 7; "
        "GDELT DOC 2.0 caps each response at 250 articles regardless of window size)",
    )
    collect_parser.add_argument(
        "--timespan", default="7d", help="gdelt only, non-historical mode: GDELT relative timespan"
    )
    collect_parser.add_argument(
        "--max-records", type=int, default=250, help="gdelt only: max articles per window"
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

    discover_report_parser = sub.add_parser(
        "discover-planned-report",
        help="Weekly Discovery workflow: run the Acquisition Intelligence Engine against every "
        "PLANNED/CANDIDATE source with a catalogued TargetOrganization, write an evidenced "
        "discovery_report.json/discovery_metrics.json/endpoint_candidates.json, and cache results "
        "so an unchanged source is not re-probed every run. Never flips a source to IMPLEMENTED "
        "itself -- see docs/DATA_ACQUISITION.md's Discovery workflow section.",
    )
    discover_report_parser.add_argument(
        "--out", type=Path, required=True, help="Directory to write the three report JSON files"
    )
    discover_report_parser.add_argument(
        "--history",
        type=Path,
        required=True,
        help="Path to the persisted, git-tracked discovery-history JSON file (incremental cache)",
    )
    discover_report_parser.add_argument(
        "--ttl-days",
        type=float,
        default=30.0,
        help="How long a verified/failed result stays cached before being re-probed (default 30)",
    )
    discover_report_parser.add_argument(
        "--force",
        help="Comma-separated source ids to re-probe even if their cache entry is still fresh",
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
    validate_dashboard_parser.add_argument(
        "--require-complete-financials",
        action="store_true",
        help=(
            "Fail unless every universe ticker has at least one sourced, "
            "non-estimated financial item"
        ),
    )

    reconcile_discovery_parser = sub.add_parser(
        "reconcile-discovery-news",
        help="Promote DISCOVERY-tier news candidates (news_discovery.csv, e.g. GDELT) into "
        "news.csv wherever a PRIMARY source independently reported the same ticker nearby "
        "in time -- see sources.spec.EvidenceTier",
    )
    reconcile_discovery_parser.add_argument(
        "--window-days", type=int, default=2,
        help="Max days between a discovery candidate and a matching primary-source report",
    )

    publication_parser = sub.add_parser(
        "publication-status",
        help="Validate publication evidence, benchmark performance and legal approval "
        "against archived raw documents; exits 2 while any gate remains blocked",
    )
    publication_parser.add_argument("--date", required=True, help="Gate evaluation date (ISO)")

    decide_parser = sub.add_parser(
        "decide",
        help="Compute position-aware Buy/Increase Position/Hold/Reduce Position/Exit/"
        "No Action decisions from --data-dir's collected knowledge, macro data, and an "
        "optional positions file. Read-only; queried on demand, never run on a schedule "
        "(see decision_service/__init__.py -- a real portfolio's holdings cannot be "
        "autonomously discovered).",
    )
    decide_parser.add_argument("--date", required=True, help="Decision date (ISO)")
    decide_parser.add_argument(
        "--positions",
        type=Path,
        default=None,
        help='JSON file: {"TICKER": {"held": true, "current_weight": 0.05, '
        '"average_cost": 12.3}}. A ticker absent from this file is treated as not held.',
    )

    allocate_capital_parser = sub.add_parser(
        "allocate-capital",
        help="Capital Allocation Intelligence: rank every ticker `decide` would evaluate "
        "against every other one for the same capital budget, and produce a deployment "
        "queue, an opportunity-cost note per proposal, and a capital-recycling ledger "
        "(which released holding funded which new one, or cash). Composes `decide`'s own "
        "real evidence -- read-only, queried on demand, never run on a schedule (same "
        "constraint as `decide`; see capital_allocation/__init__.py).",
    )
    allocate_capital_parser.add_argument("--date", required=True, help="Decision date (ISO)")
    allocate_capital_parser.add_argument(
        "--positions",
        type=Path,
        default=None,
        help='JSON file: {"TICKER": {"held": true, "current_weight": 0.05, '
        '"average_cost": 12.3}}. A ticker absent from this file is treated as not held.',
    )

    validate_investment_parser = sub.add_parser(
        "validate-investment",
        help="Institutional Investment Validation: stress-test the decision engine against "
        "10 repeatable scenarios (full-universe ranking, rejection, cash, portfolio "
        "construction, benchmark comparison, thesis-failure detection, change attribution, "
        "evidence traceability). Self-contained -- ignores --data-dir except to report real "
        "mock price coverage honestly; exits 2 only if a scenario finds a genuine defect.",
    )
    validate_investment_parser.add_argument(
        "--out", type=Path, default=None, help="Write the JSON report to this path (in addition to stdout)."
    )
    validate_investment_parser.add_argument(
        "--markdown-out", type=Path, default=None, help="Also write a human-readable Markdown report."
    )

    investment_proof_parser = sub.add_parser(
        "investment-proof",
        help="Investment Proof Framework: runs Institutional Investment Validation plus decision "
        "attribution, counterfactual analysis, committee validation, portfolio validation, "
        "decision stability, thesis-survival, confidence-calibration and walk-forward readiness "
        "checks, and assembles the final Capital Trust Report (would a rational institutional "
        "investment committee trust this system with capital?). Self-contained, synthetic-data "
        "based -- exits 2 only if a dimension finds a genuine (FAIL) defect, never for an honest "
        "READY FOR DATA gap.",
    )
    investment_proof_parser.add_argument(
        "--date", default=None, help="As-of date (ISO). Defaults to the same date validate-investment uses."
    )
    investment_proof_parser.add_argument(
        "--ticker-limit",
        type=int,
        default=15,
        help="How many real EGX30 tickers to build the shared synthetic scenario from.",
    )
    investment_proof_parser.add_argument(
        "--out", type=Path, default=None, help="Write the JSON report to this path (in addition to stdout)."
    )
    investment_proof_parser.add_argument(
        "--markdown-out", type=Path, default=None, help="Also write a human-readable Markdown Capital Trust Report."
    )

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

    if args.command == "shadow-fund":
        from agx_research.shadow_fund.export import export_shadow_fund
        from agx_research.shadow_fund.repository import ShadowFundLedger

        ledger = ShadowFundLedger(args.data_dir / "shadow_fund.json")
        state = export_shadow_fund(ledger)
        if state is None:
            print(
                json.dumps({"error": "Shadow Fund has not started yet -- run `agx run` first."}, indent=2)
            )
            return 0
        _print_json(state.model_dump(mode="json"))
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
        elif spec.collector == "GdeltDocCollector":
            if not args.query:
                print("--query is required for gdelt", file=sys.stderr)
                return 1
            hints = args.ticker_hints.split(",") if args.ticker_hints else None
            if bool(args.start_date) != bool(args.end_date):
                print("--start-date and --end-date must be given together", file=sys.stderr)
                return 1
            collector = GdeltDocCollector(
                spec,
                query=args.query,
                ticker_hints=hints,
                max_records=args.max_records,
                timespan=args.timespan,
                start_date=date.fromisoformat(args.start_date) if args.start_date else None,
                end_date=date.fromisoformat(args.end_date) if args.end_date else None,
                window_days=args.window_days,
            )
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
                    "news_discovery_items_written": result.news_discovery_items_written,
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
        company_ir_targets = generate_company_ir_targets(universe)

        # A second, independent free hint source that does not depend on
        # `egx_official` being reachable at all: Wikidata's own declared
        # `P856` (official website) property, matched by company name (see
        # `discovery.wikidata_lookup`). `run_catalog`'s own
        # `discover_company_directory_links` pass (via egx_official or any
        # other resolved catalog target) can still supply a hint later in
        # the same run for any ticker this lookup missed -- it never
        # overrides a hint a target already carries, so applying this first
        # only ever adds coverage, never removes it.
        wikidata_hints = build_live_wikidata_client().lookup(universe)
        if wikidata_hints:
            company_ir_targets = [
                t.model_copy(update={"domain_hints": [wikidata_hints[t.company_ticker]]})
                if t.company_ticker in wikidata_hints
                else t
                for t in company_ir_targets
            ]

        # A third, independent hint source (see TD-38): a reviewed, evidenced
        # web-search snapshot (`discovery.load_web_search_domain_hints`),
        # applied only to tickers Wikidata's own structured P856 claim did
        # not already resolve -- Wikidata is preferred where both exist
        # since it's independently machine-verifiable, not just text search
        # evidence. Like every other hint here, nothing is trusted directly:
        # `HeuristicDomainResolver` still independently probes it.
        web_search_hints = load_web_search_domain_hints(
            args.universe_seed_dir / "egx30_web_search_domain_hints.json"
        )
        if web_search_hints:
            company_ir_targets = [
                t.model_copy(update={"domain_hints": [web_search_hints[t.company_ticker]]})
                if t.company_ticker in web_search_hints and t.company_ticker not in wikidata_hints
                else t
                for t in company_ir_targets
            ]
        all_targets = [*seed_target_organizations(), *company_ir_targets]

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

    if args.command == "discover-planned-report":
        args.data_dir.mkdir(parents=True, exist_ok=True)
        args.out.mkdir(parents=True, exist_ok=True)
        registry = seed_registry(SourceRegistry(args.data_dir / "source_registry.json"))
        fetcher = HttpFetcher()
        engine = AcquisitionIntelligenceEngine(
            prober=build_live_prober(fetcher),
            fetch_text=build_live_fetch_text(fetcher),
            robots_checker=build_live_robots_checker(fetcher),
            registry=registry,
            wayback=build_live_wayback_client(),
        )
        history = DiscoveryHistoryRepository(args.history)
        force_ids = {s.strip() for s in args.force.split(",") if s.strip()} if args.force else set()
        started_at = datetime.now()
        outcomes, candidates = run_discovery_report(
            engine,
            registry,
            seed_target_organizations(),
            history,
            force_ids=force_ids,
            ttl_days=args.ttl_days,
            now=started_at,
        )
        finished_at = datetime.now()
        metrics = build_discovery_metrics(outcomes, started_at=started_at, finished_at=finished_at)

        (args.out / "discovery_report.json").write_text(
            json.dumps([o.model_dump(mode="json") for o in outcomes], indent=2, sort_keys=True)
            + "\n"
        )
        (args.out / "discovery_metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n"
        )
        (args.out / "endpoint_candidates.json").write_text(
            json.dumps([c.model_dump(mode="json") for c in candidates], indent=2, sort_keys=True)
            + "\n"
        )
        print(json.dumps(metrics, indent=2))
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

    if args.command == "reconcile-discovery-news":
        args.data_dir.mkdir(parents=True, exist_ok=True)
        result = reconcile_discovery_news(args.data_dir, window_days=args.window_days)
        print(
            json.dumps(
                {
                    "candidates_checked": result.candidates_checked,
                    "promoted": result.promoted,
                    "still_pending": result.still_pending,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "validate-dashboard":
        try:
            counts = validate_dashboard_artifacts(
                args.dir,
                require_complete_financials=args.require_complete_financials,
            )
        except DashboardArtifactError as exc:
            print(f"Dashboard artifact validation failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(counts, indent=2))
        return 0

    if args.command == "publication-status":
        as_of = date.fromisoformat(args.date)
        report = build_publication_gate_report(args.data_dir, as_of)
        payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
        try:
            payload.encode(sys.stdout.encoding or "utf-8")
        except UnicodeEncodeError:
            # Windows terminals commonly expose a narrow codepage (e.g.
            # cp1252) that can't represent every character report content
            # might carry (e.g. a non-ASCII legal reviewer name). Preserve
            # readable JSON and the meaningful 0/2 exit code instead of
            # crashing during output.
            sys.stdout.buffer.write(payload.encode("utf-8") + b"\n")
        else:
            print(payload)
        return 0 if report.publication_ready else 2

    if args.command == "validate-investment":
        from agx_research.institutional_validation.report import CheckVerdict

        report = run_institutional_validation()
        payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(payload, encoding="utf-8")
        if args.markdown_out is not None:
            args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
            args.markdown_out.write_text(report.to_markdown(), encoding="utf-8")
        try:
            payload.encode(sys.stdout.encoding or "utf-8")
        except UnicodeEncodeError:
            sys.stdout.buffer.write(payload.encode("utf-8") + b"\n")
        else:
            print(payload)
        return 0 if report.overall_verdict != CheckVerdict.FAIL else 2

    if args.command == "investment-proof":
        from agx_research.institutional_validation.report import CheckVerdict
        from agx_research.institutional_validation.runner import DEFAULT_AS_OF
        from agx_research.investment_proof.capital_trust import InvestmentProofEngine

        as_of = date.fromisoformat(args.date) if args.date else DEFAULT_AS_OF
        report = InvestmentProofEngine().run(as_of, ticker_limit=args.ticker_limit)
        payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(payload, encoding="utf-8")
        if args.markdown_out is not None:
            args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
            args.markdown_out.write_text(report.to_markdown(), encoding="utf-8")
        try:
            payload.encode(sys.stdout.encoding or "utf-8")
        except UnicodeEncodeError:
            sys.stdout.buffer.write(payload.encode("utf-8") + b"\n")
        else:
            print(payload)
        has_fail = any(d.verdict == CheckVerdict.FAIL for d in report.dimensions)
        return 0 if not has_fail else 2

    if args.command == "decide":
        as_of = date.fromisoformat(args.date)
        decisions = build_position_aware_decisions(args.data_dir, args.universe_seed_dir, as_of, args.positions)
        _print_json([decision.model_dump(mode="json") for decision in decisions])
        return 0

    if args.command == "allocate-capital":
        as_of = date.fromisoformat(args.date)
        decisions = build_position_aware_decisions(args.data_dir, args.universe_seed_dir, as_of, args.positions)
        plan = CapitalAllocationEngine().build(decisions, as_of)
        _print_json(plan.model_dump(mode="json"))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
