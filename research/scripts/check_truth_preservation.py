"""Truth Preservation static analysis (AD-60, docs/TRUTH_PRESERVATION_POLICY.md).

Fails (non-zero exit) whenever this codebase's zero-fabrication policy is
violated in a way a machine check can catch. This is a floor, not a
ceiling -- it catches the exact `06a6882` regression and known-shape
variants of it; it does not replace review judgment for a genuinely new
fabrication pattern (see the policy doc's Pull Request Checklist for that).

Run via `uv run python scripts/check_truth_preservation.py` from
`research/` (also invoked by `tests/test_truth_preservation.py`, so plain
`pytest` catches a regression too, and by CI, so a PR does).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_SRC = REPO_ROOT / "research" / "src" / "agx_research"
WEB_SRC = REPO_ROOT / "web" / "src"
API_SRC = REPO_ROOT / "api" / "src"
RESEARCH_TESTS = REPO_ROOT / "research" / "tests"
WEB_TEST = REPO_ROOT / "web" / "test"

SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".json"}
SCAN_ROOTS = (RESEARCH_SRC, WEB_SRC, API_SRC)

# 1. Exact-phrase denylist: the literal strings the 06a6882 incident
# actually introduced. A byte-for-byte regression is caught here even
# before any structural check below runs.
BANNED_EXACT_PHRASES = [
    "Active free public feed connected and operational",
    "Public free collector endpoint active",
    "Public terms verified; open access endpoint active",
    "Source standby mode active",
    "Configured via registry fallback capability.",
    "client_decision_engine",
    "client_capital_allocation_engine",
    "smartlist-ive-v2.2-fallback",
]

# Narrower substrings for paraphrased variants of the same false-availability
# claim. Deliberately does not include bare words like "verified" or
# "active" alone -- those appear inside honest phrasing too ("not yet
# verified against a real fetch"), so only distinctive multi-word phrases
# that only make sense as an affirmative operational claim are listed.
BANNED_STATUS_SUBSTRINGS = [
    "operational",
    "endpoint active",
    "mode active",
    "connected and",
    "feed connected",
]

# Decision-action labels that may only be produced by
# agx_research.meta.decision_engine.DecisionAction or
# agx_research.decision_service (PositionAction on the TS side). Matches
# `action` (or `required_action`) being ASSIGNED one of these literals --
# not read, not used as an object key in a display-mapping table.
DECISION_LITERAL_ASSIGNMENT_RE = re.compile(
    r"\b(?:action|required_action)\s*[:=]\s*[\"'](?:buy|sell|increase_position|"
    r"reduce_position|exit|no_action|hold|abstain)[\"']"
)

# Files where the type union itself is declared, or that are otherwise
# exempt (test fixtures constructing a mock artifact are not "inferring" a
# decision -- they're standing in for one already computed upstream).
FRONTEND_ASSIGNMENT_EXEMPT_SUFFIXES = (
    "types.ts",
    ".test.ts",
    ".test.tsx",
)

# A fair/intrinsic value must only ever come from a real, computed model.
# Assigning it directly from a bar's raw close price (the exact
# meta/readiness.py `06a6882` bug) is banned outright.
FAIR_VALUE_FROM_PRICE_RE = re.compile(
    r"\b(?:fair_value|weighted_fair_value|intrinsic_value|est_fair)\w*\s*=\s*"
    r"(?:round\()?\s*\w*\.close\b"
)

# Synthetic valuation-model names invented by the 06a6882 "supplementary
# fallback" rather than computed by a real model.
BANNED_SYNTHETIC_MODEL_NAMES = [
    "sector_relative",
    "base_anchor",
    "sector_bear_anchor",
    "sector_bull_anchor",
]

# Protected tests: deleting or renaming any of these without an
# equal-or-stronger replacement fails this check. Grows over time, never
# shrinks without a replacement of equal or greater strength (see the
# policy doc's Test Protection section).
PROTECTED_TESTS = {
    RESEARCH_TESTS
    / "test_fair_value_engine.py": ["test_engine_refuses_to_fabricate_value_without_share_count"],
    RESEARCH_TESTS
    / "test_decision_readiness.py": [
        "test_missing_fundamentals_and_knowledge_force_explicit_abstention"
    ],
    RESEARCH_TESTS
    / "test_capability_engine.py": [
        "test_rank_capability_strategies_marks_uncatalogued_source_not_ready",
        "test_rank_capability_strategies_orders_by_composite_and_marks_ready",
    ],
    RESEARCH_TESTS
    / "test_production_pipeline.py": [
        "test_live_mode_collects_real_endpoints_and_reports_unavailable_sources"
    ],
    RESEARCH_TESTS
    / "test_financials.py": ["test_production_path_never_fabricates_missing_financials"],
    RESEARCH_TESTS
    / "test_runtime_and_intelligence.py": [
        "test_fair_value_blends_into_investment_prediction_and_surfaces_as_evidence"
    ],
    RESEARCH_TESTS
    / "test_ticker_data_gap_report.py": [
        "test_gap_report_splits_readiness_into_five_named_layers"
    ],
}

PROTECTED_WEB_TESTS = {
    WEB_TEST
    / "StaticJsonProvider.test.ts": [
        "postDecisions always reports itself unavailable, never fabricating a decision",
        "postCapitalAllocation always reports itself unavailable, never fabricating a plan",
    ],
}


class Violation:
    def __init__(self, rule: str, path: Path, detail: str, line: int | None = None):
        self.rule = rule
        self.path = path
        self.detail = detail
        self.line = line

    def __str__(self) -> str:
        location = f"{self.path.relative_to(REPO_ROOT)}"
        if self.line is not None:
            location += f":{self.line}"
        return f"[{self.rule}] {location}: {self.detail}"


def _iter_scanned_files():
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_EXTENSIONS:
                continue
            if "__pycache__" in path.parts or "node_modules" in path.parts:
                continue
            yield path


def check_banned_phrases(violations: list[Violation]) -> None:
    # Exact phrases only here -- these are the literal strings from the
    # actual incident, precise enough to scan repo-wide with no false
    # positives. BANNED_STATUS_SUBSTRINGS is deliberately *not* applied
    # repo-wide (words like "operational" are legitimate prose all over
    # this codebase); it is only checked against the specific
    # reason-by-status dicts in check_status_reason_dicts, where every
    # value is known to be describing a non-ready source and so can never
    # legitimately contain availability language.
    for path in _iter_scanned_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for phrase in BANNED_EXACT_PHRASES:
            if phrase in text:
                line = text[: text.index(phrase)].count("\n") + 1
                violations.append(
                    Violation("banned-exact-phrase", path, f"contains banned phrase {phrase!r}", line)
                )


def check_fair_value_and_synthetic_models(violations: list[Violation]) -> None:
    for path in _iter_scanned_files():
        if path.suffix != ".py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if FAIR_VALUE_FROM_PRICE_RE.search(line):
                violations.append(
                    Violation(
                        "fair-value-from-price",
                        path,
                        f"assigns a fair/intrinsic value directly from a price close: {line.strip()!r}",
                        lineno,
                    )
                )
            for name in BANNED_SYNTHETIC_MODEL_NAMES:
                if name in line and "valuation" in str(path):
                    violations.append(
                        Violation(
                            "synthetic-valuation-model",
                            path,
                            f"references banned synthetic model name {name!r}: {line.strip()!r}",
                            lineno,
                        )
                    )


def check_decision_literal_assignment_in_frontend(violations: list[Violation]) -> None:
    for root in (WEB_SRC, API_SRC):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".ts", ".tsx"}:
                continue
            if "node_modules" in path.parts:
                continue
            if any(str(path).endswith(suffix) for suffix in FRONTEND_ASSIGNMENT_EXEMPT_SUFFIXES):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), start=1):
                if DECISION_LITERAL_ASSIGNMENT_RE.search(line):
                    violations.append(
                        Violation(
                            "frontend-decision-inference",
                            path,
                            f"assigns a decision-action literal outside DecisionService/decision_engine: {line.strip()!r}",
                            lineno,
                        )
                    )


def check_status_reason_dicts(violations: list[Violation]) -> None:
    sys.path.insert(0, str(REPO_ROOT / "research" / "src"))
    try:
        from agx_research.acquisition_intelligence.capability_engine import (
            _NOT_CATALOGUED_REASON,
            _NOT_READY_REASON_BY_STATUS,
        )
        from agx_research.production.collector_plan import (
            _UNAVAILABLE_REASON_BY_STATUS,
        )
    except ImportError as exc:  # pragma: no cover - structural check, not a runtime path
        violations.append(
            Violation(
                "status-reason-import-failed",
                RESEARCH_SRC,
                f"could not import reason-by-status dicts to validate them: {exc}",
            )
        )
        return

    dicts_to_check = {
        "capability_engine._NOT_READY_REASON_BY_STATUS": _NOT_READY_REASON_BY_STATUS,
        "capability_engine._NOT_CATALOGUED_REASON": {"_": _NOT_CATALOGUED_REASON},
        "collector_plan._UNAVAILABLE_REASON_BY_STATUS": _UNAVAILABLE_REASON_BY_STATUS,
    }
    for dict_name, mapping in dicts_to_check.items():
        for key, reason in mapping.items():
            lowered = reason.lower()
            for substring in BANNED_STATUS_SUBSTRINGS:
                if substring in lowered:
                    violations.append(
                        Violation(
                            "status-reason-false-availability",
                            RESEARCH_SRC,
                            f"{dict_name}[{key!r}] claims false availability ({substring!r}): {reason!r}",
                        )
                    )


def check_protected_tests(violations: list[Violation]) -> None:
    for path, names in PROTECTED_TESTS.items():
        if not path.exists():
            violations.append(
                Violation("protected-test-missing-file", path, "protected test file no longer exists")
            )
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in names:
            if f"def {name}(" not in text:
                violations.append(
                    Violation(
                        "protected-test-removed",
                        path,
                        f"protected test {name!r} is missing (removed, renamed, or never replaced "
                        "with an equal-or-stronger test)",
                    )
                )

    for path, names in PROTECTED_WEB_TESTS.items():
        if not path.exists():
            violations.append(
                Violation("protected-test-missing-file", path, "protected test file no longer exists")
            )
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in names:
            if name not in text:
                violations.append(
                    Violation(
                        "protected-test-removed",
                        path,
                        f"protected test {name!r} is missing (removed, renamed, or never replaced "
                        "with an equal-or-stronger test)",
                    )
                )


def run_all_checks() -> list[Violation]:
    violations: list[Violation] = []
    check_banned_phrases(violations)
    check_fair_value_and_synthetic_models(violations)
    check_decision_literal_assignment_in_frontend(violations)
    check_status_reason_dicts(violations)
    check_protected_tests(violations)
    return violations


def main() -> int:
    violations = run_all_checks()
    if not violations:
        print("check_truth_preservation: clean (no fabrication patterns detected).")
        return 0

    print(f"check_truth_preservation: {len(violations)} violation(s) found.\n")
    print("See docs/TRUTH_PRESERVATION_POLICY.md (AD-60) for what this checks and why.\n")
    for violation in violations:
        print(f"  {violation}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
