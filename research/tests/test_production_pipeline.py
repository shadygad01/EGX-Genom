"""Integration tests for the first production execution pipeline
(`agx_research.production.pipeline.ProductionPipeline`): end-to-end
execution, replay mode, failure isolation, artifact generation, and
Mission Control tracking. Every collector-level unit behavior (parsing,
quality scoring, provenance, etc.) is already covered by the collector/
service test suites -- these tests exercise the *wiring*, not the
individual systems being wired.
"""

from datetime import date

import pytest

from agx_research.production.collector_plan import ExecutionMode
from agx_research.production.pipeline import ProductionPipeline
from agx_research.production.stages import StageName, StageStatus

TICKERS = ["COMI", "MFPC", "EAST", "ETEL"]  # small universe: fast tests, still exercises pairing
RUN_DATE = date(2026, 6, 14)


def _all_stage_names_in_order(report):
    return [s.name for s in report.stages]


def test_end_to_end_mock_execution_runs_every_stage_and_succeeds(tmp_path):
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)
    report = pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK)

    assert report.overall_status == StageStatus.SUCCEEDED
    assert report.errors == []
    names = _all_stage_names_in_order(report)
    # Every stage the mission specifies appears, in order.
    assert names == list(StageName)
    assert all(s.status == StageStatus.SUCCEEDED for s in report.stages)


def test_end_to_end_execution_produces_a_real_hypothesis_from_collected_data(tmp_path):
    """Proves collector output actually reaches the research pipeline --
    the exact gap this pipeline was built to close (previously `agx collect`
    and `agx run` used two disconnected data roots).
    """
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)
    report = pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK)

    research_stage = report.stage(StageName.RESEARCH_PIPELINE)
    assert "1 day(s) processed" in research_stage.detail
    assert len(pipeline.run_records_this_execution) == 1
    assert pipeline.run_records_this_execution[0].hypotheses >= 1


def test_collector_execution_writes_data_dir_that_market_memory_reads(tmp_path):
    data_dir = tmp_path / "data"
    pipeline = ProductionPipeline(data_dir=data_dir, tickers=TICKERS)
    pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK)

    assert (data_dir / "prices" / "COMI.csv").exists()
    assert (data_dir / "prices" / "MFPC.csv").exists()
    assert (data_dir / "macro" / "BRENT_USD.csv").exists()
    assert (data_dir / "news.csv").exists()


def test_replay_mode_reproduces_the_same_research_outcome(tmp_path):
    """The pipeline must not know whether data is live or replayed: a mock
    run followed by a replay run over the same archive produces the same
    hypothesis count.
    """
    data_dir = tmp_path / "data"
    mock_pipeline = ProductionPipeline(data_dir=data_dir, tickers=TICKERS)
    mock_report = mock_pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK)
    mock_hypotheses = mock_pipeline.run_records_this_execution[0].hypotheses

    replay_pipeline = ProductionPipeline(data_dir=data_dir, tickers=TICKERS)
    replay_report = replay_pipeline.run(RUN_DATE, mode=ExecutionMode.REPLAY)
    replay_hypotheses = replay_pipeline.run_records_this_execution[0].hypotheses

    assert mock_report.overall_status == StageStatus.SUCCEEDED
    assert replay_report.overall_status == StageStatus.SUCCEEDED
    assert replay_hypotheses == mock_hypotheses


def test_replay_does_not_duplicate_raw_documents(tmp_path):
    data_dir = tmp_path / "data"
    ProductionPipeline(data_dir=data_dir, tickers=TICKERS).run(RUN_DATE, mode=ExecutionMode.MOCK)

    from agx_research.collectors.raw import RawDocumentRepository

    count_after_mock = len(RawDocumentRepository(data_dir / "raw_documents.json").all_latest())

    ProductionPipeline(data_dir=data_dir, tickers=TICKERS).run(RUN_DATE, mode=ExecutionMode.REPLAY)
    count_after_replay = len(RawDocumentRepository(data_dir / "raw_documents.json").all_latest())

    assert count_after_replay == count_after_mock


def test_replay_with_no_prior_archive_is_honest_not_fabricated(tmp_path):
    """A fresh data_dir has nothing archived yet; replay mode must report
    that honestly rather than fabricate collected data.
    """
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)
    report = pipeline.run(RUN_DATE, mode=ExecutionMode.REPLAY)

    execution_stage = report.stage(StageName.COLLECTOR_EXECUTION)
    assert execution_stage.status == StageStatus.SUCCEEDED  # ran, just fetched nothing
    for result in pipeline.collection_results.values():
        assert result.documents_fetched == 0
        assert result.batches_materialized == 0


def test_deterministic_execution_same_inputs_same_collected_values(tmp_path):
    pipeline_a = ProductionPipeline(data_dir=tmp_path / "a", tickers=TICKERS)
    pipeline_a.run(RUN_DATE, mode=ExecutionMode.MOCK)
    pipeline_b = ProductionPipeline(data_dir=tmp_path / "b", tickers=TICKERS)
    pipeline_b.run(RUN_DATE, mode=ExecutionMode.MOCK)

    comi_a = (tmp_path / "a" / "prices" / "COMI.csv").read_text()
    comi_b = (tmp_path / "b" / "prices" / "COMI.csv").read_text()
    assert comi_a == comi_b

    assert (
        pipeline_a.run_records_this_execution[0].hypotheses
        == pipeline_b.run_records_this_execution[0].hypotheses
    )


def test_failure_isolation_one_stage_failing_does_not_stop_later_stages(tmp_path, monkeypatch):
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)

    def _broken_market_memory(as_of):
        raise RuntimeError("simulated market memory failure")

    monkeypatch.setattr(pipeline, "_stage_market_memory", _broken_market_memory)
    report = pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK)

    market_memory_stage = report.stage(StageName.MARKET_MEMORY)
    assert market_memory_stage.status == StageStatus.FAILED
    assert "simulated market memory failure" in market_memory_stage.error

    # Later stages still ran (degraded, since market_memory never got set),
    # rather than the whole execution aborting.
    names_after = [s.name for s in report.stages]
    assert StageName.RESEARCH_PIPELINE in names_after
    assert StageName.DASHBOARD_ARTIFACT_GENERATOR in names_after
    assert StageName.EXECUTION_REPORT in names_after

    research_stage = report.stage(StageName.RESEARCH_PIPELINE)
    assert research_stage.status == StageStatus.SKIPPED  # honest: nothing to run without memory

    assert report.overall_status == StageStatus.PARTIAL
    assert any("simulated market memory failure" in e for e in report.errors)


def test_failure_isolation_collector_failure_marks_partial_not_total(tmp_path, monkeypatch):
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)

    original_selection = pipeline._stage_collector_selection

    def _selection_with_one_broken(mode):
        status, detail, warnings = original_selection(mode)

        class _BrokenCollector:
            def fetch(self):
                raise RuntimeError("simulated fetch failure")

        from agx_research.production.collector_plan import PlannedCollector

        pipeline._planned.append(PlannedCollector("broken_source", _BrokenCollector()))
        return status, detail, warnings

    monkeypatch.setattr(pipeline, "_stage_collector_selection", _selection_with_one_broken)
    report = pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK)

    execution_stage = report.stage(StageName.COLLECTOR_EXECUTION)
    assert execution_stage.status == StageStatus.PARTIAL
    assert any("broken_source" in w for w in execution_stage.warnings)
    # The other, healthy collectors still produced data.
    assert "stooq" in pipeline.collection_results
    assert report.overall_status in (StageStatus.PARTIAL, StageStatus.SUCCEEDED)


def test_artifact_generation_writes_every_expected_file(tmp_path):
    dashboard_out = tmp_path / "dashboard"
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)
    pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK, dashboard_out=dashboard_out)

    expected = {
        "knowledge.json", "events.json", "patterns.json", "recommendations.json",
        "market_state.json", "runtime_metrics.json", "system_status.json",
        "source_registry.json", "investment_cases.json", "collector_status.json",
        "runtime_status.json", "dashboard_metrics.json", "mission_status.json",
        "execution_report.json",
    }
    for filename in expected:
        assert (dashboard_out / filename).exists(), filename


def test_artifacts_validate_against_dashboard_validator(tmp_path):
    from agx_research.dashboard.validate import validate_dashboard_artifacts

    dashboard_out = tmp_path / "dashboard"
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)
    pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK, dashboard_out=dashboard_out)

    counts = validate_dashboard_artifacts(dashboard_out)
    assert counts["source_registry.json"] == 51
    assert "execution_report.json" in counts
    assert "mission_status.json" in counts


def test_mission_control_tracks_pipeline_execution_across_runs(tmp_path):
    import json

    data_dir = tmp_path / "data"
    dashboard_out = tmp_path / "dashboard"

    ProductionPipeline(data_dir=data_dir, tickers=TICKERS).run(
        RUN_DATE, mode=ExecutionMode.MOCK, dashboard_out=dashboard_out
    )
    first_status = json.loads((dashboard_out / "mission_status.json").read_text())
    assert first_status["pipeline_status"] == "succeeded"
    assert first_status["total_executions"] == 1
    assert first_status["last_successful_pipeline_id"] is not None
    assert first_status["last_failed_pipeline_id"] is None
    assert first_status["current_execution_mode"] == "mock"

    ProductionPipeline(data_dir=data_dir, tickers=TICKERS).run(
        RUN_DATE, mode=ExecutionMode.REPLAY, dashboard_out=dashboard_out
    )
    second_status = json.loads((dashboard_out / "mission_status.json").read_text())
    assert second_status["total_executions"] == 2
    assert second_status["current_execution_mode"] == "replay"


def test_execution_report_captures_knowledge_and_genome_deltas(tmp_path):
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)
    report = pipeline.run(RUN_DATE, mode=ExecutionMode.MOCK)

    assert report.knowledge_before == 0
    assert report.knowledge_after >= 0
    assert report.genome_before == 0
    assert report.genome_after == report.knowledge_after  # one gene per promoted knowledge object
    assert report.knowledge_delta == report.knowledge_after - report.knowledge_before


def test_pipeline_execution_repository_persists_history(tmp_path):
    from agx_research.production.report import PipelineExecutionRepository

    data_dir = tmp_path / "data"
    ProductionPipeline(data_dir=data_dir, tickers=TICKERS).run(RUN_DATE, mode=ExecutionMode.MOCK)
    ProductionPipeline(data_dir=data_dir, tickers=TICKERS).run(RUN_DATE, mode=ExecutionMode.MOCK)

    history = PipelineExecutionRepository(data_dir / "pipeline_executions.json")
    assert len(history.all_latest()) == 2
    assert history.last_successful() is not None
    assert history.last_failed() is None


def test_run_rejects_end_before_start(tmp_path):
    pipeline = ProductionPipeline(data_dir=tmp_path / "data", tickers=TICKERS)
    with pytest.raises(ValueError):
        pipeline.run(RUN_DATE, date(2026, 6, 1))


def test_cli_run_command_executes_full_pipeline(tmp_path, capsys):
    from agx_research.cli import main

    data_dir = tmp_path / "agx_data"
    exit_code = main(
        ["--data-dir", str(data_dir), "run", "--date", RUN_DATE.isoformat(), "--mode", "mock"]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert f"{RUN_DATE.isoformat()} succeeded" in out
    assert "Production pipeline" in out
    assert (data_dir / "dashboard" / "execution_report.json").exists()
