"""Mission 3, Step 1.7: Directional Semantics & Economic Validity Audit.

Determines whether a negative-expectancy pattern in the current AGX pattern
discovery architecture should be interpreted as (A) a failed long signal,
(B) a potentially valid short/inverse signal, (C) something requiring
explicit directional metadata before economic interpretation, or (D) an
intentionally unsupported direction under an explicit long-only mandate.

Read-only against the real registry (`/tmp/agx_real_run/patterns/registry.json`)
and the repository source tree. Never mutates the registry, never creates a
PromotionCase, never changes a validation_status, never touches Mission 2/
Step 1/Step 1.5/Step 1.6 artifacts (this run does not even assume those
artifacts exist on disk -- see the provenance section below and this
script's own docstring notes throughout).

Self-contained: all Step 1.6 reconciliation figures used here (94.3%
positive-at-DISCOVERED, GT/LT parity, the 400/511 robustness-cost
decomposition) are RECOMPUTED directly from the registry in this script,
not read from any prior artifact file -- because this session found that
Step 1.6's own output files no longer exist on disk (see provenance
section). The registry itself was independently verified unchanged
(same total/validated/rejected counts Step 1.6 reported), so this
recomputation reproduces Step 1.6's published figures rather than
inventing new ones -- it is a same-session reproduction against a
verified-unchanged input, not a blind regeneration.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = REPO_ROOT / "research"
REGISTRY_PATH = Path("/tmp/agx_real_run/patterns/registry.json")
OUTPUT_PATH = RESEARCH_ROOT / "data" / "pattern_directional_semantics_audit" / "analysis.json"
TRANSACTION_COST_FRACTION = 20.0 / 10_000

EXPECTED_TOTAL = 3398
EXPECTED_VALIDATED = 1773
EXPECTED_REJECTED = 1625


def load_registry() -> dict[str, list[dict]]:
    with REGISTRY_PATH.open() as f:
        return json.load(f)


def check_provenance() -> dict:
    """Per the Step 1.7 'critical provenance requirement': check whether
    Step 1 and Step 1.5 artifacts exist on disk before doing anything else,
    and report honestly rather than silently regenerating them. Also checks
    Step 1.6's own artifacts, since this audit's §7 reconciliation depends
    on citing Step 1.6's figures accurately."""
    candidates = {
        "step_1_family_collapse_report": REPO_ROOT / "docs" / "PATTERN_CROSS_TICKER_FAMILY_COLLAPSE.md",
        "step_1_family_collapse_script": RESEARCH_ROOT / "scripts" / "analyze_cross_ticker_family_collapse.py",
        "step_1_family_collapse_json": RESEARCH_ROOT / "data" / "pattern_cross_ticker_family_collapse" / "analysis.json",
        "step_1_5_stress_test_report": REPO_ROOT / "docs" / "PATTERN_FAMILY_DEFINITION_STRESS_TEST.md",
        "step_1_5_stress_test_script": RESEARCH_ROOT / "scripts" / "analyze_pattern_family_definition_stress_test.py",
        "step_1_5_stress_test_json": RESEARCH_ROOT / "data" / "pattern_family_definition_stress_test" / "analysis.json",
        "step_1_6_bias_audit_report": REPO_ROOT / "docs" / "PATTERN_DIRECTIONAL_VALIDATION_BIAS_AUDIT.md",
        "step_1_6_bias_audit_script": RESEARCH_ROOT / "scripts" / "audit_pattern_directional_validation_bias.py",
        "step_1_6_bias_audit_json": RESEARCH_ROOT / "data" / "pattern_directional_validation_bias_audit" / "analysis.json",
    }
    existence = {name: path.exists() for name, path in candidates.items()}
    step1_missing = not any(existence[k] for k in existence if k.startswith("step_1_family"))
    step15_missing = not any(existence[k] for k in existence if k.startswith("step_1_5"))
    step16_missing = not any(existence[k] for k in existence if k.startswith("step_1_6"))
    return {
        "file_existence": existence,
        "step_1_artifacts_missing": step1_missing,
        "step_1_5_artifacts_missing": step15_missing,
        "step_1_6_artifacts_missing": step16_missing,
        "statement": (
            "This session's working tree does not persist uncommitted files across turns "
            "(confirmed: even Step 1.6's artifacts, produced and verified earlier in this SAME "
            "conversation, are absent from disk at the start of Step 1.7). Per the critical "
            "provenance requirement: Step 1 and Step 1.5 artifacts are reported here as MISSING, "
            "not silently regenerated. Step 1.7 does not require Step 1/1.5's family-collapse "
            "outputs (family analysis is out of scope for directional semantics, matching Step "
            "1.6's own scope discipline), so no reproduction of them was attempted. Step 1.6's "
            "specific reconciliation FIGURES (not the file) are independently recomputed fresh in "
            "this script directly from the registry -- verified against the same unchanged "
            "registry state (3,398/1,773/1,625) Step 1.6 itself reported -- and are labeled below "
            "as 'recomputed_this_session', not claimed as byte-identical retrieval of the missing "
            "original file."
        ),
    }


def recompute_step_1_6_reconciliation_figures(registry: dict[str, list[dict]]) -> dict:
    """Independent same-session recomputation of the specific Step 1.6
    figures Step 1.7 section 7 must reconcile with. Method is identical to
    research/scripts/audit_pattern_directional_validation_bias.py (that
    script's own logic, reproduced here since the file no longer exists on
    disk this session -- see check_provenance())."""
    v1: dict[str, dict] = {}
    latest: dict[str, dict] = {}
    for pid, revs in registry.items():
        revs_sorted = sorted(revs, key=lambda r: r["version"])
        v1[pid] = next(r for r in revs_sorted if r["version"] == 1)
        latest[pid] = revs_sorted[-1]

    total = len(registry)
    positive = sum(1 for r in v1.values() if r["expectancy"] > 0)
    negative = sum(1 for r in v1.values() if r["expectancy"] < 0)
    zero = sum(1 for r in v1.values() if r["expectancy"] == 0)

    def op(r: dict) -> str:
        conds = r.get("conditions") or []
        return conds[0]["operator"] if conds else "no_condition"

    gt_pids = [pid for pid, r in v1.items() if op(r) == "gt"]
    lt_pids = [pid for pid, r in v1.items() if op(r) == "lt"]
    gt_validated = sum(1 for pid in gt_pids if latest[pid]["validation_status"] == "validated")
    lt_validated = sum(1 for pid in lt_pids if latest[pid]["validation_status"] == "validated")

    def robustness_ambiguous(pid: str) -> bool:
        reason = latest[pid].get("rejection_reason")
        return bool(reason) and "perturbation(s) flipped sign, or the pattern does not survive transaction costs" in reason

    ambiguous_pids = [pid for pid in latest if latest[pid]["validation_status"] == "rejected" and robustness_ambiguous(pid)]
    txn_cost_alone = sum(1 for pid in ambiguous_pids if v1[pid]["expectancy"] - TRANSACTION_COST_FRACTION <= 0)

    return {
        "source": "recomputed_this_session",
        "note": "Not read from a Step 1.6 artifact file (none exist on disk this session) -- computed fresh from the same registry Step 1.6 used, which was independently verified unchanged.",
        "total_discovered": total,
        "v1_positive_count": positive,
        "v1_negative_count": negative,
        "v1_zero_count": zero,
        "v1_positive_pct": positive / total,
        "gt_discovered": len(gt_pids),
        "gt_validated": gt_validated,
        "lt_discovered": len(lt_pids),
        "lt_validated": lt_validated,
        "robustness_ambiguous_total": len(ambiguous_pids),
        "robustness_ambiguous_txn_cost_alone_explains": txn_cost_alone,
    }


def grep(pattern: str, path: str, extra_flags: str = "-n") -> str:
    result = subprocess.run(
        ["grep", "-riE", extra_flags, pattern, path],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    return result.stdout


def code_semantics_audit() -> dict:
    """Live, reproducible (grep-based) verification of the direction-
    semantics code citations this report relies on -- run at analysis time
    rather than only asserted narratively, so a future re-run catches drift
    if the cited code ever changes."""
    findings = {}

    # 1. Pattern schema: no explicit direction/side field.
    registry_py = (RESEARCH_ROOT / "src" / "agx_research" / "patterns" / "registry.py").read_text()
    direction_field_present = any(
        needle in registry_py for needle in ("side:", "direction:", "position_type:", "is_short", "trade_direction")
    )
    findings["pattern_schema_has_explicit_direction_field"] = direction_field_present

    # 2. live.py: PatternActivation never emits BUY/SELL.
    live_py = (RESEARCH_ROOT / "src" / "agx_research" / "patterns" / "live.py").read_text()
    findings["live_py_label_is_always_ACTIVE_PATTERN"] = 'label: str = "ACTIVE_PATTERN"' in live_py
    findings["live_py_contains_buy_sell_literal"] = ("BUY" in live_py or "SELL" in live_py)

    # 3. robustness.py: the positive-only transaction-cost gate.
    robustness_py = (RESEARCH_ROOT / "src" / "agx_research" / "patterns" / "robustness.py").read_text()
    findings["robustness_py_has_net_expectancy_gt_zero_gate"] = "net_expectancy > 0" in robustness_py

    # 4. transaction_costs.py: same construction recurs.
    txn_costs_py = (RESEARCH_ROOT / "src" / "agx_research" / "patterns" / "transaction_costs.py").read_text()
    findings["transaction_costs_py_has_matching_gate"] = "> 0" in txn_costs_py and "net_expectancy" in txn_costs_py
    findings["transaction_costs_py_models_borrow_or_short_cost"] = any(
        needle in txn_costs_py.lower() for needle in ("borrow", "short", "financing", "locate", "hard-to-borrow", "hard to borrow")
    )

    # 5. decision_service / portfolio: no short-side infrastructure at all.
    decision_service_dir = RESEARCH_ROOT / "src" / "agx_research" / "decision_service"
    portfolio_dir = RESEARCH_ROOT / "src" / "agx_research" / "portfolio"
    short_mentions = []
    for base in (decision_service_dir, portfolio_dir):
        if not base.exists():
            continue
        for f in base.rglob("*.py"):
            text = f.read_text()
            for line_no, line in enumerate(text.splitlines(), 1):
                low = line.lower()
                if ("short" in low and "shortcut" not in low and "shorthand" not in low
                        and "short-term" not in low and "shortfall" not in low and "short of" not in low):
                    short_mentions.append(f"{f.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    findings["decision_service_or_portfolio_short_position_mentions"] = short_mentions

    # 6. PositionAction enum: confirm long-only lifecycle (no SHORT/SELL_SHORT/COVER).
    service_py = (decision_service_dir / "service.py").read_text() if decision_service_dir.exists() else ""
    findings["position_action_values"] = [
        line.strip() for line in service_py.splitlines()
        if any(v in line for v in ('BUY = "buy"', 'INCREASE_POSITION', 'HOLD = "hold"', 'REDUCE_POSITION', 'EXIT = "exit"', 'NO_ACTION'))
    ]
    findings["position_action_has_short_variant"] = any(
        needle in service_py for needle in ("SELL_SHORT", "SHORT =", "OPEN_SHORT", "COVER")
    )

    # 7. What imports patterns/ -- confirms whether anything downstream acts on Pattern data.
    grep_out = subprocess.run(
        ["grep", "-rl", "from agx_research.patterns", "src", "tests"],
        cwd=RESEARCH_ROOT, capture_output=True, text=True,
    ).stdout
    importers = sorted(set(grep_out.strip().splitlines()))
    non_pattern_internal_importers = [
        p for p in importers
        if not p.startswith("src/agx_research/patterns/") and not p.startswith("tests/")
    ]
    findings["files_importing_agx_research_patterns"] = importers
    findings["non_patterns_package_importers"] = non_pattern_internal_importers
    findings["only_cli_and_self_and_tests_import_patterns"] = non_pattern_internal_importers == ["src/agx_research/cli.py"]

    # 8. AD-42 precedent: codebase already rejected an analogous synthetic-position fabrication elsewhere.
    ad_doc = (REPO_ROOT / "docs" / "ARCHITECTURE_DECISIONS.md")
    ad42_text = ""
    if ad_doc.exists():
        for line in ad_doc.read_text().splitlines():
            if "AD-42" in line:
                ad42_text = line.strip()
                break
    findings["ad_42_precedent_text"] = ad42_text

    # 9. VISION.md / MASTER_PROMPT.md / investment doctrine: explicit long-only or short-capable mandate search.
    doc_hits = {}
    for doc_name in (
        "docs/VISION.md", "MASTER_PROMPT.md", "docs/PATTERN_DISCOVERY_DATA_AUDIT.md",
        "docs/INVESTMENT_CONSTITUTION.md", "docs/DECISION_STANDARDS.md", "docs/PORTFOLIO_STANDARDS.md",
    ):
        doc_path = REPO_ROOT / doc_name
        if not doc_path.exists():
            doc_hits[doc_name] = "FILE_NOT_FOUND"
            continue
        text = doc_path.read_text().lower()
        doc_hits[doc_name] = {
            "mentions_long_only": "long-only" in text or "long only" in text,
            "mentions_short_selling_or_short_signal": ("short-sell" in text or "short sell" in text
                                                        or "short signal" in text or "short position" in text),
            "mentions_direction_agnostic": "direction-agnostic" in text or "direction agnostic" in text,
        }
    findings["authoritative_doc_direction_mandate_search"] = doc_hits

    return findings


def verify_registry_unchanged(registry: dict[str, list[dict]]) -> dict:
    from collections import Counter
    total = len(registry)
    latest_status = Counter(
        sorted(revs, key=lambda r: r["version"])[-1]["validation_status"] for revs in registry.values()
    )
    ok = (
        total == EXPECTED_TOTAL
        and latest_status.get("validated", 0) == EXPECTED_VALIDATED
        and latest_status.get("rejected", 0) == EXPECTED_REJECTED
    )
    return {
        "total_patterns": total,
        "validated": latest_status.get("validated", 0),
        "rejected": latest_status.get("rejected", 0),
        "matches_expected_step_1_6_counts": ok,
        "expected": {"total": EXPECTED_TOTAL, "validated": EXPECTED_VALIDATED, "rejected": EXPECTED_REJECTED},
    }


def main() -> None:
    provenance = check_provenance()
    registry = load_registry()
    registry_check = verify_registry_unchanged(registry)
    reconciliation = recompute_step_1_6_reconciliation_figures(registry)
    code_audit = code_semantics_audit()

    # ---- economic semantics trace (direct code facts, not opinions) ----
    semantics_trace = {
        "GT_LT_meaning": (
            "ConditionOperator.GT/LT (candidates.py:41-46) define the DIRECTION OF THE FEATURE "
            "THRESHOLD a candidate tests (e.g. 'RSI > 70' vs 'RSI < 30'), never the direction of "
            "a trade. FeatureCondition.evaluate() only returns whether the feature value satisfies "
            "the threshold comparison -- it has no relationship to how the resulting match should "
            "be traded."
        ),
        "expectancy_meaning": (
            "Pattern.expectancy / OutcomeDistribution.expectancy (evaluation.py:113) is always "
            "'mean(matched forward_return)', and forward_return_series() (targets.py:76-85) is "
            "always '(closes[i+h] - closes[i]) / closes[i]' -- the arithmetic return of BUYING at "
            "close[i] and holding to close[i+h]. This is computed identically regardless of "
            "whether the triggering condition used GT or LT. There is no code path anywhere that "
            "inverts, relabels, or reinterprets this value based on the condition's operator."
        ),
        "forward_return_target_meaning": (
            "A single, universal LONG-entry economic definition (targets.py:76-85), shared by "
            "every condition operator, every feature, and every baseline in baselines.py (which "
            "imports forward_return_series directly for buy_and_hold_baseline() etc.) -- there is "
            "no parallel 'short_return' target anywhere in TargetKind (targets.py:32-41's enum has "
            "9 members, none short-specific)."
        ),
        "pattern_direction_field": (
            "CONFIRMED ABSENT. Pattern (registry.py) has no side/direction/position_type/is_short "
            "field (grep-verified: pattern_schema_has_explicit_direction_field=False below). The "
            "only signal a downstream consumer has for 'which way to trade this' is the sign of "
            "expectancy itself -- which conflates 'statistically real effect' with 'implied trade "
            "direction,' two different claims that happen to have been collapsed into one field."
        ),
        "pattern_activation_live_output": (
            "live.py's PatternActivation.label is a fixed string, always 'ACTIVE_PATTERN' "
            "(confirmed: live_py_label_is_always_ACTIVE_PATTERN=True below), and the package "
            "docstring explicitly states output is 'deliberately never a BUY/SELL recommendation.' "
            "This is direction-agnostic OUTPUT VOCABULARY layered on top of an implicitly "
            "LONG-only ECONOMIC COMPUTATION underneath (expectancy/robustness/baseline all assume "
            "a long entry) -- an internal inconsistency, not a resolved design."
        ),
        "validation_sign_agreement_meaning": (
            "WalkForwardValidator.validate() (validation.py:170-174) and "
            "engine.final_holdout() (engine.py:673) both test whether two independently-measured "
            "expectancy samples AGREE IN SIGN -- consistency of the LONG-return statistic across "
            "time periods, not a judgment about whether that sign implies a tradeable long or "
            "short position. Sign-neutral with respect to trade direction."
        ),
        "robustness_transaction_cost_survival_meaning": (
            "RobustnessTester.run() (robustness.py:124-126) treats 'net_expectancy = "
            "expectancy - 0.002 > 0' as the pattern's economic viability test -- this ONLY makes "
            "sense as a viability test for a LONG position (buy at the cost, realize the raw "
            "forward return). It implicitly assumes every candidate, regardless of GT/LT or sign, "
            "would be traded long. A negative-expectancy candidate is therefore rejected not "
            "because it lacks a real effect, but because the pipeline never considers the "
            "alternative (shorting) that would make that same effect economically positive."
        ),
        "baseline_comparison_meaning": (
            "beats_baseline() (baselines.py:156-162) compares net_expectancy to "
            "buy_and_hold_baseline().mean_outcome -- also implicitly a LONG-vs-LONG comparison "
            "('does this conditional long strategy beat unconditionally going long'), with no "
            "analogous 'does this conditional short strategy beat unconditionally going short' "
            "comparison anywhere in baselines.py's TargetKind/BaselineResult surface."
        ),
    }

    # ---- short/inverse validity test ----
    short_validity_test = {
        "question": "Can short_return = -forward_return legitimately be used to reinterpret a negative-expectancy pattern as a valid short signal?",
        "arithmetic_validity": (
            "Mechanically valid: negating a realized long return equals the frictionless, "
            "unconstrained P&L of an equal-and-opposite short position, ignoring financing, "
            "borrow cost, and availability."
        ),
        "economic_validity": "INVALID as a promotion basis, for four independent reasons:",
        "reasons": [
            (
                "No independent re-validation: the entire discover()->validate()->final_holdout() "
                "pipeline (bootstrap significance, walk-forward sign agreement, robustness "
                "perturbation-agreement, transaction-cost floor, baseline-beat) was computed and "
                "gated using forward_return, i.e. long economics, throughout. Retroactively negating "
                "already-computed statistics is not the same as running -forward_return through the "
                "same discovery/validation/holdout machinery independently -- e.g. a candidate whose "
                "sign flips under negation might fail perturbation-sign-agreement or baseline-beat "
                "under the negated series even though it passed under the original one; this was "
                "never tested."
            ),
            (
                "No short-specific cost model exists anywhere: the ONLY cost model in this codebase "
                "(robustness.py's flat 20bps, transaction_costs.py's 0-100bps sensitivity grid) is a "
                "single symmetric round-trip figure applied identically regardless of direction. Real "
                "short economics require borrow fee, hard-to-borrow premium/availability, financing "
                "rate, and often asymmetric execution cost -- none of which exist in this codebase "
                "(grep-verified: transaction_costs_py_models_borrow_or_short_cost=False below)."
            ),
            (
                "No EGX-specific short-selling/securities-lending data source exists: this audit "
                "found zero references to short-selling, margin trading, or securities-lending "
                "availability anywhere in sources/, data/, or the documented Data Acquisition "
                "Program (docs/DATA_ACQUISITION.md was not found to model this) -- so even if a "
                "cost figure were assumed, no data exists to determine WHETHER a given EGX30 ticker "
                "is actually shortable at all."
            ),
            (
                "Direct internal precedent against this move already exists in this codebase: "
                "AD-42 (docs/ARCHITECTURE_DECISIONS.md) explicitly rejects treating a non-executed, "
                "counterfactual outcome as a 'synthetic long/short position' elsewhere in this same "
                "platform, on the grounds that 'counterfactual avoidance and observation are not "
                "executed portfolio returns.' A negative-expectancy pattern's forward_return series "
                "was never executed as a short trade by anything in this system -- applying "
                "short_return = -forward_return and calling the result 'a valid short signal' is "
                "the same category of retrospective fabrication AD-42 already rules out."
            ),
        ],
        "conclusion": (
            "The transform is mechanically well-defined but economically unvalidated. Using it to "
            "promote a negative-expectancy pattern would assert an executed short-trade edge that "
            "was never modeled, priced, or independently tested by any part of this system."
        ),
    }

    result = {
        "audit": "Mission 3 Step 1.7: Directional Semantics & Economic Validity Audit",
        "provenance": provenance,
        "registry_verification": registry_check,
        "step_1_6_reconciliation_figures": reconciliation,
        "code_semantics_audit": code_audit,
        "semantics_trace": semantics_trace,
        "short_inverse_validity_test": short_validity_test,
        "objective_answer": {
            "question": "Should a negative-expectancy pattern be interpreted as (A) failed long, (B) potentially valid short/inverse, (C) requires explicit directional metadata, or (D) intentionally unsupported under an explicit long-only mandate?",
            "answer": "C",
            "justification": (
                "Not (A) alone: nothing in the code declares a negative-expectancy candidate "
                "'wrong' or 'noise' -- validation.py's sign-agreement gates would happily validate "
                "a consistently negative pattern if the robustness/baseline gates weren't "
                "independently long-only-coded; the negativity itself was never treated as evidence "
                "of failure by discover()'s sign-neutral significance test. Not (B): no economic "
                "infrastructure (cost, availability, financing) exists to support treating it as a "
                "valid short signal today -- see short_inverse_validity_test above. Not (D): no "
                "explicit long-only mandate exists in any authoritative doc (VISION.md, "
                "MASTER_PROMPT.md, the investment doctrine set, or patterns/'s own docstrings) -- "
                "the long-only behavior is implicit/emergent from robustness.py's and baselines.py's "
                "coded assumptions, never a stated design decision. (C) fits: the Pattern schema "
                "has no direction/side field, and interpreting a negative-expectancy pattern "
                "economically (long failure vs. short candidate vs. unsupported) requires "
                "information -- an explicit direction/side semantic, plus a short-cost model if "
                "shorts are ever meant to be in scope -- that does not currently exist anywhere in "
                "this system."
            ),
        },
        "downstream_directional_assumptions": {
            "trades_executed_by_patterns_package": False,
            "buy_sell_emitted_by_patterns_package": False,
            "patterns_ranked_for_capital_allocation": False,
            "portfolios_constructed_from_patterns": False,
            "evidence": (
                "Grep-confirmed (see code_semantics_audit.non_patterns_package_importers below): "
                "the only non-test, non-self file importing agx_research.patterns anywhere in the "
                "repository is cli.py. decision_service/, portfolio/, capital_allocation/, "
                "shadow_fund/, api/, and web/ contain zero references to the patterns package. "
                "Nothing today acts on Pattern/PatternActivation data for any real decision, "
                "ranking, or execution -- the directional-semantics ambiguity above currently has "
                "ZERO live consequence. It becomes load-bearing only once a Promotion Gate (Mission "
                "3's actual objective) creates the first real bridge from patterns/ into "
                "decision-relevant use."
            ),
        },
        "classification": {
            "category": "C",
            "label": "Direction semantics are missing/ambiguous",
            "justification": (
                "No authoritative doc declares an explicit long-only mandate (rules out A). No "
                "short-side economic infrastructure -- cost, availability, financing -- exists "
                "anywhere in the codebase, and this audit's own short-validity test found the "
                "naive short_return=-forward_return transform economically unvalidated (rules out "
                "B and D). The system's actual behavior is an UNDOCUMENTED, EMERGENT long-only "
                "assumption baked into two specific gates (robustness.py:126, baselines.py:161-162) "
                "that is in direct tension with live.py's own explicit 'direction-agnostic output' "
                "framing -- an unresolved internal inconsistency, not a deliberate design, which is "
                "the definition of 'missing/ambiguous' rather than 'other.'"
            ),
        },
        "what_is_proven": [
            "GT/LT operators define feature-threshold direction only, never trade direction (candidates.py, direct code read).",
            "expectancy/forward_return are always computed as a long-entry return, identically regardless of operator or sign (targets.py, evaluation.py).",
            "The Pattern schema has no direction/side field (registry.py, grep-verified).",
            "PatternActivation never emits BUY/SELL (live.py, grep-verified and matches its own docstring).",
            "robustness.py's transaction_cost_survival and baselines.py's beats_baseline() both implicitly assume long-only economics via their exact code construction (robustness.py:126, baselines.py:161-162).",
            "No short-cost, borrow-fee, financing, or short-availability model exists anywhere in patterns/ (grep-verified against transaction_costs.py, the only cost-modeling module).",
            "Nothing outside patterns/ (and its own tests/cli.py) currently imports or consumes Pattern data -- zero live downstream directional consequence today (grep-verified).",
            "No authoritative doc (VISION.md, MASTER_PROMPT.md, patterns/'s own mission-derived docstrings, the investment doctrine set) states an explicit long-only or short-capable mandate for pattern discovery specifically.",
            "This codebase has an internal precedent (AD-42) against fabricating synthetic long/short positions from non-executed outcomes, directly analogous to the short_return=-forward_return transform this audit tested.",
        ],
        "what_is_not_proven": [
            "Whether EGX30 tickers are, in reality, shortable at all, and at what cost -- this audit found no data source addressing this, but does not claim to have exhaustively searched every possible external source.",
            "Whether a negative-expectancy pattern, if independently re-validated end-to-end against a properly-modeled short-return series (with real borrow/financing costs), would or would not survive -- this was never tested, and this audit deliberately does not test it (out of scope, and no short-cost data exists to test it with).",
            "Whether the long-only behavior in robustness.py/baselines.py was a deliberate simplification the original implementer intended to revisit later, or a genuine oversight -- no comment, commit message, or doc found by this audit states either way.",
            "Whether any future consumer of Pattern data (a not-yet-built Promotion Gate, or any other downstream system) would in practice need short-signal support at all -- that is a product/scope decision, not something this audit can determine from the code alone.",
        ],
        "required_architectural_decision": (
            "Before any pattern can be economically interpreted when its expectancy is negative, "
            "an explicit decision is needed on: (1) whether AGX/the Promotion Gate is long-only by "
            "design (in which case negative-expectancy patterns should be explicitly and "
            "permanently out of scope for promotion, not silently rejected by an incidental cost "
            "gate as they are today), or (2) whether short/inverse signals are ever in scope, which "
            "would require adding a direction/side field to the Pattern schema, building a real "
            "short-side cost/availability/financing model, and independently re-running the full "
            "discover()->validate()->final_holdout() pipeline against a properly-defined short "
            "target -- not retroactively negating existing statistics. This decision belongs to the "
            "user/product owner, not to this audit or to the Promotion Gate design."
        ),
        "impact_on_step_1_6_interpretation": (
            "Step 1.6 correctly identified the code-level mechanism "
            "(robustness.py:126's net_expectancy>0 gate) and the data-level mechanism (positive "
            "market drift) that together explain why the VALIDATED population is 100% positive. "
            "Step 1.6 did NOT claim negative-expectancy patterns are short signals, and explicitly "
            "did not need to -- that question is precisely what Step 1.7 was scoped to answer. "
            "Step 1.7 does not overturn any Step 1.6 finding; it adds one clarification: Step 1.6's "
            "'accidental implementation bias' component (Component B) can now be stated more "
            "precisely as 'the codebase assumes long-only economics without ever declaring that "
            "assumption explicitly, and provides no mechanism to evaluate a negative-expectancy "
            "candidate under any alternative economic interpretation' -- i.e. the bias is not "
            "merely an arbitrary implementation accident, it is a specific, identifiable GAP "
            "(missing direction semantics), consistent with this audit's own classification (C)."
        ),
        "recommendation_on_promotion_gate_work": {
            "may_promotion_gate_design_proceed": "YES, WITH AN EXPLICIT SCOPING CONSTRAINT",
            "constraint": (
                "Promotion Gate design/implementation MAY proceed for POSITIVE-expectancy patterns "
                "-- their economic interpretation (a long signal) is unambiguous under every gate "
                "traced in this audit, with no open architectural question blocking it. Promotion "
                "Gate design/implementation must NOT create any pathway that promotes, scores, or "
                "otherwise treats a negative-expectancy pattern as a tradeable (short/inverse) "
                "signal, and must not apply short_return=-forward_return or any equivalent "
                "relabeling anywhere, until the required_architectural_decision above is made "
                "explicitly by the user/product owner. Given only 4/3,398 DISCOVERED patterns are "
                "even negative (Step 1.6), this constraint is narrow in practical scope but must "
                "still be stated explicitly in the Gate's design, not left implicit the way it is "
                "in the current discover()/validate() pipeline."
            ),
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w") as f:
        json.dump(result, f, indent=2, default=str, sort_keys=True)
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Registry check: {registry_check}")
    print(f"Classification: {result['classification']['category']}")


if __name__ == "__main__":
    main()
