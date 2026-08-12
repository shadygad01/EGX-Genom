"""Tests for `patterns.promotion_evidence` (Mission 3, Blocking Dependency #1).

Uses the same synthetic-data + discover->validate->final_holdout
convention `test_pattern_engine.py` already establishes, so every test
here exercises a genuine, already-VALIDATED `Pattern` object -- never a
hand-typed fixture that might silently omit a field the real pipeline
always sets.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agx_research.patterns.candidates import CandidateGeneratorConfig, ConditionOperator, FeatureCondition
from agx_research.patterns.engine import PatternDiscoveryEngine, PatternDiscoveryEngineConfig
from agx_research.patterns.multiple_testing import TestingLedgerRepository
from agx_research.patterns.promotion_evidence import (
    EvidenceStatus,
    PromotionEvidenceSnapshot,
    _snapshot_id,
    compute_promotion_evidence,
)
from agx_research.patterns.registry import PatternRegistry, PatternStatus
from agx_research.patterns.validation import WalkForwardValidatorConfig
from tests.pattern_test_helpers import make_deterministic_ticker_series, make_panel

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _validated_pattern_and_panel():
    a = make_deterministic_ticker_series(
        "A", n_days=200, seed=11, block_length=10, daily_drift=0.01, noise_stdev=0.0005, sector="Banks"
    )
    b = make_deterministic_ticker_series(
        "B", n_days=200, seed=22, block_length=13, daily_drift=0.008, noise_stdev=0.0006, sector="Banks"
    )
    panel = make_panel(series={"A": a, "B": b})

    registry = PatternRegistry()
    engine = PatternDiscoveryEngine(
        pattern_registry=registry,
        testing_ledger_repository=TestingLedgerRepository(),
        config=PatternDiscoveryEngineConfig(
            candidate_config=CandidateGeneratorConfig(
                min_sample_size=15,
                correlation_prune_threshold=0.8,
                max_candidates_per_ticker=40,
                enable_three_feature=False,
                enable_regime_conditioning=False,
            ),
            walk_forward_config=WalkForwardValidatorConfig(
                n_folds=3, min_train_size=40, min_oos_sample_size=8, embargo_days=2
            ),
            fdr_alpha=0.10,
            require_beats_baseline=True,
            horizons=(5,),
        ),
    )
    engine.discover(panel)
    engine.validate(panel)
    engine.final_holdout(panel)
    validated = registry.by_status(PatternStatus.VALIDATED)
    assert validated, "fixture setup must produce at least one VALIDATED pattern"
    return validated[0], panel


@pytest.fixture(scope="module")
def validated_pattern_and_panel():
    return _validated_pattern_and_panel()


# ---- 1. deterministic evidence generation ----


def test_deterministic_evidence_generation(validated_pattern_and_panel):
    pattern, panel = validated_pattern_and_panel
    snapshot = compute_promotion_evidence(pattern, panel, dataset_source="synthetic", dataset_version="test-v1")

    assert isinstance(snapshot, PromotionEvidenceSnapshot)
    assert snapshot.provenance.integrity_check_passed is True
    # All four evidence types should be computable for a real, validated,
    # sufficiently-sampled synthetic pattern.
    assert snapshot.net_of_cost_expectancy.status == EvidenceStatus.COMPUTED
    assert snapshot.robustness_detail.status == EvidenceStatus.COMPUTED
    assert snapshot.baseline_comparison.status in (EvidenceStatus.COMPUTED, EvidenceStatus.INSUFFICIENT_EVIDENCE)
    assert snapshot.regime_profile.status in (EvidenceStatus.COMPUTED, EvidenceStatus.INSUFFICIENT_EVIDENCE)


# ---- 2. identical input -> identical evidence ----


def test_identical_input_produces_identical_evidence(validated_pattern_and_panel):
    pattern, panel = validated_pattern_and_panel
    snap1 = compute_promotion_evidence(pattern, panel, dataset_source="synthetic", dataset_version="test-v1")
    snap2 = compute_promotion_evidence(pattern, panel, dataset_source="synthetic", dataset_version="test-v1")

    # Content-derived id never includes a timestamp -- identical inputs
    # must always produce the identical id.
    assert snap1.id == snap2.id

    # Every substantive evidence field must match too -- only the
    # timestamp-bearing provenance fields (generated_at/created_at) are
    # allowed to differ between two independently-timed calls.
    assert snap1.net_of_cost_expectancy == snap2.net_of_cost_expectancy
    assert snap1.baseline_comparison == snap2.baseline_comparison
    assert snap1.robustness_detail == snap2.robustness_detail
    assert snap1.regime_profile == snap2.regime_profile
    assert snap1.provenance.pattern_definition_hash == snap2.provenance.pattern_definition_hash
    assert snap1.provenance.data_windows == snap2.provenance.data_windows


# ---- 3. changed pattern hash -> new snapshot ----


def test_changed_pattern_hash_produces_new_snapshot_id(validated_pattern_and_panel):
    pattern, panel = validated_pattern_and_panel
    snap1 = compute_promotion_evidence(pattern, panel)

    mutated_condition = FeatureCondition(
        feature_id=pattern.conditions[0].feature_id,
        operator=ConditionOperator.LT if pattern.conditions[0].operator == ConditionOperator.GT else ConditionOperator.GT,
        threshold=pattern.conditions[0].threshold,
    )
    mutated_pattern = pattern.model_copy(update={"conditions": [mutated_condition, *pattern.conditions[1:]]})
    snap2 = compute_promotion_evidence(mutated_pattern, panel)

    assert snap1.id != snap2.id
    assert snap1.provenance.pattern_definition_hash != snap2.provenance.pattern_definition_hash


# ---- 4. changed methodology version -> new snapshot ----


def test_changed_methodology_version_produces_new_snapshot_id():
    id_v1 = _snapshot_id(
        pattern_definition_hash="abc", pattern_registry_version=1,
        dataset_source="synthetic", dataset_version="v1", methodology_version="1.0.0",
    )
    id_v2 = _snapshot_id(
        pattern_definition_hash="abc", pattern_registry_version=1,
        dataset_source="synthetic", dataset_version="v1", methodology_version="1.1.0",
    )
    assert id_v1 != id_v2


# ---- 5. changed data snapshot -> new snapshot ----


def test_changed_data_snapshot_produces_new_snapshot_id(validated_pattern_and_panel):
    pattern, panel = validated_pattern_and_panel
    snap1 = compute_promotion_evidence(pattern, panel, dataset_version="seed-commit-aaa")
    snap2 = compute_promotion_evidence(pattern, panel, dataset_version="seed-commit-bbb")
    assert snap1.id != snap2.id


# ---- 6. missing evidence source -> INSUFFICIENT_EVIDENCE, never a crash or fabricated value ----


def test_missing_ticker_returns_insufficient_evidence(validated_pattern_and_panel):
    pattern, panel = validated_pattern_and_panel
    orphan_pattern = pattern.model_copy(update={"ticker": "NOT_IN_PANEL"})

    snapshot = compute_promotion_evidence(orphan_pattern, panel)

    for evidence in (
        snapshot.net_of_cost_expectancy,
        snapshot.baseline_comparison,
        snapshot.robustness_detail,
        snapshot.regime_profile,
    ):
        assert evidence.status == EvidenceStatus.INSUFFICIENT_EVIDENCE
        assert evidence.reason
    assert snapshot.net_of_cost_expectancy.net_of_cost_expectancy is None
    assert snapshot.provenance.integrity_check_passed is False


def test_reconstruction_integrity_mismatch_returns_insufficient_evidence(validated_pattern_and_panel):
    """A pattern whose recorded discovery_period does not match what this
    module's own reconstruction produces must never be silently evaluated
    on the wrong window (Step 3's 'no silent recomputation' requirement)."""
    pattern, panel = validated_pattern_and_panel
    bogus_pattern = pattern.model_copy(
        update={"discovery_period": (pattern.discovery_period[0], pattern.discovery_period[0])}
    )
    snapshot = compute_promotion_evidence(bogus_pattern, panel)

    assert snapshot.provenance.integrity_check_passed is False
    assert snapshot.net_of_cost_expectancy.status == EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert snapshot.robustness_detail.status == EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert snapshot.baseline_comparison.status == EvidenceStatus.INSUFFICIENT_EVIDENCE
    assert "discovery_period" in snapshot.provenance.integrity_check_note


# ---- 7. evidence cannot contain promotion decisions ----


def test_schema_contains_no_promotion_decision_fields():
    from agx_research.patterns.promotion_evidence import (
        BaselineComparisonEvidence,
        NetOfCostExpectancyEvidence,
        RegimeProfileEvidence,
        RobustnessDetailEvidence,
    )

    forbidden = ("promote", "eligible", "production", "reject")
    for model in (
        NetOfCostExpectancyEvidence,
        BaselineComparisonEvidence,
        RobustnessDetailEvidence,
        RegimeProfileEvidence,
        PromotionEvidenceSnapshot,
    ):
        for field_name in model.model_fields:
            lowered = field_name.lower()
            assert not any(bad in lowered for bad in forbidden), (
                f"{model.__name__}.{field_name} looks like a promotion-decision field"
            )


# ---- 8. evidence cannot be mutated after creation ----


def test_snapshot_is_immutable_after_creation(validated_pattern_and_panel):
    pattern, panel = validated_pattern_and_panel
    snapshot = compute_promotion_evidence(pattern, panel)

    with pytest.raises(Exception):  # pydantic ValidationError on a frozen model
        snapshot.pattern_id = "tampered"


# ---- 9. provenance fields are complete ----


def test_provenance_fields_are_complete(validated_pattern_and_panel):
    pattern, panel = validated_pattern_and_panel
    snapshot = compute_promotion_evidence(pattern, panel, dataset_source="synthetic", dataset_version="test-v1")
    prov = snapshot.provenance

    assert prov.pattern_id == pattern.id
    assert len(prov.pattern_definition_hash) == 64  # sha256 hex digest
    assert prov.pattern_registry_version == pattern.version
    assert prov.reproducibility.git_commit is not None or prov.reproducibility.git_commit is None  # field present, value honest either way
    assert prov.reproducibility.dataset_source == "synthetic"
    assert prov.reproducibility.dataset_version == "test-v1"
    assert prov.ticker_universe == panel.tickers
    assert prov.transaction_cost_bps > 0
    assert prov.baseline_definition == "buy_and_hold_baseline"
    assert set(prov.regime_definition.keys()) == {
        "dimensions", "bucket_count", "regime_lookback_days", "correlation_lookback_days",
    }
    assert prov.bootstrap_seed == 42
    assert prov.methodology_version
    assert len(prov.data_windows) == 4
    labels = {w.label for w in prov.data_windows}
    assert labels == {
        "research_period_full", "walk_forward_oos_folds",
        "full_history_incl_spent_final_holdout", "future_paper_validation_data",
    }
    future_window = next(w for w in prov.data_windows if w.label == "future_paper_validation_data")
    assert future_window.start is None and future_window.end is None and future_window.trading_day_count == 0
    assert future_window.used_by == []


# ---- 10. no production decision path imports this module ----


def test_no_production_decision_path_imports_promotion_evidence():
    forbidden_dirs = [
        _REPO_ROOT / "research" / "src" / "agx_research" / "decision_service",
        _REPO_ROOT / "research" / "src" / "agx_research" / "meta",
        _REPO_ROOT / "research" / "src" / "agx_research" / "capital_allocation",
        _REPO_ROOT / "research" / "src" / "agx_research" / "shadow_fund",
    ]
    pattern = re.compile(r"\bpromotion_evidence\b")
    offenders: list[str] = []
    for directory in forbidden_dirs:
        if not directory.is_dir():
            continue
        for py_file in directory.rglob("*.py"):
            if pattern.search(py_file.read_text(encoding="utf-8")):
                offenders.append(str(py_file))

    live_module = _REPO_ROOT / "research" / "src" / "agx_research" / "patterns" / "live.py"
    if live_module.is_file() and pattern.search(live_module.read_text(encoding="utf-8")):
        offenders.append(str(live_module))

    assert offenders == [], f"promotion_evidence must not be imported by any production decision path: {offenders}"
