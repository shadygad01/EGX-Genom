"""ProductionPipeline: the first end-to-end production execution path.

Wires every already-completed system together, in the exact order the
production execution chain requires:

    Entry Point -> Source Registry -> Discovery Engine -> Collector
    Selection -> Collector Execution -> Raw Archive -> Canonical
    Transformation -> Validation -> Event Platform -> Market Memory ->
    Knowledge Base -> Research Pipeline -> Genome -> Investment Case
    Generator -> Dashboard Artifact Generator -> Mission Control Update ->
    Execution Report

Nothing here reimplements a completed system: `CollectionService`,
`DailyResearchPipeline`, `RuntimeEngine`, `RecommendationService`,
`PortfolioConstructor`, `write_dashboard_artifacts`, and the Acquisition
Intelligence Engine are all called exactly as they already exist. This
module is composition -- constructing them against a shared `data_dir` so
data collected in "Collector Execution" is what "Research Pipeline"
actually reads (previously two disconnected paths: `agx collect` wrote to
`--data-dir`, but `agx run` always read from the separate, static
`--mock-data` directory regardless).

Some stages are mutations (Collector Execution, Research Pipeline);
others are reporting checkpoints over state a neighboring stage already
mutated (Raw Archive/Canonical Transformation/Validation report on what
Collector Execution just did; Genome reports on what Research Pipeline
just did) -- because gene creation and knowledge promotion are one atomic
flow inside `DailyResearchPipeline` (a completed system this doesn't
redesign), "Genome" cannot be a separate mutation step without duplicating
that flow. Every stage still appears, in order, with a real result.

Failure isolation: each stage is wrapped independently. A stage that
raises is recorded FAILED with its error message; execution continues to
the next stage regardless, exactly as `RuntimeEngine.run_day` already
isolates one bad day from the rest of a range.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from agx_research.acquisition_intelligence.capability import Capability
from agx_research.acquisition_intelligence.capability_engine import (
    CapabilityDecision,
    CapabilityDecisionEngine,
    CapabilityStrategyAttempt,
    rank_capability_strategies,
)
from agx_research.acquisition_intelligence.continuity import AcquisitionContinuityMonitor
from agx_research.acquisition_intelligence.engine import AcquisitionIntelligenceEngine
from agx_research.acquisition_intelligence.live import (
    build_live_fetch_text,
    build_live_prober,
    build_live_robots_checker,
    build_live_wayback_client,
)
from agx_research.acquisition_intelligence.target import (
    seed_target_organizations,
)
from agx_research.agents.corporate_events import CorporateEventsAgent
from agx_research.agents.liquidity import LiquidityAgent
from agx_research.agents.macro import MacroAgent
from agx_research.agents.market_structure import MarketStructureAgent
from agx_research.agents.technical_structure import TechnicalStructureAgent
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.collectors.provenance_index import ProvenanceIndexRepository
from agx_research.collectors.raw import RawDocumentRepository
from agx_research.collectors.service import CollectionRunResult, CollectionService
from agx_research.dashboard.export import ARTIFACT_FILENAMES, write_dashboard_artifacts
from agx_research.data.mock_provider import LocalCsvDataProvider
from agx_research.domain.identifiers import new_id
from agx_research.events.repository import EventRepository
from agx_research.events.service import EventPlatform
from agx_research.financials.collected import CollectedFinancialStatementProvider
from agx_research.genome.service import AlphaGenome
from agx_research.graph.knowledge_graph import KnowledgeGraph
from agx_research.hypotheses.repository import HypothesisRepository
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory
from agx_research.meta.readiness import assess_decision_readiness
from agx_research.orchestration.pipeline import DailyResearchPipeline
from agx_research.papers.repository import PaperRepository
from agx_research.production import artifacts as production_artifacts
from agx_research.production.collector_plan import (
    EXPECTED_RECORDS,
    EXPECTED_RECORDS_LIVE,
    LIVE_MACRO_SERIES_IDS,
    ExecutionMode,
    build_collector_plan,
    build_live_collector,
    live_wired_source_ids,
    unavailable_sources,
)
from agx_research.production.decision_lineage import export_decision_routes
from agx_research.production.mission_control import build_mission_control_status
from agx_research.production.report import (
    PIPELINE_VERSION,
    ExecutionReport,
    PipelineExecutionRepository,
    derive_overall_status,
)
from agx_research.production.stages import StageName, StageResult, StageStatus
from agx_research.runtime.engine import RunRecord, RunRecordRepository, RunStatus, RuntimeEngine
from agx_research.sources.catalog import seed_registry
from agx_research.sources.health import HealthAlertRepository, HealthMonitor
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.reputation import SourceMetricsRepository
from agx_research.universe.collected import CollectedUniverseProvider
from agx_research.universe.provider import UniverseProvider
from agx_research.universe.sector import StaticSectorProvider

_DEFAULT_MACRO_SERIES = ["BRENT_USD", "EGP_USD", "egypt_cpi_inflation"]

# Egyptian Live Data Sprint (original): fresh discovery started restricted
# to exactly the project owner's first named priority order (EGX official ->
# EGX30/EGX70 Investor Relations -> CBE -> Enterprise -> Mubasher -> Zawya).
# Coverage-expansion mission: that allowlist meant every target added to
# target.py's seed catalog afterward (Reuters, Trading Economics, Asharq
# Business, CNBC Arabia, and the nine outlets this mission added) was
# catalogued but never actually attempted by a real production run -- only
# reachable via a manual `discover-sources --target <id>` CLI call, which is
# how this mission itself found `skynews_arabia_economy`'s live feed. Fresh
# discovery now runs every non-per-constituent seeded target every live run
# (still governed by `TargetOrganization.priority` for processing order, and
# still real-network-verified/legality-gated per target, same as always) so
# a newly catalogued target is automatically covered with no second
# registration step required.


class ProductionPipeline:
    def __init__(
        self,
        *,
        data_dir: Path | str,
        universe_provider: UniverseProvider | None = None,
        macro_series_ids: list[str] | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.universe_provider = universe_provider or CollectedUniverseProvider(self.data_dir)
        # Deferred to `run()`, which knows the execution mode: LIVE fetches
        # real FRED/World Bank series ids, which differ from the mock
        # fixtures' placeholder ids -- an explicit override here always wins.
        self._macro_series_ids_override = macro_series_ids
        self.macro_series_ids = macro_series_ids or list(_DEFAULT_MACRO_SERIES)

        # Populated by stages as they run; downstream stages check these
        # rather than assume a prior stage succeeded.
        self.registry: SourceRegistry | None = None
        self.raw_documents: RawDocumentRepository | None = None
        self.event_platform: EventPlatform | None = None
        self.collection_results: dict[str, CollectionRunResult] = {}
        self.materialized_source_results: dict[str, CollectionRunResult] = {}
        self.market_memory: MarketMemory | None = None
        self.market_state_summary: str = ""
        self.knowledge_store: KnowledgeStore | None = None
        self.genome: AlphaGenome | None = None
        self.knowledge_before = 0
        self.knowledge_after = 0
        self.genome_before = 0
        self.genome_after = 0
        self.events_before = 0
        self.events_after = 0
        self.run_records_this_execution: list[RunRecord] = []
        self.investment_cases: dict | None = None
        self.dashboard_counts: dict[str, int] = {}
        self.mode: ExecutionMode = ExecutionMode.LIVE
        self._unavailable: dict[str, str] = {}
        self._standby: dict[str, str] = {}
        self.collector_failures: dict[str, str] = {}
        self.metrics: SourceMetricsRepository | None = None
        # Capability-driven acquisition (LIVE mode only): one decision per
        # `Capability`, recording every strategy considered -- see
        # `acquisition_intelligence.capability_engine`.
        self.capability_decisions: list[CapabilityDecision] = []

    def _tickers(self, as_of: date) -> list[str]:
        """Resolve membership at use time; the provider is the only source of truth."""
        return sorted(self.universe_provider.constituents(as_of))

    # ---- the public entrypoint ----------------------------------------

    def run(
        self,
        start: date,
        end: date | None = None,
        *,
        mode: ExecutionMode = ExecutionMode.LIVE,
        dashboard_out: Path | None = None,
    ) -> ExecutionReport:
        end = end or start
        if end < start:
            raise ValueError("end must be on or after start")
        dashboard_out = dashboard_out or (self.data_dir / "dashboard")
        self.mode = mode
        self._run_as_of = end
        if self._macro_series_ids_override is not None:
            self.macro_series_ids = list(self._macro_series_ids_override)
        elif mode == ExecutionMode.LIVE:
            self.macro_series_ids = list(LIVE_MACRO_SERIES_IDS)
        else:
            self.macro_series_ids = list(_DEFAULT_MACRO_SERIES)

        started_at = datetime.now()
        stages: list[StageResult] = []
        errors: list[str] = []
        warnings: list[str] = []

        def execute(name: StageName, fn) -> StageResult:
            stage_started = datetime.now()
            try:
                status, detail, stage_warnings = fn()
            except Exception as exc:  # per-stage isolation -- never propagates
                status = StageStatus.FAILED
                detail = ""
                stage_warnings = []
                error = f"{type(exc).__name__}: {exc}"
                errors.append(f"{name.value}: {error}")
                stage_completed = datetime.now()
                result = StageResult(
                    name=name,
                    status=status,
                    started_at=stage_started,
                    completed_at=stage_completed,
                    duration_seconds=(stage_completed - stage_started).total_seconds(),
                    detail=detail,
                    error=error,
                )
                stages.append(result)
                return result
            stage_completed = datetime.now()
            warnings.extend(stage_warnings)
            result = StageResult(
                name=name,
                status=status,
                started_at=stage_started,
                completed_at=stage_completed,
                duration_seconds=(stage_completed - stage_started).total_seconds(),
                detail=detail,
                warnings=stage_warnings,
            )
            stages.append(result)
            return result

        execute(
            StageName.ENTRYPOINT,
            lambda: (
                StageStatus.SUCCEEDED,
                f"Production pipeline v{PIPELINE_VERSION} started for {start}..{end}, mode={mode.value}.",
                [],
            ),
        )
        execute(StageName.SOURCE_REGISTRY, self._stage_source_registry)
        execute(StageName.DISCOVERY_ENGINE, self._stage_discovery_engine)
        execute(
            StageName.COLLECTOR_SELECTION,
            lambda: self._stage_collector_selection(mode, end),
        )
        execute(StageName.COLLECTOR_EXECUTION, self._stage_collector_execution)
        execute(StageName.RAW_ARCHIVE, self._stage_raw_archive)
        execute(StageName.CANONICAL_TRANSFORMATION, self._stage_canonical_transformation)
        execute(StageName.VALIDATION, self._stage_validation)
        execute(StageName.EVENT_PLATFORM, self._stage_event_platform)
        execute(StageName.MARKET_MEMORY, lambda: self._stage_market_memory(end))
        execute(StageName.KNOWLEDGE_BASE, self._stage_knowledge_base)
        execute(StageName.RESEARCH_PIPELINE, lambda: self._stage_research_pipeline(start, end))
        execute(StageName.GENOME, self._stage_genome)
        execute(StageName.INVESTMENT_CASE_GENERATOR, self._stage_investment_case_generator)
        execute(
            StageName.DASHBOARD_ARTIFACT_GENERATOR,
            lambda: self._stage_dashboard_artifact_generator(dashboard_out, end),
        )

        completed_at = datetime.now()
        report = ExecutionReport(
            id=new_id("execution"),
            execution_mode=mode.value,
            run_dates=[
                (start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)
            ],
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
            overall_status=self._overall_status(stages),
            stages=list(stages),
            artifacts_generated=dict(self.dashboard_counts),
            errors=list(errors),
            warnings=list(warnings),
            skipped_stages=[s.name.value for s in stages if s.status == StageStatus.SKIPPED],
            knowledge_before=self.knowledge_before,
            knowledge_after=self.knowledge_after,
            genome_before=self.genome_before,
            genome_after=self.genome_after,
            events_before=self.events_before,
            events_after=self.events_after,
        )

        execute(
            StageName.MISSION_CONTROL_UPDATE,
            lambda: self._stage_mission_control_update(report, dashboard_out),
        )
        # Recompute with the mission-control stage included (it only ever
        # adds a SUCCEEDED/FAILED entry; status can still change if it fails).
        report = report.model_copy(
            update={
                "stages": list(stages),
                "overall_status": self._overall_status(stages),
                "skipped_stages": [s.name.value for s in stages if s.status == StageStatus.SKIPPED],
            }
        )

        execution_report_path = dashboard_out / "execution_report.json"
        execute(
            StageName.EXECUTION_REPORT,
            lambda: self._stage_execution_report(report, execution_report_path),
        )
        # The report written above can't include its own finalizing stage;
        # rewrite once more so the artifact on disk is complete.
        final_report = report.model_copy(update={"stages": list(stages)})
        execution_report_path.write_text(
            json.dumps(final_report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        )
        return final_report

    def _overall_status(self, stages: list[StageResult]) -> StageStatus:
        """`derive_overall_status`'s generic per-stage rule, plus the
        mission's explicit LIVE-mode failure policy: never silently fall
        back to mock, and if no live source succeeds at all, fail loudly
        rather than report the milder PARTIAL a generic per-stage rule
        would otherwise compute (most later stages "succeed" vacuously with
        zero rows once collection produces nothing).
        """
        status = derive_overall_status(stages)
        if self.mode == ExecutionMode.LIVE and not self.collection_results:
            return StageStatus.FAILED
        return status

    # ---- individual stages ---------------------------------------------

    def _stage_source_registry(self):
        self.registry = seed_registry(SourceRegistry(self.data_dir / "source_registry.json"))
        self.metrics = SourceMetricsRepository(self.data_dir / "source_metrics.json")
        return (
            StageStatus.SUCCEEDED,
            f"{len(self.registry.all_latest())} source(s) catalogued; "
            f"{len(self.registry.collectable())} collectable.",
            [],
        )

    def _stage_discovery_engine(self):
        if self.registry is None:
            return StageStatus.SKIPPED, "No registry available.", []
        # LIVE-mode only: this stage's engine is real-network-backed
        # (`HttpFetcher`) regardless of mode, and MOCK/REPLAY are
        # testing-only and must never touch the real network.
        if self.mode != ExecutionMode.LIVE:
            return (
                StageStatus.SUCCEEDED,
                f"Discovery is a live-network operation; not applicable in {self.mode.value} mode.",
                [],
            )

        fetcher = HttpFetcher()
        engine = AcquisitionIntelligenceEngine(
            prober=build_live_prober(fetcher),
            fetch_text=build_live_fetch_text(fetcher),
            robots_checker=build_live_robots_checker(fetcher),
            registry=self.registry,
            wayback=build_live_wayback_client(),
        )

        # Acquisition is frozen: routine Pages deployments must collect from
        # already-approved sources, not spend ~57 minutes rediscovering every
        # blocked/planned target. Continuity recovery remains live so an
        # IMPLEMENTED source marked DOWN can still be repaired automatically.
        # A future named acquisition sprint can call `discover-sources`
        # explicitly and promote its verified result into the catalog.
        monitor = AcquisitionContinuityMonitor(engine, seed_target_organizations())
        recovery_results = monitor.check_and_recover(self.registry)
        recovered = sum(1 for r in recovery_results if r.registered)
        return (
            StageStatus.SUCCEEDED,
            "Acquisition freeze active: fresh discovery skipped; "
            f"{len(recovery_results)} DOWN source(s) needed recovery "
            f"({recovered} recovered).",
            [],
        )

    def _stage_collector_selection(self, mode: ExecutionMode, as_of: date | None = None):
        if self.registry is None:
            return StageStatus.SKIPPED, "No registry available.", []
        self.raw_documents = RawDocumentRepository(self.data_dir / "raw_documents.json")

        if mode == ExecutionMode.LIVE:
            # Capability-driven selection (mission: acquisition strategy is
            # ranked per capability, never a fixed per-website list). Actual
            # collector construction is deferred to Collector Execution,
            # since a capability's next-ranked strategy is only built if a
            # higher-ranked one fails or yields nothing -- this stage only
            # ranks, it never fetches.
            self._planned = []
            self._capability_rankings = {
                capability: rank_capability_strategies(capability, self.registry, self.metrics)
                for capability in Capability
            }
            ready_total = sum(
                1 for scores in self._capability_rankings.values() for s in scores if s.ready
            )
            candidate_total = sum(len(scores) for scores in self._capability_rankings.values())
            return (
                StageStatus.SUCCEEDED,
                f"Ranked {candidate_total} candidate strategy(ies) across "
                f"{len(self._capability_rankings)} capability(ies); {ready_total} collectable now.",
                [],
            )

        self._planned = build_collector_plan(
            self.registry,
            mode=mode,
            raw_documents=self.raw_documents,
            tickers=self._tickers(as_of or self._run_as_of),
        )
        self._unavailable = unavailable_sources(self.registry, {p.source_id for p in self._planned})
        if not self._planned:
            return (
                StageStatus.SKIPPED,
                f"No collectable source matched this pipeline's collector plan "
                f"({len(self._unavailable)} source(s) unavailable).",
                [],
            )
        return (
            StageStatus.SUCCEEDED,
            f"Selected {len(self._planned)} collector(s): "
            f"{', '.join(p.source_id for p in self._planned)} (mode={mode.value}); "
            f"{len(self._unavailable)} source(s) unavailable this run.",
            [],
        )

    def _stage_collector_execution(self):
        if self.mode == ExecutionMode.LIVE:
            return self._stage_collector_execution_capability_driven()

        planned = getattr(self, "_planned", None)
        if not planned:
            return StageStatus.SKIPPED, "No collectors selected.", []

        self.event_platform = EventPlatform(
            repository=EventRepository(self.data_dir / "events.json")
        )
        service = CollectionService(
            self.data_dir,
            raw_documents=self.raw_documents,
            event_platform=self.event_platform,
            provenance_index=ProvenanceIndexRepository(self.data_dir / "provenance_index.json"),
            metrics=self.metrics or SourceMetricsRepository(self.data_dir / "source_metrics.json"),
            health_monitor=HealthMonitor(
                HealthAlertRepository(self.data_dir / "health_alerts.json")
            ),
            registry=self.registry,
            min_confidence=0.5,
        )

        failures: list[str] = []
        for plan in planned:
            try:
                result = service.run(
                    plan.collector, expected_records=EXPECTED_RECORDS.get(plan.source_id, 1)
                )
                self.collection_results[plan.source_id] = result
            except Exception as exc:
                # The exact reason -- exception type + message -- never
                # abort the remaining collectors for one source's failure.
                reason = f"{type(exc).__name__}: {exc}"
                failures.append(f"{plan.source_id}: {reason}")
                self.collector_failures[plan.source_id] = reason

        succeeded = len(self.collection_results)
        total = len(planned)
        if succeeded == 0:
            return StageStatus.FAILED, f"All {total} collector(s) failed.", failures
        if failures:
            return (
                StageStatus.PARTIAL,
                f"{succeeded}/{total} collector(s) succeeded.",
                failures,
            )
        return StageStatus.SUCCEEDED, f"{succeeded}/{total} collector(s) succeeded.", []

    def _stage_collector_execution_capability_driven(self):
        """LIVE mode's Collector Execution: capability-driven, not a fixed
        per-website list. For every `Capability`, `CapabilityDecisionEngine`
        ranks catalogued strategies and executes the best collectable one,
        automatically falling through to the next on failure or zero yield
        (mission Phase 4) -- reusing the exact same `CollectionService`
        every mode has always used, so raw archive/canonical transformation/
        validation/health/reputation bookkeeping is unchanged.
        """
        if self.registry is None:
            return StageStatus.SKIPPED, "No registry available.", []

        self.event_platform = EventPlatform(
            repository=EventRepository(self.data_dir / "events.json")
        )
        service = CollectionService(
            self.data_dir,
            raw_documents=self.raw_documents,
            event_platform=self.event_platform,
            provenance_index=ProvenanceIndexRepository(self.data_dir / "provenance_index.json"),
            metrics=self.metrics or SourceMetricsRepository(self.data_dir / "source_metrics.json"),
            health_monitor=HealthMonitor(
                HealthAlertRepository(self.data_dir / "health_alerts.json")
            ),
            registry=self.registry,
            min_confidence=0.5,
        )
        fetcher = HttpFetcher()

        def factory(source_id: str, spec):
            return build_live_collector(
                source_id,
                spec,
                fetcher=fetcher,
                tickers=self._tickers(self._run_as_of),
            )

        engine = CapabilityDecisionEngine(self.registry, factory, metrics=self.metrics)

        self.capability_decisions = []
        failures: list[str] = []
        for capability in Capability:
            decision, results, capability_failures = engine.decide_and_execute(
                capability,
                service,
                expected_records=EXPECTED_RECORDS_LIVE,
            )
            self.capability_decisions.append(decision)
            self.collection_results.update(results)
            self.collector_failures.update(capability_failures)
            for source_id, reason in capability_failures.items():
                failures.append(f"{source_id}: {reason}")

        # These two capabilities are materialized by existing production
        # providers, not fetched as independent network feeds. Record that
        # operational fact instead of leaving Mission Control falsely red.
        universe_tickers = self._tickers(self._run_as_of)
        universe_result = CollectionRunResult(
            source_id="egx_universe_seed",
            documents_fetched=1,
            batches_materialized=1,
            batches_withheld=0,
            price_bars_written=0,
            macro_observations_written=0,
            news_items_written=0,
            corporate_events_written=0,
            index_constituents_written=len(universe_tickers),
            financial_statement_line_items_written=0,
            events_registered=0,
            assessments=[],
        )
        self.materialized_source_results["egx_universe_seed"] = universe_result

        def record_materialized_capability(
            capability: Capability, source_id: str, reason: str, yield_count: int
        ) -> None:
            replacement = CapabilityDecision(
                capability=capability.value,
                decided_at=datetime.now().astimezone(),
                attempts=[CapabilityStrategyAttempt(
                    source_id=source_id,
                    rank=1,
                    composite_score=1.0,
                    outcome="succeeded",
                    reason=reason,
                    yield_count=yield_count,
                )],
                selected_source_ids=[source_id],
                succeeded=True,
            )
            self.capability_decisions = [
                replacement if decision.capability == capability.value else decision
                for decision in self.capability_decisions
            ]

        record_materialized_capability(
            Capability.INDEX_CONSTITUENTS,
            "egx_universe_seed",
            "Satisfied by the materialized official UniverseProvider snapshot.",
            len(universe_tickers),
        )
        price_result = self.collection_results.get("egx_price_composite")
        if price_result is not None and price_result.price_bars_written > 0:
            record_materialized_capability(
                Capability.MARKET_BREADTH,
                "egx_price_composite",
                "Derived from collected price bars across the complete UniverseProvider.",
                price_result.price_bars_written,
            )

        attempted_ids = (
            set(self.collection_results)
            | set(self.materialized_source_results)
            | set(self.collector_failures)
        )
        wired_ids = live_wired_source_ids(self.registry)
        self._standby = {
            source_id: (
                "Live collector is wired and ready as a fallback, but was not selected "
                "because a higher-ranked strategy already satisfied its capability this run."
            )
            for source_id in sorted(wired_ids - attempted_ids)
        }
        self._unavailable = unavailable_sources(
            self.registry, attempted_ids | set(self._standby)
        )

        succeeded = len(self.collection_results)
        attempted = succeeded + len(self.collector_failures)
        if attempted == 0:
            return (
                StageStatus.SKIPPED,
                "No capability had a collectable strategy ready to attempt this run.",
                [],
            )
        if succeeded == 0:
            return StageStatus.FAILED, f"All {attempted} attempted collector(s) failed.", failures
        if failures:
            return StageStatus.PARTIAL, f"{succeeded}/{attempted} collector(s) succeeded.", failures
        return StageStatus.SUCCEEDED, f"{succeeded}/{attempted} collector(s) succeeded.", []

    def _stage_raw_archive(self):
        if self.raw_documents is None:
            return StageStatus.SKIPPED, "No raw document repository available.", []
        count = len(self.raw_documents.all_latest())
        return (
            StageStatus.SUCCEEDED,
            f"{count} raw document(s) archived (content-addressed, write-once).",
            [],
        )

    def _stage_canonical_transformation(self):
        if not self.collection_results:
            return StageStatus.SKIPPED, "No collection results to transform.", []
        prices = sum(r.price_bars_written for r in self.collection_results.values())
        macro = sum(r.macro_observations_written for r in self.collection_results.values())
        news = sum(r.news_items_written for r in self.collection_results.values())
        return (
            StageStatus.SUCCEEDED,
            f"Canonical transformation produced {prices} price bar(s), "
            f"{macro} macro observation(s), {news} news item(s).",
            [],
        )

    def _stage_validation(self):
        if not self.collection_results:
            return StageStatus.SKIPPED, "No collection results to validate.", []
        materialized = sum(r.batches_materialized for r in self.collection_results.values())
        withheld = sum(r.batches_withheld for r in self.collection_results.values())
        status = StageStatus.SUCCEEDED if withheld == 0 else StageStatus.PARTIAL
        return (
            status,
            f"{materialized} batch(es) materialized, {withheld} withheld below the "
            f"confidence floor (never silently degraded).",
            [],
        )

    def _stage_event_platform(self):
        if self.event_platform is None:
            self.event_platform = EventPlatform(
                repository=EventRepository(self.data_dir / "events.json")
            )
        self.events_before = len(self.event_platform.repository.all_latest())
        return (
            StageStatus.SUCCEEDED,
            f"{self.events_before} event(s) registered in the Event Platform so far.",
            [],
        )

    def _stage_market_memory(self, as_of: date):
        if self.event_platform is None:
            self.event_platform = EventPlatform(
                repository=EventRepository(self.data_dir / "events.json")
            )
        self.market_memory = MarketMemory(
            LocalCsvDataProvider(self.data_dir),
            self.universe_provider,
            StaticSectorProvider(),
            macro_series_ids=self.macro_series_ids,
            lookback_days=30,
            event_platform=self.event_platform,
        )
        state = self.market_memory.reconstruct(as_of)
        self.market_state_summary = (
            f"Reconstructed market state as of {as_of}: "
            f"{len(state.constituents)} constituent(s), {len(state.events)} event(s) this snapshot."
        )
        return StageStatus.SUCCEEDED, self.market_state_summary, []

    def _stage_knowledge_base(self):
        self.knowledge_store = KnowledgeStore(self.data_dir / "knowledge.json")
        self.genome = AlphaGenome(self.data_dir / "genes.json")
        self.knowledge_before = len(self.knowledge_store.all_latest())
        self.genome_before = len(self.genome.repository.all_latest())
        return (
            StageStatus.SUCCEEDED,
            f"Knowledge base ready: {self.knowledge_before} promoted knowledge object(s) so far.",
            [],
        )

    def _stage_research_pipeline(self, start: date, end: date):
        if self.market_memory is None or self.knowledge_store is None or self.genome is None:
            return StageStatus.SKIPPED, "Market memory or knowledge base not ready.", []

        tickers = self._tickers(end)
        agents = [
            MarketStructureAgent(
                ticker_pairs=[(a, b) for i, a in enumerate(tickers) for b in tickers[i + 1 :]],
                max_findings=250,
            ),
            MacroAgent(),
            CorporateEventsAgent(),
            LiquidityAgent(),
            TechnicalStructureAgent(),
        ]
        daily_pipeline = DailyResearchPipeline(
            self.market_memory,
            agents,
            hypothesis_repository=HypothesisRepository(self.data_dir / "hypotheses.json"),
            knowledge_store=self.knowledge_store,
            genome=self.genome,
            paper_repository=PaperRepository(self.data_dir / "papers.json"),
            graph=KnowledgeGraph(
                self.data_dir / "graph_nodes.json", self.data_dir / "graph_edges.json"
            ),
        )
        runtime_engine = RuntimeEngine(
            daily_pipeline, run_records=RunRecordRepository(self.data_dir / "runs.json")
        )
        records = runtime_engine.run_range(start, end)
        self.run_records_this_execution = records
        for record in records:
            print(
                f"{record.run_date} {record.status.value}: "
                f"{record.hypotheses} hypotheses, {record.promoted} promoted"
                + (f" ({record.error})" if record.error else "")
            )

        statuses = [r.status for r in records]
        warnings = [f"{r.run_date}: {r.error}" for r in records if r.status == RunStatus.FAILED]
        if all(s == RunStatus.FAILED for s in statuses):
            return StageStatus.FAILED, f"All {len(records)} day(s) failed.", warnings
        if any(s == RunStatus.FAILED for s in statuses):
            return (
                StageStatus.PARTIAL,
                f"{sum(1 for s in statuses if s == RunStatus.SUCCEEDED)}/{len(records)} day(s) succeeded.",
                warnings,
            )
        return (
            StageStatus.SUCCEEDED,
            f"{len(records)} day(s) processed "
            f"({sum(1 for s in statuses if s == RunStatus.SUCCEEDED)} succeeded, "
            f"{sum(1 for s in statuses if s == RunStatus.SKIPPED_NON_TRADING)} non-trading).",
            [],
        )

    def _stage_genome(self):
        if self.genome is None:
            return StageStatus.SKIPPED, "No genome available.", []
        self.genome_after = len(self.genome.repository.all_latest())
        if self.knowledge_store is not None:
            self.knowledge_after = len(self.knowledge_store.all_latest())
        return (
            StageStatus.SUCCEEDED,
            f"{self.genome_after} gene(s) total ({self.genome_after - self.genome_before} new this "
            f"execution).",
            [],
        )

    def _stage_investment_case_generator(self):
        if self.knowledge_store is None or self.event_platform is None:
            return StageStatus.SKIPPED, "Knowledge base not ready.", []
        succeeded_dates = sorted(
            r.run_date for r in self.run_records_this_execution if r.status == RunStatus.SUCCEEDED
        )
        as_of = succeeded_dates[-1] if succeeded_dates else None
        self.investment_cases = production_artifacts.export_investment_cases(
            self.knowledge_store,
            self.event_platform,
            tickers=self._tickers(as_of),
            as_of=as_of,
        )
        if as_of is None:
            return (
                StageStatus.SKIPPED,
                "No successfully-completed trading day this execution; no investment case generated.",
                [],
            )
        n = len(self.investment_cases["recommendations"])
        return (
            StageStatus.SUCCEEDED,
            f"{n} recommendation(s) as of {as_of}; portfolio constructed.",
            [],
        )

    def _stage_dashboard_artifact_generator(self, dashboard_out: Path, end: date):
        if self.knowledge_store is None or self.market_memory is None:
            return StageStatus.SKIPPED, "Nothing to export yet.", []
        dashboard_out.mkdir(parents=True, exist_ok=True)

        succeeded_dates = sorted(
            r.run_date for r in self.run_records_this_execution if r.status == RunStatus.SUCCEEDED
        )
        as_of = succeeded_dates[-1] if succeeded_dates else None

        counts = write_dashboard_artifacts(
            knowledge_store=self.knowledge_store,
            event_repository=self.event_platform.repository,
            runs=RunRecordRepository(self.data_dir / "runs.json"),
            memory=self.market_memory,
            as_of=as_of,
            out_dir=dashboard_out,
            registry=self.registry,
        )

        investment_cases = self.investment_cases or {
            "as_of": None,
            "recommendations": [],
            "portfolio": None,
        }
        (dashboard_out / "investment_cases.json").write_text(
            json.dumps(investment_cases, indent=2, sort_keys=True) + "\n"
        )
        counts["investment_cases.json"] = len(investment_cases["recommendations"])

        collector_status = production_artifacts.export_collector_status(
            self.registry,
            {**self.collection_results, **self.materialized_source_results},
            unavailable=self._unavailable,
            failures=self.collector_failures,
            standby=self._standby,
        )
        (dashboard_out / "collector_status.json").write_text(
            json.dumps(collector_status, indent=2, sort_keys=True) + "\n"
        )
        counts["collector_status.json"] = len(collector_status)

        last_record = (
            self.run_records_this_execution[-1] if self.run_records_this_execution else None
        )
        runtime_status = production_artifacts.export_runtime_status(last_record)
        (dashboard_out / "runtime_status.json").write_text(
            json.dumps(runtime_status, indent=2, sort_keys=True) + "\n"
        )
        counts["runtime_status.json"] = 1 if runtime_status else 0

        genes = production_artifacts.export_genes(self.genome) if self.genome else []
        (dashboard_out / "genes.json").write_text(
            json.dumps(genes, indent=2, sort_keys=True) + "\n"
        )
        counts["genes.json"] = len(genes)

        papers = production_artifacts.export_papers(PaperRepository(self.data_dir / "papers.json"))
        (dashboard_out / "papers.json").write_text(
            json.dumps(papers, indent=2, sort_keys=True) + "\n"
        )
        counts["papers.json"] = len(papers)

        hypotheses = production_artifacts.export_hypotheses(
            HypothesisRepository(self.data_dir / "hypotheses.json")
        )
        (dashboard_out / "hypotheses.json").write_text(
            json.dumps(hypotheses, indent=2, sort_keys=True) + "\n"
        )
        counts["hypotheses.json"] = len(hypotheses)

        knowledge_graph = production_artifacts.export_knowledge_graph(
            KnowledgeGraph(self.data_dir / "graph_nodes.json", self.data_dir / "graph_edges.json")
        )
        (dashboard_out / "knowledge_graph.json").write_text(
            json.dumps(knowledge_graph, indent=2, sort_keys=True) + "\n"
        )
        counts["knowledge_graph.json"] = len(knowledge_graph["nodes"])

        financial_statements = production_artifacts.export_financial_statements(
            self.data_dir, self._tickers(as_of), as_of
        )
        (dashboard_out / "financial_statements.json").write_text(
            json.dumps(financial_statements, indent=2, sort_keys=True) + "\n"
        )
        counts["financial_statements.json"] = len(financial_statements)

        decision_readiness_rows = []
        if as_of is not None:
            state = self.market_memory.reconstruct(as_of)
            decision_readiness_rows = assess_decision_readiness(
                state,
                CollectedFinancialStatementProvider(self.data_dir),
                self.knowledge_store.all_latest(),
            )
        decision_readiness = [row.model_dump(mode="json") for row in decision_readiness_rows]
        (dashboard_out / "decision_readiness.json").write_text(
            json.dumps(decision_readiness, indent=2, sort_keys=True) + "\n"
        )
        counts["decision_readiness.json"] = len(decision_readiness)

        ticker_data_gap_report = production_artifacts.export_ticker_data_gap_report(
            decision_readiness_rows
        )
        (dashboard_out / "ticker_data_gap_report.json").write_text(
            json.dumps(ticker_data_gap_report, indent=2, sort_keys=True) + "\n"
        )
        counts["ticker_data_gap_report.json"] = len(ticker_data_gap_report)

        acquisition_decisions = production_artifacts.export_acquisition_decisions(
            self.capability_decisions
        )
        (dashboard_out / "acquisition_decisions.json").write_text(
            json.dumps(acquisition_decisions, indent=2, sort_keys=True) + "\n"
        )
        counts["acquisition_decisions.json"] = len(acquisition_decisions)

        source_metrics = production_artifacts.export_source_metrics(
            self.registry,
            self.metrics or SourceMetricsRepository(self.data_dir / "source_metrics.json"),
        )
        (dashboard_out / "source_metrics.json").write_text(
            json.dumps(source_metrics, indent=2, sort_keys=True) + "\n"
        )
        counts["source_metrics.json"] = len(source_metrics)

        decision_routes = export_decision_routes(self.registry)
        (dashboard_out / "decision_source_routes.json").write_text(
            json.dumps(decision_routes, indent=2, sort_keys=True) + "\n"
        )
        counts["decision_source_routes.json"] = len(decision_routes)

        dashboard_metrics = production_artifacts.export_dashboard_metrics(dashboard_out, counts)
        (dashboard_out / "dashboard_metrics.json").write_text(
            json.dumps(dashboard_metrics, indent=2, sort_keys=True) + "\n"
        )
        counts["dashboard_metrics.json"] = len(counts)

        self.dashboard_counts = counts
        return (
            StageStatus.SUCCEEDED,
            f"{len(counts)} artifact(s) written to {dashboard_out}.",
            [],
        )

    def _stage_mission_control_update(self, report: ExecutionReport, dashboard_out: Path):
        history = PipelineExecutionRepository(self.data_dir / "pipeline_executions.json")
        history.add(report)
        status = build_mission_control_status(report, history)
        dashboard_out.mkdir(parents=True, exist_ok=True)
        (dashboard_out / "mission_status.json").write_text(
            json.dumps(status.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        )
        return (
            StageStatus.SUCCEEDED,
            f"Mission Control updated: pipeline_status={status.pipeline_status.value}, "
            f"total_executions={status.total_executions}.",
            [],
        )

    def _stage_execution_report(self, report: ExecutionReport, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n")
        return StageStatus.SUCCEEDED, f"Execution report written to {path}.", []


__all__ = ["ARTIFACT_FILENAMES", "ExecutionMode", "ProductionPipeline"]
