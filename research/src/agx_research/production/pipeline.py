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

from agx_research.acquisition_intelligence.continuity import AcquisitionContinuityMonitor
from agx_research.acquisition_intelligence.engine import AcquisitionIntelligenceEngine
from agx_research.acquisition_intelligence.live import (
    build_live_fetch_text,
    build_live_prober,
    build_live_robots_checker,
)
from agx_research.acquisition_intelligence.target import seed_target_organizations
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
from agx_research.genome.service import AlphaGenome
from agx_research.hypotheses.repository import HypothesisRepository
from agx_research.knowledge.store import KnowledgeStore
from agx_research.market_memory.memory import MarketMemory
from agx_research.orchestration.pipeline import DailyResearchPipeline
from agx_research.papers.repository import PaperRepository
from agx_research.production import artifacts as production_artifacts
from agx_research.production.collector_plan import (
    EXPECTED_RECORDS,
    ExecutionMode,
    build_collector_plan,
)
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
from agx_research.universe.sector import StaticSectorProvider
from agx_research.universe.static import StaticUniverseProvider

_DEFAULT_MACRO_SERIES = ["BRENT_USD", "EGP_USD", "egypt_cpi_inflation"]


class ProductionPipeline:
    def __init__(
        self,
        *,
        data_dir: Path | str,
        tickers: list[str],
        macro_series_ids: list[str] | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tickers = tickers
        self.macro_series_ids = macro_series_ids or list(_DEFAULT_MACRO_SERIES)

        # Populated by stages as they run; downstream stages check these
        # rather than assume a prior stage succeeded.
        self.registry: SourceRegistry | None = None
        self.raw_documents: RawDocumentRepository | None = None
        self.event_platform: EventPlatform | None = None
        self.collection_results: dict[str, CollectionRunResult] = {}
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

    # ---- the public entrypoint ----------------------------------------

    def run(
        self,
        start: date,
        end: date | None = None,
        *,
        mode: ExecutionMode = ExecutionMode.MOCK,
        dashboard_out: Path | None = None,
    ) -> ExecutionReport:
        end = end or start
        if end < start:
            raise ValueError("end must be on or after start")
        dashboard_out = dashboard_out or (self.data_dir / "dashboard")

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
                    name=name, status=status, started_at=stage_started,
                    completed_at=stage_completed,
                    duration_seconds=(stage_completed - stage_started).total_seconds(),
                    detail=detail, error=error,
                )
                stages.append(result)
                return result
            stage_completed = datetime.now()
            warnings.extend(stage_warnings)
            result = StageResult(
                name=name, status=status, started_at=stage_started,
                completed_at=stage_completed,
                duration_seconds=(stage_completed - stage_started).total_seconds(),
                detail=detail, warnings=stage_warnings,
            )
            stages.append(result)
            return result

        execute(StageName.ENTRYPOINT, lambda: (
            StageStatus.SUCCEEDED,
            f"Production pipeline v{PIPELINE_VERSION} started for {start}..{end}, mode={mode.value}.",
            [],
        ))
        execute(StageName.SOURCE_REGISTRY, self._stage_source_registry)
        execute(StageName.DISCOVERY_ENGINE, self._stage_discovery_engine)
        execute(StageName.COLLECTOR_SELECTION, lambda: self._stage_collector_selection(mode))
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
                (start + timedelta(days=i)).isoformat()
                for i in range((end - start).days + 1)
            ],
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=(completed_at - started_at).total_seconds(),
            overall_status=derive_overall_status(stages),
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
                "overall_status": derive_overall_status(stages),
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

    # ---- individual stages ---------------------------------------------

    def _stage_source_registry(self):
        self.registry = seed_registry(SourceRegistry(self.data_dir / "source_registry.json"))
        return (
            StageStatus.SUCCEEDED,
            f"{len(self.registry.all_latest())} source(s) catalogued; "
            f"{len(self.registry.collectable())} collectable.",
            [],
        )

    def _stage_discovery_engine(self):
        if self.registry is None:
            return StageStatus.SKIPPED, "No registry available.", []
        fetcher = HttpFetcher()
        engine = AcquisitionIntelligenceEngine(
            prober=build_live_prober(fetcher),
            fetch_text=build_live_fetch_text(fetcher),
            robots_checker=build_live_robots_checker(fetcher),
            registry=self.registry,
        )
        monitor = AcquisitionContinuityMonitor(engine, seed_target_organizations())
        results = monitor.check_and_recover(self.registry)
        recovered = sum(1 for r in results if r.registered)
        return (
            StageStatus.SUCCEEDED,
            f"{len(results)} DOWN source(s) needed recovery; {recovered} recovered.",
            [],
        )

    def _stage_collector_selection(self, mode: ExecutionMode):
        if self.registry is None:
            return StageStatus.SKIPPED, "No registry available.", []
        self.raw_documents = RawDocumentRepository(self.data_dir / "raw_documents.json")
        self._planned = build_collector_plan(
            self.registry, mode=mode, raw_documents=self.raw_documents, tickers=self.tickers,
        )
        if not self._planned:
            return (
                StageStatus.SKIPPED,
                "No collectable source matched this pipeline's collector plan.",
                [],
            )
        return (
            StageStatus.SUCCEEDED,
            f"Selected {len(self._planned)} collector(s): "
            f"{', '.join(p.source_id for p in self._planned)} (mode={mode.value}).",
            [],
        )

    def _stage_collector_execution(self):
        planned = getattr(self, "_planned", None)
        if not planned:
            return StageStatus.SKIPPED, "No collectors selected.", []

        self.event_platform = EventPlatform(repository=EventRepository(self.data_dir / "events.json"))
        service = CollectionService(
            self.data_dir,
            raw_documents=self.raw_documents,
            event_platform=self.event_platform,
            provenance_index=ProvenanceIndexRepository(self.data_dir / "provenance_index.json"),
            metrics=SourceMetricsRepository(self.data_dir / "source_metrics.json"),
            health_monitor=HealthMonitor(HealthAlertRepository(self.data_dir / "health_alerts.json")),
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
                failures.append(f"{plan.source_id}: {type(exc).__name__}: {exc}")

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

    def _stage_raw_archive(self):
        if self.raw_documents is None:
            return StageStatus.SKIPPED, "No raw document repository available.", []
        count = len(self.raw_documents.all_latest())
        return StageStatus.SUCCEEDED, f"{count} raw document(s) archived (content-addressed, write-once).", []

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
            StaticUniverseProvider(),
            StaticSectorProvider(),
            tickers=self.tickers,
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

        agents = [
            MarketStructureAgent(
                ticker_pairs=[
                    (a, b) for i, a in enumerate(self.tickers) for b in self.tickers[i + 1 :]
                ]
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
            self.knowledge_store, self.event_platform, tickers=self.tickers, as_of=as_of,
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
            tickers=self.tickers,
            as_of=as_of,
            out_dir=dashboard_out,
        )

        investment_cases = self.investment_cases or {"as_of": None, "recommendations": [], "portfolio": None}
        (dashboard_out / "investment_cases.json").write_text(
            json.dumps(investment_cases, indent=2, sort_keys=True) + "\n"
        )
        counts["investment_cases.json"] = len(investment_cases["recommendations"])

        collector_status = production_artifacts.export_collector_status(
            self.registry, self.collection_results
        )
        (dashboard_out / "collector_status.json").write_text(
            json.dumps(collector_status, indent=2, sort_keys=True) + "\n"
        )
        counts["collector_status.json"] = len(collector_status)

        last_record = self.run_records_this_execution[-1] if self.run_records_this_execution else None
        runtime_status = production_artifacts.export_runtime_status(last_record)
        (dashboard_out / "runtime_status.json").write_text(
            json.dumps(runtime_status, indent=2, sort_keys=True) + "\n"
        )
        counts["runtime_status.json"] = 1 if runtime_status else 0

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


__all__ = ["ProductionPipeline", "ExecutionMode", "ARTIFACT_FILENAMES"]
