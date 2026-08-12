"""Promotion Evidence Infrastructure (Mission 3, Blocking Dependency #1).

Resolves the persistence gap `docs/PATTERN_PROMOTION_GATE_DESIGN.md`'s v2.2
specification (§5, "Persisted Evidence") names as `BLOCKING DEPENDENCY` for
four evidence types a future Promotion Gate needs: net-of-cost expectancy,
baseline comparison, robustness detail, and regime profile. None of these
is persisted at the granularity the Gate needs today -- only the aggregate
`Pattern.robustness_passed` boolean survives past `validate()`, and
`PatternFailureProfile`/`TransactionCostSensitivity` are computed only on
demand via `cli.py`, never for the full registry.

**This module is evidence infrastructure, not the Promotion Gate.** It
computes and persists OBSERVED/COMPUTED evidence about an already-VALIDATED
pattern. It never creates a `PromotionCase`, never introduces a `PROMOTED`
state, never makes a promotion/rejection decision, and is imported by
nothing in the production decision path (`decision_service/`,
`meta.decision_engine`, `capital_allocation/`, `shadow_fund/`,
`patterns.live.LiveActivationEngine`). See `docs/
PROMOTION_EVIDENCE_INFRASTRUCTURE_DESIGN.md` for the full design note this
implements.

Every one of the four evidence types is computed by calling the existing,
unmodified functions in `robustness.py`/`baselines.py`/`regimes.py` --
this module only reconstructs their inputs (a `PatternCandidate`, the
research-period `anchor_dates`, a `feature_lookup`, the `target`), wraps
the outputs in an immutable, versioned, fully-provenanced snapshot, and
refuses (returning `INSUFFICIENT_EVIDENCE`, never a fabricated value) when
required source data is missing or the reconstruction fails an integrity
check against the pattern's own already-persisted `discovery_period`.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from agx_research.patterns.baselines import beats_baseline, buy_and_hold_baseline
from agx_research.patterns.candidates import FeatureCondition, PatternCandidate
from agx_research.patterns.engine import (
    PatternDiscoveryEngineConfig,
    _build_context,
    _lead_lag_predictor_features,
    _nearby_feature_ids,
    _sector_leaders,
    _split_research_and_holdout,
)
from agx_research.patterns.panel import ResearchPanel
from agx_research.patterns.regimes import (
    CORRELATION_LOOKBACK_DAYS,
    DEFAULT_BUCKET_COUNT,
    DEFAULT_REGIME_LOOKBACK_DAYS,
    PatternFailureProfile,
    RegimeDimension,
    analyze_pattern_failure_conditions,
)
from agx_research.patterns.registry import Pattern
from agx_research.patterns.reproducibility import ReproducibilityManifest, build_reproducibility_manifest
from agx_research.patterns.robustness import DEFAULT_TRANSACTION_COST_BPS, RobustnessResult, RobustnessTester
from agx_research.patterns.validation import WalkForwardValidator
from agx_research.storage.repository import JsonFileRepository

# Bump whenever this module's evidence-computation LOGIC changes in a way
# that would produce different numbers for the same input -- same "explicit
# version, not implicit trust" posture as `reproducibility.
# FEATURE_FACTORY_VERSION`. A bump changes every future snapshot's content
# hash (see `_snapshot_id`), so it is never confused with an older
# methodology's output.
PROMOTION_EVIDENCE_METHODOLOGY_VERSION = "1.0.0"

# `evaluation.py`'s own bootstrap default (`_bootstrap(..., seed=42)`),
# never overridden anywhere this module calls into. Stated explicitly here
# so every snapshot's provenance records the seed that was actually in
# effect, rather than leaving it implicit.
BOOTSTRAP_SEED = 42

BASELINE_DEFINITION = "buy_and_hold_baseline"

_ENGINE_DEFAULTS = PatternDiscoveryEngineConfig()


class EvidenceStatus(str, Enum):
    COMPUTED = "computed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class DataWindowProvenance(BaseModel):
    """One labeled slice of history some evidence field was computed from.
    Always four entries, one per label below, even when a label's window is
    empty -- an empty `future_paper_validation_data` entry is an explicit
    assertion that this evidence layer never touched fresh/future data, not
    an omission a reader has to infer."""

    label: str
    used_by: list[str] = Field(default_factory=list)
    start: date | None = None
    end: date | None = None
    trading_day_count: int = 0
    note: str


class NetOfCostExpectancyEvidence(BaseModel):
    status: EvidenceStatus
    net_of_cost_expectancy: float | None = None
    base_expectancy: float | None = None
    sample_size: int | None = None
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS
    reason: str | None = None


class BaselineComparisonEvidence(BaseModel):
    status: EvidenceStatus
    baseline_name: str | None = None
    baseline_mean_outcome: float | None = None
    baseline_sample_size: int | None = None
    oos_expectancy: float | None = None
    oos_sample_size: int | None = None
    net_expectancy: float | None = None
    beats_baseline: bool | None = None
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS
    reason: str | None = None


class RobustnessDetailEvidence(BaseModel):
    status: EvidenceStatus
    robustness_result: RobustnessResult | None = None
    reason: str | None = None


class RegimeProfileEvidence(BaseModel):
    status: EvidenceStatus
    failure_profile: PatternFailureProfile | None = None
    reason: str | None = None


class PatternDefinitionSnapshot(BaseModel):
    """The frozen, hashable identity of the pattern this evidence describes
    -- exactly the field set `docs/PATTERN_PROMOTION_GATE_DESIGN.md`'s v2/
    v2.2 `PromotionCase` design already names as the "frozen fields" a
    future Promotion Gate must freeze at intake. Never includes any
    statistic subject to the `family_size`/`block_bootstrap_p_value`/
    `deflated_sharpe_ratio` reconstruction bug (Part 2 §6.3) -- this module
    does not read those fields at all, from any revision."""

    ticker: str
    conditions: list[FeatureCondition]
    regime_filter: FeatureCondition | None
    target_id: str
    complexity: int
    is_lead_lag: bool

    def content_hash(self) -> str:
        canonical = self.model_dump_json()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PromotionEvidenceProvenance(BaseModel):
    pattern_id: str
    pattern_definition_hash: str
    pattern_registry_version: int
    reproducibility: ReproducibilityManifest
    ticker_universe: list[str]
    transaction_cost_bps: float
    baseline_definition: str
    regime_definition: dict
    bootstrap_seed: int
    methodology_version: str
    data_windows: list[DataWindowProvenance]
    integrity_check_passed: bool
    integrity_check_note: str


def _snapshot_id(
    *,
    pattern_definition_hash: str,
    pattern_registry_version: int,
    dataset_source: str,
    dataset_version: str | None,
    methodology_version: str,
) -> str:
    """Content-derived, not randomly generated -- the same discipline
    `events.service.build_candidate_event()` already uses elsewhere in this
    codebase ("derives the id from a content fingerprint... never mint an
    id with `new_id()`"). Identical inputs always produce the identical id,
    so persisting an unchanged snapshot again is a harmless no-op; any
    change to the pattern definition, registry revision, source data, or
    methodology produces a genuinely new id, never a silent overwrite."""
    basis = "|".join(
        [
            pattern_definition_hash,
            str(pattern_registry_version),
            dataset_source,
            dataset_version or "",
            methodology_version,
        ]
    )
    return "promotion_evidence_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


class PromotionEvidenceSnapshot(BaseModel):
    """Immutable, versioned, fully-provenanced OBSERVED/COMPUTED evidence
    about one pattern. Never contains a promotion decision -- there is no
    `promote`, `eligible`, or `production` field anywhere on this model or
    any of its four evidence sub-objects (enforced by
    `test_promotion_evidence.py::test_schema_contains_no_promotion_decision_fields`).
    `id` is content-derived (see `_snapshot_id`); `model_config` marks every
    instance frozen so no in-place mutation is even possible after
    construction -- a changed input always produces a new object with a new
    id, never an edited one."""

    model_config = ConfigDict(frozen=True)

    id: str
    version: int = 1
    pattern_id: str
    provenance: PromotionEvidenceProvenance
    net_of_cost_expectancy: NetOfCostExpectancyEvidence
    baseline_comparison: BaselineComparisonEvidence
    robustness_detail: RobustnessDetailEvidence
    regime_profile: RegimeProfileEvidence
    created_at: datetime


_FORBIDDEN_FIELD_SUBSTRINGS = ("promote", "eligible", "production", "reject", "promoted")


def _assert_no_decision_fields() -> None:
    """Defensive, import-time self-check -- if a future edit ever adds a
    decision-shaped field to any evidence model, this raises immediately
    rather than letting the schema drift silently. Mirrors the explicit
    test of the same name; kept here too since import-time enforcement
    catches the mistake even for a caller that never runs the test suite."""
    for model in (
        NetOfCostExpectancyEvidence,
        BaselineComparisonEvidence,
        RobustnessDetailEvidence,
        RegimeProfileEvidence,
        PromotionEvidenceSnapshot,
    ):
        for field_name in model.model_fields:
            lowered = field_name.lower()
            if any(bad in lowered for bad in _FORBIDDEN_FIELD_SUBSTRINGS):
                raise AssertionError(
                    f"{model.__name__}.{field_name} looks like a promotion-decision field "
                    "-- evidence objects must never carry a decision (see module docstring)."
                )


_assert_no_decision_fields()


def _empty_data_windows() -> list[DataWindowProvenance]:
    return [
        DataWindowProvenance(
            label="research_period_full",
            used_by=["net_of_cost_expectancy", "robustness_detail"],
            note="All research-period anchor_dates -- identical to what engine.validate() used.",
        ),
        DataWindowProvenance(
            label="walk_forward_oos_folds",
            used_by=["baseline_comparison"],
            note="The out-of-sample fold dates inside WalkForwardValidator's own reconstruction, a sub-portion of research_period_full.",
        ),
        DataWindowProvenance(
            label="full_history_incl_spent_final_holdout",
            used_by=["baseline_comparison", "regime_profile"],
            note=(
                "The pattern's complete date range, INCLUDING the already-spent final_holdout() "
                "slice -- explicitly spent/historical data, never fresh evidence."
            ),
        ),
        DataWindowProvenance(
            label="future_paper_validation_data",
            used_by=[],
            note=(
                "Not used by this evidence layer. Temporal OOS / paper-validation infrastructure "
                "is a separate, not-yet-built component (docs/PATTERN_PROMOTION_GATE_DESIGN.md "
                "v2.2 §8/§13). This module never reads or claims post-as_of data."
            ),
        ),
    ]


def _fill_window(windows: list[DataWindowProvenance], label: str, dates: list[date]) -> None:
    if not dates:
        return
    for w in windows:
        if w.label == label:
            w.start = min(dates)
            w.end = max(dates)
            w.trading_day_count = len(dates)
            return


def compute_promotion_evidence(
    pattern: Pattern,
    panel: ResearchPanel,
    *,
    dataset_source: str = "unknown",
    dataset_version: str | None = None,
    engine_config: PatternDiscoveryEngineConfig | None = None,
) -> PromotionEvidenceSnapshot:
    """Pure function: `(pattern, panel) -> PromotionEvidenceSnapshot`.
    Never mutates `pattern`, the registry, or `panel`. Never raises for
    missing/insufficient source data -- every such case is reflected as
    `EvidenceStatus.INSUFFICIENT_EVIDENCE` on the specific affected field,
    with an explicit `reason`, never inferred or approximated."""
    config = engine_config or _ENGINE_DEFAULTS

    definition = PatternDefinitionSnapshot(
        ticker=pattern.ticker,
        conditions=list(pattern.conditions),
        regime_filter=pattern.regime_filter,
        target_id=pattern.target_id,
        complexity=pattern.complexity,
        is_lead_lag=pattern.is_lead_lag,
    )
    pattern_definition_hash = definition.content_hash()

    manifest = build_reproducibility_manifest(
        engine_name="promotion_evidence_infrastructure",
        engine_version=PROMOTION_EVIDENCE_METHODOLOGY_VERSION,
        dataset_source=dataset_source,
        dataset_version=dataset_version,
        config=config.model_dump(mode="json"),
    )

    data_windows = _empty_data_windows()

    net_of_cost_evidence: NetOfCostExpectancyEvidence
    baseline_evidence: BaselineComparisonEvidence
    robustness_evidence: RobustnessDetailEvidence
    regime_evidence: RegimeProfileEvidence

    integrity_ok = True
    integrity_note = "Reconstructed research-period window matches the pattern's own recorded discovery_period."

    if pattern.ticker not in panel.series:
        reason = f"Ticker {pattern.ticker!r} is not present in the supplied panel -- no source data available."
        net_of_cost_evidence = NetOfCostExpectancyEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=reason)
        baseline_evidence = BaselineComparisonEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=reason)
        robustness_evidence = RobustnessDetailEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=reason)
        regime_evidence = RegimeProfileEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=reason)
        integrity_ok = False
        integrity_note = reason
    else:
        all_features, market_features, targets_by_ticker = _build_context(
            panel, config.horizons, enable_barrier_targets=config.enable_barrier_targets
        )
        targets = targets_by_ticker.get(pattern.ticker, [])
        target = next((t for t in targets if t.id == pattern.target_id), None)

        research_dates, _holdout_dates = _split_research_and_holdout(
            panel.series[pattern.ticker].dates, config.holdout_fraction
        )
        anchor_dates = research_dates
        _fill_window(data_windows, "research_period_full", anchor_dates)
        _fill_window(data_windows, "full_history_incl_spent_final_holdout", panel.series[pattern.ticker].dates)

        if research_dates and pattern.discovery_period is not None:
            reconstructed = (min(research_dates), max(research_dates))
            if reconstructed != pattern.discovery_period:
                integrity_ok = False
                integrity_note = (
                    f"Reconstructed research-period window {reconstructed} does not match the "
                    f"pattern's own recorded discovery_period {pattern.discovery_period} -- the "
                    "supplied panel or engine_config (holdout_fraction) likely differs from what "
                    "the original validate() run used. Refusing to compute evidence on a "
                    "different window than the original run."
                )

        if target is None:
            reason = f"Could not reconstruct target {pattern.target_id!r} from the supplied panel."
            net_of_cost_evidence = NetOfCostExpectancyEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=reason)
            baseline_evidence = BaselineComparisonEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=reason)
            robustness_evidence = RobustnessDetailEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=reason)
        elif not integrity_ok:
            net_of_cost_evidence = NetOfCostExpectancyEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=integrity_note)
            baseline_evidence = BaselineComparisonEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=integrity_note)
            robustness_evidence = RobustnessDetailEvidence(status=EvidenceStatus.INSUFFICIENT_EVIDENCE, reason=integrity_note)
        else:
            ticker_features = [f for f in all_features if f.ticker == pattern.ticker]
            sector_leaders = _sector_leaders(panel) if config.enable_lead_lag else {}
            predictors = (
                _lead_lag_predictor_features(
                    panel, all_features, market_features, pattern.ticker, sector_leaders,
                    config.leader_predictor_feature_keys,
                )
                if pattern.is_lead_lag
                else market_features
            )
            feature_lookup = {f.id: f for f in [*ticker_features, *predictors]}
            candidate = PatternCandidate(
                id=pattern.id, ticker=pattern.ticker, conditions=pattern.conditions,
                is_lead_lag=pattern.is_lead_lag, regime_filter=pattern.regime_filter,
                target_id=pattern.target_id, complexity=pattern.complexity,
            )

            # ---- robustness detail + net-of-cost expectancy (RobustnessTester, unmodified) ----
            nearby_targets = [t for t in targets if t.spec.kind == target.spec.kind and t.id != target.id]
            robustness_result = RobustnessTester().run(
                candidate, anchor_dates=anchor_dates, feature_lookup=feature_lookup, target=target,
                nearby_feature_ids=_nearby_feature_ids(candidate, all_features), nearby_targets=nearby_targets,
            )
            robustness_evidence = RobustnessDetailEvidence(status=EvidenceStatus.COMPUTED, robustness_result=robustness_result)
            if robustness_result.net_of_cost_expectancy is None:
                net_of_cost_evidence = NetOfCostExpectancyEvidence(
                    status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                    reason="RobustnessTester could not compute a base distribution (insufficient matched sample).",
                )
            else:
                net_of_cost_evidence = NetOfCostExpectancyEvidence(
                    status=EvidenceStatus.COMPUTED,
                    net_of_cost_expectancy=robustness_result.net_of_cost_expectancy,
                    base_expectancy=robustness_result.base_expectancy,
                    sample_size=len(anchor_dates),
                )

            # ---- baseline comparison (WalkForwardValidator + baselines.py, unmodified) ----
            wf_result = WalkForwardValidator(config.walk_forward_config).validate(
                candidate, anchor_dates=anchor_dates, feature_lookup=feature_lookup, target=target
            )
            baseline = buy_and_hold_baseline(panel, pattern.ticker, target.spec.horizon_days)
            if wf_result.oos_period is not None:
                oos_start, oos_end = wf_result.oos_period
                for w in data_windows:
                    if w.label == "walk_forward_oos_folds":
                        w.start, w.end = oos_start, oos_end
                        w.trading_day_count = wf_result.oos_sample_size
            if baseline is None:
                baseline_evidence = BaselineComparisonEvidence(
                    status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                    reason="buy_and_hold_baseline() returned None (fewer than 2 forward-return observations for this ticker/horizon).",
                )
            elif wf_result.oos_distribution is None:
                baseline_evidence = BaselineComparisonEvidence(
                    status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                    reason="WalkForwardValidator produced no out-of-sample distribution (insufficient OOS matched sample).",
                    baseline_name=baseline.name, baseline_mean_outcome=baseline.mean_outcome,
                    baseline_sample_size=baseline.sample_size,
                )
            else:
                result = beats_baseline(wf_result.oos_distribution, baseline)
                baseline_evidence = BaselineComparisonEvidence(
                    status=EvidenceStatus.COMPUTED,
                    baseline_name=baseline.name, baseline_mean_outcome=baseline.mean_outcome,
                    baseline_sample_size=baseline.sample_size,
                    oos_expectancy=wf_result.oos_distribution.expectancy,
                    oos_sample_size=wf_result.oos_distribution.sample_count,
                    net_expectancy=wf_result.oos_distribution.expectancy - (DEFAULT_TRANSACTION_COST_BPS / 10_000),
                    beats_baseline=result,
                )

        # ---- regime profile (regimes.py, unmodified) -- always attempted independently ----
        try:
            failure_profile = analyze_pattern_failure_conditions(pattern, panel)
            regime_evidence = RegimeProfileEvidence(status=EvidenceStatus.COMPUTED, failure_profile=failure_profile)
        except Exception as exc:  # noqa: BLE001 -- any reconstruction failure becomes an explicit INSUFFICIENT_EVIDENCE, never a crash or a fabricated value
            regime_evidence = RegimeProfileEvidence(
                status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                reason=f"analyze_pattern_failure_conditions() failed: {type(exc).__name__}: {exc}",
            )

    provenance = PromotionEvidenceProvenance(
        pattern_id=pattern.id,
        pattern_definition_hash=pattern_definition_hash,
        pattern_registry_version=pattern.version,
        reproducibility=manifest,
        ticker_universe=list(panel.tickers),
        transaction_cost_bps=DEFAULT_TRANSACTION_COST_BPS,
        baseline_definition=BASELINE_DEFINITION,
        regime_definition={
            "dimensions": [d.value for d in RegimeDimension],
            "bucket_count": DEFAULT_BUCKET_COUNT,
            "regime_lookback_days": DEFAULT_REGIME_LOOKBACK_DAYS,
            "correlation_lookback_days": CORRELATION_LOOKBACK_DAYS,
        },
        bootstrap_seed=BOOTSTRAP_SEED,
        methodology_version=PROMOTION_EVIDENCE_METHODOLOGY_VERSION,
        data_windows=data_windows,
        integrity_check_passed=integrity_ok,
        integrity_check_note=integrity_note,
    )

    snapshot_id = _snapshot_id(
        pattern_definition_hash=pattern_definition_hash,
        pattern_registry_version=pattern.version,
        dataset_source=dataset_source,
        dataset_version=dataset_version,
        methodology_version=PROMOTION_EVIDENCE_METHODOLOGY_VERSION,
    )

    return PromotionEvidenceSnapshot(
        id=snapshot_id,
        pattern_id=pattern.id,
        provenance=provenance,
        net_of_cost_expectancy=net_of_cost_evidence,
        baseline_comparison=baseline_evidence,
        robustness_detail=robustness_evidence,
        regime_profile=regime_evidence,
        created_at=manifest.generated_at,
    )


class PromotionEvidenceRepository(JsonFileRepository[PromotionEvidenceSnapshot]):
    """Versioned, append-only persistence for `PromotionEvidenceSnapshot`,
    composing `storage.JsonFileRepository` exactly like every other new
    entity in this codebase (`PatternRegistry`, `TestingLedgerRepository`)
    -- no bespoke persistence mechanism. Because `PromotionEvidenceSnapshot
    .id` is content-derived (see `_snapshot_id`), `add()`-ing an unchanged
    snapshot again is idempotent (same id, same content); any genuinely
    different snapshot always carries a different id, so this repository
    never needs, and never performs, an in-place update."""

    def __init__(self, persist_path=None):
        super().__init__(PromotionEvidenceSnapshot, persist_path)


__all__ = [
    "BASELINE_DEFINITION",
    "BOOTSTRAP_SEED",
    "PROMOTION_EVIDENCE_METHODOLOGY_VERSION",
    "BaselineComparisonEvidence",
    "DataWindowProvenance",
    "EvidenceStatus",
    "NetOfCostExpectancyEvidence",
    "PatternDefinitionSnapshot",
    "PromotionEvidenceProvenance",
    "PromotionEvidenceRepository",
    "PromotionEvidenceSnapshot",
    "RegimeProfileEvidence",
    "RobustnessDetailEvidence",
    "compute_promotion_evidence",
]
