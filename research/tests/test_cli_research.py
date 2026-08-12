"""CLI-level coverage for `agx research ...` -- the subcommand group had
no dedicated test at all before this (each stage was only proven at the
`PatternDiscoveryEngine`/module level in `test_pattern_*.py`). Uses the
tiny 10-day/2-ticker mock fixture (`--source mock`, the default) so every
stage runs in well under a second; the point is proving the CLI wiring
(argument parsing, dispatch, JSON output shape) is correct, not repeating
the statistical-behavior proofs `test_pattern_engine.py` already owns --
zero candidates/patterns at this sample size is the expected, honest
result here, same as `docs/PATTERN_DISCOVERY_REPORT.md`'s real run.
"""

from __future__ import annotations

import json

from agx_research import cli


def test_discover_validate_final_holdout_chain_runs_clean_on_the_mock_fixture(tmp_path, capsys):
    exit_code = cli.main(
        ["--data-dir", str(tmp_path), "research", "discover", "--as-of", "2026-06-14", "--tickers", "COMI,MFPC"]
    )
    assert exit_code == 0
    discover_payload = json.loads(capsys.readouterr().out)
    assert discover_payload["candidates_generated"] == 0  # below every stage's sample-size floor, as expected

    exit_code = cli.main(
        ["--data-dir", str(tmp_path), "research", "validate", "--as-of", "2026-06-14", "--tickers", "COMI,MFPC"]
    )
    assert exit_code == 0
    validate_payload = json.loads(capsys.readouterr().out)
    assert validate_payload["patterns_considered"] == 0

    exit_code = cli.main(
        ["--data-dir", str(tmp_path), "research", "final-holdout", "--as-of", "2026-06-14", "--tickers", "COMI,MFPC"]
    )
    assert exit_code == 0
    holdout_payload = json.loads(capsys.readouterr().out)
    assert holdout_payload["patterns_validated"] == 0


def test_patterns_list_is_empty_before_any_discovery_run(tmp_path, capsys):
    exit_code = cli.main(["--data-dir", str(tmp_path), "research", "patterns"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == []


def test_failure_profile_and_cost_sensitivity_are_clean_no_ops_with_no_validated_patterns(tmp_path, capsys):
    exit_code = cli.main(
        ["--data-dir", str(tmp_path), "research", "failure-profile", "--as-of", "2026-06-14", "--tickers", "COMI,MFPC"]
    )
    assert exit_code == 0
    profiles = json.loads(capsys.readouterr().out)
    assert profiles == []

    exit_code = cli.main(
        ["--data-dir", str(tmp_path), "research", "cost-sensitivity", "--as-of", "2026-06-14", "--tickers", "COMI,MFPC"]
    )
    assert exit_code == 0
    reports = json.loads(capsys.readouterr().out)
    assert reports == []


def test_control_suite_runs_and_reports_a_summary_per_control(capsys):
    exit_code = cli.main(
        ["research", "control-suite", "--positive-seeds", "1", "--negative-seeds", "1"]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    names = {s["control_name"] for s in payload["summaries"]}
    assert names == {
        "momentum", "mean_reversion", "lead_lag",
        "pure_noise", "shuffled_returns", "shuffled_timestamps", "independent_random_predictor",
    }
    for summary in payload["summaries"]:
        assert summary["seeds_run"] == 1


def test_control_suite_defaults_to_two_seeds_when_not_specified(capsys):
    exit_code = cli.main(["research", "control-suite", "--positive-seeds", "1", "--negative-seeds", "1,2"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    by_kind = {s["control_name"]: s["seeds_run"] for s in payload["summaries"]}
    assert by_kind["momentum"] == 1
    assert by_kind["pure_noise"] == 2
