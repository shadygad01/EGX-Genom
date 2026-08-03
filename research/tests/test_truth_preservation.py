"""Permanent Truth Preservation regression suite (AD-60,
docs/TRUTH_PRESERVATION_POLICY.md).

This file is itself protected: weakening or deleting an assertion here
requires the same review scrutiny as any other protected test (see the
policy doc's Test Protection section). Its job is to make sure `pytest`
alone -- not just a separate CI step -- catches a fabrication regression,
by invoking the same static-analysis script CI runs, plus a handful of
direct structural assertions against the real modules the 06a6882
incident actually broke.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = REPO_ROOT / "research" / "scripts" / "check_truth_preservation.py"


def test_static_analysis_reports_no_fabrication_patterns():
    """The permanent static-analysis gate (also run in CI) must pass on
    every commit. See docs/TRUTH_PRESERVATION_POLICY.md for exactly what
    this checks and why."""
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT / "research",
    )
    assert result.returncode == 0, (
        "Truth Preservation static analysis failed:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_fair_value_engine_never_fabricates_below_three_real_models():
    """No output is real research until a genuine third model exists --
    the exact invariant `06a6882` broke by synthesizing candidates to
    reach the threshold instead of returning None."""
    from agx_research.financials.schema import FinancialStatementLineItem
    from agx_research.valuation.engine import FairValueEngine
    from datetime import date

    class _TwoModelOnlyProvider:
        """Only enough data for a P/E figure -- one real model, nowhere
        near the 3-model floor."""

        def get_line_items(self, ticker, start, end, *, statement_type=None):
            return [
                FinancialStatementLineItem(
                    ticker=ticker,
                    period_end_date=date(2026, 6, 30),
                    period_type="QUARTERLY",
                    statement_type="INCOME_STATEMENT",
                    line_item="eps_diluted",
                    value=1.0,
                    currency="EGP",
                )
            ]

    engine = FairValueEngine(_TwoModelOnlyProvider())
    result = engine.value("TEST", date(2026, 7, 1))
    assert result is None, (
        "FairValueEngine.value() must return None when fewer than 3 real "
        "models are available -- it must never synthesize a candidate "
        "(e.g. a hardcoded graham_number/sector_relative/anchor) to reach "
        "the threshold."
    )


def test_readiness_never_synthesizes_fair_value_from_market_price():
    """assess_decision_readiness must never construct a FairValueResult
    equal to the current price when no real fair value exists -- the
    exact `06a6882` bug in meta/readiness.py."""
    import inspect

    from agx_research.meta import readiness

    source = inspect.getsource(readiness)
    assert "FairValueResult(" not in source or "fair_value_engine.value(" in source, (
        "meta.readiness must only ever obtain a FairValueResult from a real "
        "FairValueEngine.value() call, never construct one itself as a "
        "fallback."
    )
    assert "est_fair" not in source, (
        "meta.readiness must not synthesize an estimated fair value from "
        "the current price (the est_fair fallback removed after 06a6882)."
    )


def test_source_status_reason_strings_stay_honest():
    """A source's reason string may never claim availability language for
    a status that isn't IMPLEMENTED -- the exact `06a6882` bug that
    rewrote 'not yet verified' into 'Active ... connected and operational'
    while SourceStatus itself stayed PLANNED/NEEDS_KEY/TOS_REVIEW/DISABLED."""
    from agx_research.acquisition_intelligence.capability_engine import (
        _NOT_READY_REASON_BY_STATUS,
    )
    from agx_research.production.collector_plan import _UNAVAILABLE_REASON_BY_STATUS

    banned_substrings = ["operational", "endpoint active", "mode active", "connected and"]
    for mapping in (_NOT_READY_REASON_BY_STATUS, _UNAVAILABLE_REASON_BY_STATUS):
        for status, reason in mapping.items():
            lowered = reason.lower()
            for substring in banned_substrings:
                assert substring not in lowered, (
                    f"{status} reason {reason!r} falsely claims availability "
                    f"({substring!r}) for a source that is not IMPLEMENTED."
                )


@pytest.mark.parametrize(
    "test_file,test_name",
    [
        ("test_fair_value_engine.py", "test_engine_refuses_to_fabricate_value_without_share_count"),
        (
            "test_decision_readiness.py",
            "test_missing_fundamentals_and_knowledge_force_explicit_abstention",
        ),
        (
            "test_capability_engine.py",
            "test_rank_capability_strategies_marks_uncatalogued_source_not_ready",
        ),
        (
            "test_capability_engine.py",
            "test_rank_capability_strategies_orders_by_composite_and_marks_ready",
        ),
        (
            "test_production_pipeline.py",
            "test_live_mode_collects_real_endpoints_and_reports_unavailable_sources",
        ),
        ("test_financials.py", "test_production_path_never_fabricates_missing_financials"),
        (
            "test_runtime_and_intelligence.py",
            "test_fair_value_blends_into_investment_prediction_and_surfaces_as_evidence",
        ),
        (
            "test_ticker_data_gap_report.py",
            "test_gap_report_splits_readiness_into_five_named_layers",
        ),
    ],
)
def test_protected_test_still_exists(test_file, test_name):
    """Deleting or renaming any of these without an equal-or-stronger
    replacement is a Test Protection violation (see the policy doc)."""
    path = Path(__file__).resolve().parent / test_file
    assert path.exists(), f"protected test file {test_file} no longer exists"
    text = path.read_text(encoding="utf-8")
    assert f"def {test_name}(" in text, (
        f"protected test {test_name!r} is missing from {test_file} -- it must not be "
        "removed or renamed without an equal-or-stronger replacement"
    )
