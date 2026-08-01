"""Orchestrates every repeatable scenario through every check and
assembles the final `ValidationReport`. This is the one function a CLI
command or a pytest test calls -- neither builds scenarios or calls checks
directly, so the report a human reads and the report a test asserts on are
always the same thing.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from agx_research.institutional_validation import checks, scenarios as sc
from agx_research.institutional_validation.report import CheckResult, ValidationReport

DEFAULT_AS_OF = date(2026, 6, 14)
DEFAULT_LIFECYCLE_START = date(2026, 1, 1)
_MOCK_ROOT = Path(__file__).resolve().parents[3] / "data" / "mock"


def run_institutional_validation(
    *, as_of: date = DEFAULT_AS_OF, lifecycle_start: date = DEFAULT_LIFECYCLE_START, mock_root: Path | None = _MOCK_ROOT
) -> ValidationReport:
    egx30, egx70 = sc.real_universe_tickers()
    full_universe = egx30 + egx70

    full_scenario = sc.synthetic_full_universe(full_universe, as_of, scenario_id="synthetic_full_universe")
    zero_scenario = sc.zero_evidence_universe(full_universe, as_of)
    all_avoid_scenario = sc.all_reject_universe([f"REJECT{i}" for i in range(10)], as_of)

    results: list[CheckResult] = [
        checks.check_universe_ranking(1, "EGX30", egx30, as_of, mock_root=mock_root),
        checks.check_universe_ranking(2, "EGX70", egx70, as_of, mock_root=mock_root),
        checks.check_explain_every_ranking(full_scenario),
        checks.check_rejection(full_scenario, zero_scenario),
        checks.check_hold_cash(all_avoid_scenario),
        checks.check_complete_portfolio(full_scenario),
        checks.check_benchmark_comparison(as_of, date(2026, 8, 1), mock_root=mock_root),
        checks.check_thesis_failure_detection(lifecycle_start),
        checks.check_change_attribution(lifecycle_start),
        checks.check_evidence_traceability(as_of),
    ]

    scenarios_run = [
        "real_universe_tickers",
        full_scenario.scenario_id,
        zero_scenario.scenario_id,
        all_avoid_scenario.scenario_id,
        "country_crisis_scenario",
        "thesis_lifecycle_scenario",
        "benchmark_scenario",
        "evidence_chain_scenario",
    ]
    return ValidationReport.build(scenarios_run, results)


__all__ = ["run_institutional_validation"]
