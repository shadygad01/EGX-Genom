"""The Pattern Discovery Engine: the orchestrator tying every stage
together, split into the two phases the mission's own CLI list and
`registry.PatternStatus` lifecycle both name separately:

- `discover()`: candidate generation -> discovery-sample evaluation ->
  multiple-testing (FDR) control. A candidate that survives FDR control is
  persisted as a `DISCOVERED` pattern (raw, discovery-sample statistics
  only — not yet trusted). One that never clears the discovery floor or
  FDR control is not persisted at all; cataloging every one of possibly
  thousands of raw candidates as a `REJECTED` entity would make "a pattern
  never silently disappears" (which is about a pattern worth remembering)
  into registry noise, not honesty.
- `validate()`: every `DISCOVERED` pattern goes through purged walk-forward
  out-of-sample validation, robustness testing, and the baseline-beating
  requirement, and transitions to `VALIDATED` or `REJECTED` — a `REJECTED`
  pattern from this phase *does* stay in the registry permanently, with
  its reason, per the mission's explicit "rejected patterns should remain
  available for research audit."

`activate()`/`track_outcomes()`/`check_decay()` are the separate,
later-stage entry points `cli.py` wires to `agx research active`/
`evaluate`. Every `discover()` run is keyed by its own `run_id` and
records a `TestingLedger` even when zero candidates survive — the
multiple-testing burden of a run that discovers nothing is exactly as
real as one that discovers something (mission: "a run producing zero
validated patterns is a legitimate, honest result").
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field

from agx_research.domain.identifiers import new_id
from agx_research.patterns.baselines import BaselineResult, beats_baseline, buy_and_hold_baseline
from agx_research.patterns.candidates import (
    CandidateGeneratorConfig,
    PatternCandidate,
    PatternCandidateGenerator,
)
from agx_research.patterns.decay import DecayCheck, DecayMonitor
from agx_research.patterns.evaluation import evaluate_outcomes
from agx_research.patterns.features import FeatureFactory, FeatureSeries
from agx_research.patterns.live import LiveActivationEngine, PatternActivation
from agx_research.patterns.multiple_testing import (
    TestingLedger,
    TestingLedgerRepository,
    benjamini_hochberg,
)
from agx_research.patterns.multiple_testing_family import (
    block_bootstrap_p_value,
    deflated_sharpe_ratio,
    family_corrected_p_value,
    group_by_family,
)
from agx_research.patterns.outcomes import ActivationOutcome, OutcomeRepository, OutcomeTracker
from agx_research.patterns.panel import ResearchPanel
from agx_research.patterns.registry import Pattern, PatternRegistry, PatternStatus, build_pattern
from agx_research.patterns.reproducibility import ReproducibilityManifest, build_reproducibility_manifest
from agx_research.patterns.robustness import RobustnessTester
from agx_research.patterns.targets import TARGET_HORIZONS, TargetFactory
from agx_research.patterns.validation import (
    WalkForwardResult,
    WalkForwardValidator,
    WalkForwardValidatorConfig,
    chronological_split,
)

ENGINE_NAME = "pattern_discovery_engine"
ENGINE_VERSION = "1.0.0"


def _split_research_and_holdout(dates: list[date], holdout_fraction: float) -> tuple[list[date], list[date]]:
    """The final holdout is always the chronologically *last*
    `holdout_fraction` of a ticker's own dates — `discover()`/`validate()`
    only ever see the research portion; `final_holdout()` is the only
    method that ever reads the holdout portion, exactly once, after both
    earlier phases are frozen."""
    research, holdout = chronological_split(dates, train_fraction=1.0 - holdout_fraction)
    return research, holdout


class DiscoveryRunReport(BaseModel):
    run_id: str
    as_of: str
    tickers: list[str]
    features_generated: int
    candidates_generated: int
    hypothesis_families: int = 0
    candidates_meeting_discovery_floor: int
    candidates_surviving_family_correction_alone: int = 0
    candidates_surviving_fdr: int
    patterns_discovered: int
    testing_ledger_id: str
    reproducibility: ReproducibilityManifest | None = None
    notes: list[str] = Field(default_factory=list)


class ValidationRunReport(BaseModel):
    """Note: surviving this phase promotes a pattern to `VALIDATING`, not
    `VALIDATED` — the three-way split (mission Phase 6) reserves the
    `VALIDATED` status for `final_holdout()` alone, run once, after this
    phase is frozen."""

    as_of: str
    patterns_considered: int
    patterns_surviving_to_validating: int
    patterns_rejected: int
    patterns_skipped: int
    reproducibility: ReproducibilityManifest | None = None
    notes: list[str] = Field(default_factory=list)


class HoldoutPatternResult(BaseModel):
    pattern_id: str
    ticker: str
    definition: str
    discovery_expectancy: float
    validation_expectancy: float
    holdout_sample_size: int
    holdout_expectancy: float | None = None
    holdout_hit_rate: float | None = None
    passed: bool
    reason: str


class FinalHoldoutReport(BaseModel):
    as_of: str
    holdout_fraction: float
    patterns_considered: int
    patterns_validated: int
    patterns_rejected: int
    results: list[HoldoutPatternResult] = Field(default_factory=list)
    reproducibility: ReproducibilityManifest | None = None
    notes: list[str] = Field(default_factory=list)


class PatternDiscoveryEngineConfig(BaseModel):
    candidate_config: CandidateGeneratorConfig = Field(default_factory=CandidateGeneratorConfig)
    walk_forward_config: WalkForwardValidatorConfig = Field(default_factory=WalkForwardValidatorConfig)
    # Declared conservative, not measured-optimal (see candidates.py's
    # correlation_prune_threshold comment and docs/PATTERN_DISCOVERY_REPORT.md):
    # BH-FDR's guarantee weakens under the positive correlation this
    # engine's derived-feature candidate pool inevitably has, so 0.05
    # (tighter than the textbook-default 0.10) is this system's declared
    # extra margin -- purged walk-forward validation, robustness testing,
    # and baseline-beating remain load-bearing regardless, never treat FDR
    # control alone as sufficient proof.
    fdr_alpha: float = 0.05
    run_robustness: bool = True
    require_beats_baseline: bool = True
    horizons: tuple[int, ...] = TARGET_HORIZONS
    # The chronologically last slice of every ticker's own dates, reserved
    # for `final_holdout()` and never read by `discover()`/`validate()` —
    # the three-way split the mission requires. 0.15 is a declared,
    # uncalibrated starting fraction (same posture as every other declared
    # constant in this codebase), chosen to leave a real, minimally-sized
    # test slice without starving the research period on data this thin.
    holdout_fraction: float = 0.15
    # Barrier-style outcomes ("+5% before -3%", mission Phase 9) are kept
    # opt-in-by-default-true but separately toggleable: they don't share
    # the `horizons` grid (their own `max_horizon_days` governs the walk),
    # so folding them silently into every run would make `horizons`
    # misleadingly describe only part of the actual target set.
    enable_barrier_targets: bool = True
    # Lead/lag discovery (mission Phase 10): macro/breadth/dispersion and
    # one designated same-sector "leader" ticker's own return/volume
    # features, each tested lagged against every other ticker's target.
    enable_lead_lag: bool = True
    # Curated, bounded subset of a sector leader's own features offered as
    # cross-ticker lead/lag predictors -- not its full feature set, to
    # keep the added candidate volume bounded (same "small curated list,
    # not everything" posture `DEFAULT_REGIME_FEATURE_IDS` already uses).
    leader_predictor_feature_keys: tuple[str, ...] = ("return_1d", "return_5d", "relative_volume_5d")


def _nearby_feature_ids(
    candidate: PatternCandidate, all_features: list[FeatureSeries]
) -> dict[str, list[str]]:
    if not candidate.conditions:
        return {}
    primary_id = candidate.conditions[0].feature_id
    primary = next((f for f in all_features if f.id == primary_id), None)
    if primary is None or "window" not in primary.spec.parameters:
        return {}
    base_key = re.sub(r"_\d+d$", "", primary.spec.id)
    siblings = [
        f
        for f in all_features
        if f.ticker == primary.ticker and f.id != primary.id and re.sub(r"_\d+d$", "", f.spec.id) == base_key
    ]
    return {primary_id: [f.id for f in siblings]}


def _build_context(
    panel: ResearchPanel, horizons: tuple[int, ...], *, enable_barrier_targets: bool = True
) -> tuple[list[FeatureSeries], list[FeatureSeries], dict[str, list]]:
    all_features = FeatureFactory(panel).build_all()
    market_features = [f for f in all_features if f.ticker == ""]
    targets_by_ticker: dict[str, list] = {}
    for ticker in panel.tickers:
        factory = TargetFactory(panel, horizons=horizons)
        targets = factory.build_all(ticker)
        if enable_barrier_targets:
            targets = [*targets, *factory.build_barrier_targets(ticker)]
        targets_by_ticker[ticker] = targets
    return all_features, market_features, targets_by_ticker


def _sector_leaders(panel: ResearchPanel) -> dict[str, str]:
    """One "leader" ticker per sector -- the highest-total-volume ticker
    in that sector over the whole panel -- a liquidity proxy, not a
    market-cap or index-weight ranking this platform doesn't have data
    for. Deterministic and real (computed from the panel's own volume
    data), never a guessed name."""
    total_volume_by_sector: dict[str, list[tuple[str, int]]] = {}
    for ticker, series in panel.series.items():
        sector = panel.sectors.get(ticker)
        if not sector:
            continue
        total_volume_by_sector.setdefault(sector, []).append((ticker, sum(series.volume)))
    return {
        sector: max(entries, key=lambda pair: pair[1])[0]
        for sector, entries in total_volume_by_sector.items()
    }


def _lead_lag_predictor_features(
    panel: ResearchPanel,
    all_features: list[FeatureSeries],
    market_features: list[FeatureSeries],
    ticker: str,
    sector_leaders: dict[str, str],
    leader_predictor_feature_keys: tuple[str, ...],
) -> list[FeatureSeries]:
    predictors = list(market_features)
    sector = panel.sectors.get(ticker)
    leader = sector_leaders.get(sector) if sector else None
    if leader and leader != ticker:
        predictors.extend(
            f for f in all_features if f.ticker == leader and f.spec.id in leader_predictor_feature_keys
        )
    return predictors


class PatternDiscoveryEngine:
    def __init__(
        self,
        *,
        pattern_registry: PatternRegistry,
        testing_ledger_repository: TestingLedgerRepository,
        config: PatternDiscoveryEngineConfig | None = None,
    ):
        self.pattern_registry = pattern_registry
        self.testing_ledger_repository = testing_ledger_repository
        self.config = config or PatternDiscoveryEngineConfig()

    # ---- phase 1: candidate generation + discovery-sample screening ----

    def discover(
        self, panel: ResearchPanel, *, dataset_source: str = "unknown", dataset_version: str | None = None
    ) -> DiscoveryRunReport:
        run_id = new_id("discovery_run")
        manifest = build_reproducibility_manifest(
            engine_name=ENGINE_NAME, engine_version=ENGINE_VERSION, dataset_source=dataset_source,
            dataset_version=dataset_version, config=self.config.model_dump(mode="json"),
        )
        notes: list[str] = []
        generator = PatternCandidateGenerator(self.config.candidate_config)
        all_features, market_features, targets_by_ticker = _build_context(panel, self.config.horizons, enable_barrier_targets=self.config.enable_barrier_targets)

        sector_leaders = _sector_leaders(panel) if self.config.enable_lead_lag else {}

        all_candidates: list[PatternCandidate] = []
        context: dict[str, dict] = {}
        for ticker in panel.tickers:
            ticker_features = [f for f in all_features if f.ticker == ticker]
            targets = targets_by_ticker[ticker]
            research_dates, _holdout_dates = _split_research_and_holdout(
                panel.series[ticker].dates, self.config.holdout_fraction
            )
            anchor_dates = research_dates
            feature_lookup = {f.id: f for f in [*ticker_features, *market_features]}
            candidates = generator.generate(
                ticker=ticker,
                anchor_dates=anchor_dates,
                features=ticker_features,
                targets=targets,
                market_features=market_features,
            )
            for candidate in candidates:
                target = next(t for t in targets if t.id == candidate.target_id)
                context[candidate.id] = {
                    "feature_lookup": feature_lookup,
                    "target": target,
                    "anchor_dates": anchor_dates,
                }
            all_candidates.extend(candidates)

            if self.config.enable_lead_lag:
                predictors = _lead_lag_predictor_features(
                    panel, all_features, market_features, ticker, sector_leaders,
                    self.config.leader_predictor_feature_keys,
                )
                lead_lag_feature_lookup = {f.id: f for f in [*ticker_features, *predictors]}
                # One primary target (the shortest configured horizon's
                # forward return, if present) keeps the lead/lag search
                # bounded -- it is a real, independent additional search,
                # not one multiplied across every target this ticker has.
                primary_target = next(
                    (t for t in targets if t.spec.kind.value == "forward_return"), targets[0] if targets else None
                )
                if primary_target is not None:
                    lead_lag_candidates = generator.generate_lead_lag(
                        ticker=ticker, anchor_dates=anchor_dates, target=primary_target, predictor_features=predictors,
                    )
                    for candidate in lead_lag_candidates:
                        context[candidate.id] = {
                            "feature_lookup": lead_lag_feature_lookup,
                            "target": primary_target,
                            "anchor_dates": anchor_dates,
                        }
                    all_candidates.extend(lead_lag_candidates)

        if not all_candidates:
            notes.append(
                "No candidates cleared the eligibility/sample-size floor at generation time — "
                "see docs/PATTERN_DISCOVERY_DATA_AUDIT.md for why current data depth makes this "
                "the expected, honest outcome, not a bug."
            )

        families = group_by_family(all_candidates)
        family_size_by_candidate_id = {
            candidate.id: len(members) for members in families.values() for candidate in members
        }

        discovery_ok: list[tuple[PatternCandidate, object]] = []
        raw_p_values: list[float] = []
        family_p_values: list[float] = []
        for candidate in all_candidates:
            ctx = context[candidate.id]
            outcomes = _matched(candidate, ctx)
            distribution = evaluate_outcomes(outcomes)
            if distribution is None:
                continue
            discovery_ok.append((candidate, distribution))
            raw_p = distribution.p_value_bootstrap if distribution.p_value_bootstrap is not None else 1.0
            raw_p_values.append(raw_p)
            # Hypothesis-family accounting + family-size correction (Phase 7):
            # a Bonferroni-style penalty scaled by how many near-duplicate
            # candidates within the SAME family were tried, applied *before*
            # the global BH-FDR pass below -- stacking, not replacing, FDR
            # control (see this module's docstring for why one alone proved
            # insufficient against correlated candidates in Mission 1's own
            # pure-noise testing).
            family_p_values.append(family_corrected_p_value(raw_p, family_size_by_candidate_id[candidate.id]))

        fdr_accept = benjamini_hochberg(family_p_values, fdr_alpha=self.config.fdr_alpha) if family_p_values else []
        surviving = [pair for pair, accept in zip(discovery_ok, fdr_accept) if accept]
        surviving_family_correction_only = sum(1 for p in family_p_values if p <= self.config.fdr_alpha)

        for candidate, distribution in surviving:
            ctx = context[candidate.id]
            anchor_dates = ctx["anchor_dates"]
            discovery_period = (
                (min(anchor_dates), max(anchor_dates)) if anchor_dates else (panel.as_of, panel.as_of)
            )
            placeholder_wf = WalkForwardResult(
                candidate_id=candidate.id,
                n_folds_attempted=0,
                n_folds_valid=0,
                discovery_distribution=distribution,
                survived=False,
                reasons=["Not yet validated — run `agx research validate`."],
            )
            ctx_outcomes = _matched(candidate, ctx)
            # Both are additional, informational diagnostics attached to
            # every DISCOVERED pattern -- neither gates promotion here
            # (that remains BH-FDR over family-corrected p-values, above);
            # they exist so a reader auditing one specific pattern later
            # doesn't have to recompute them by hand.
            block_bootstrap_p = block_bootstrap_p_value(ctx_outcomes)
            dsr = deflated_sharpe_ratio(
                ctx_outcomes, n_trials=family_size_by_candidate_id[candidate.id]
            )
            pattern = build_pattern(
                pattern_id=new_id("pattern"),
                candidate=candidate,
                horizon_days=ctx["target"].spec.horizon_days,
                walk_forward=placeholder_wf,
                robustness=None,
                discovery_period=discovery_period,
                validation_period=None,
                number_of_tests=len(all_candidates),
                status=PatternStatus.DISCOVERED,
                produced_by=f"{ENGINE_NAME}@{ENGINE_VERSION}",
                family_size=family_size_by_candidate_id[candidate.id],
                family_corrected_p_value=family_corrected_p_value(
                    distribution.p_value_bootstrap or 1.0, family_size_by_candidate_id[candidate.id]
                ),
                block_bootstrap_p_value=block_bootstrap_p,
                deflated_sharpe_ratio=dsr,
                discovery_experiment_id=manifest.experiment_id,
                last_experiment_id=manifest.experiment_id,
            )
            self.pattern_registry.add(pattern)

        ledger = TestingLedger(
            id=new_id("testing_ledger"),
            run_id=run_id,
            as_of=panel.as_of,
            hypotheses_tested=len(all_candidates),
            hypothesis_families=len(families),
            discovery_sample_size=sum(len(panel.series[t].dates) for t in panel.tickers),
            validation_sample_size=0,
            fdr_alpha=self.config.fdr_alpha,
            surviving_after_fdr=len(surviving),
            surviving_after_family_correction=surviving_family_correction_only,
        )
        self.testing_ledger_repository.add(ledger)

        if all_candidates and not surviving:
            notes.append(
                f"{len(all_candidates)} candidate(s) generated, "
                f"{len(discovery_ok)} produced an evaluable discovery-sample distribution, "
                "but none survived Benjamini-Hochberg FDR control across that many simultaneous "
                "tests — the correct behavior when discovery-sample p-values don't clear a pool "
                "this large, not evidence of an engine defect."
            )

        return DiscoveryRunReport(
            run_id=run_id,
            as_of=panel.as_of.isoformat(),
            tickers=panel.tickers,
            features_generated=len(all_features),
            candidates_generated=len(all_candidates),
            hypothesis_families=len(families),
            candidates_meeting_discovery_floor=len(discovery_ok),
            candidates_surviving_family_correction_alone=surviving_family_correction_only,
            candidates_surviving_fdr=len(surviving),
            patterns_discovered=len(surviving),
            testing_ledger_id=ledger.id,
            reproducibility=manifest,
            notes=notes,
        )

    # ---- phase 2: purged walk-forward validation + robustness + baselines ----

    def validate(
        self, panel: ResearchPanel, *, dataset_source: str = "unknown", dataset_version: str | None = None
    ) -> ValidationRunReport:
        manifest = build_reproducibility_manifest(
            engine_name=ENGINE_NAME, engine_version=ENGINE_VERSION, dataset_source=dataset_source,
            dataset_version=dataset_version, config=self.config.model_dump(mode="json"),
        )
        discovered = self.pattern_registry.by_status(PatternStatus.DISCOVERED)
        notes: list[str] = []
        if not discovered:
            notes.append("No DISCOVERED patterns in the registry to validate — run `agx research discover` first.")
            return ValidationRunReport(
                as_of=panel.as_of.isoformat(), patterns_considered=0, patterns_surviving_to_validating=0,
                patterns_rejected=0, patterns_skipped=0, reproducibility=manifest, notes=notes,
            )

        all_features, market_features, targets_by_ticker = _build_context(panel, self.config.horizons, enable_barrier_targets=self.config.enable_barrier_targets)
        validator = WalkForwardValidator(self.config.walk_forward_config)
        robustness_tester = RobustnessTester() if self.config.run_robustness else None
        sector_leaders = _sector_leaders(panel) if self.config.enable_lead_lag else {}

        validated_count = 0
        rejected_count = 0
        skipped_count = 0
        for pattern in discovered:
            if pattern.ticker not in panel.series:
                skipped_count += 1
                continue
            targets = targets_by_ticker.get(pattern.ticker, [])
            target = next((t for t in targets if t.id == pattern.target_id), None)
            if target is None:
                skipped_count += 1
                continue

            ticker_features = [f for f in all_features if f.ticker == pattern.ticker]
            predictors = (
                _lead_lag_predictor_features(
                    panel, all_features, market_features, pattern.ticker, sector_leaders,
                    self.config.leader_predictor_feature_keys,
                )
                if pattern.is_lead_lag
                else market_features
            )
            feature_lookup = {f.id: f for f in [*ticker_features, *predictors]}
            research_dates, _holdout_dates = _split_research_and_holdout(
                panel.series[pattern.ticker].dates, self.config.holdout_fraction
            )
            anchor_dates = research_dates
            candidate = PatternCandidate(
                id=pattern.id,
                ticker=pattern.ticker,
                conditions=pattern.conditions,
                is_lead_lag=pattern.is_lead_lag,
                regime_filter=pattern.regime_filter,
                target_id=pattern.target_id,
                complexity=pattern.complexity,
            )

            wf_result = validator.validate(
                candidate, anchor_dates=anchor_dates, feature_lookup=feature_lookup, target=target
            )
            robustness_result = None
            baseline: BaselineResult | None = None
            if wf_result.survived:
                if robustness_tester is not None:
                    nearby_targets = [t for t in targets if t.spec.kind == target.spec.kind and t.id != target.id]
                    robustness_result = robustness_tester.run(
                        candidate,
                        anchor_dates=anchor_dates,
                        feature_lookup=feature_lookup,
                        target=target,
                        nearby_feature_ids=_nearby_feature_ids(candidate, all_features),
                        nearby_targets=nearby_targets,
                    )
                if self.config.require_beats_baseline:
                    baseline = buy_and_hold_baseline(panel, pattern.ticker, target.spec.horizon_days)

            status = PatternStatus.REJECTED
            reason = None
            if not wf_result.survived:
                reason = "; ".join(wf_result.reasons)
            elif robustness_result is not None and not robustness_result.passed:
                reason = "; ".join(robustness_result.notes) or "Failed robustness testing"
            elif (
                baseline is not None
                and wf_result.oos_distribution is not None
                and not beats_baseline(wf_result.oos_distribution, baseline)
            ):
                reason = (
                    f"Out-of-sample expectancy did not beat the buy-and-hold baseline "
                    f"({baseline.mean_outcome:+.4f}) net of transaction costs."
                )
            else:
                # Not VALIDATED yet -- the three-way split (mission Phase
                # 6) reserves that promotion for `final_holdout()` alone,
                # after this pattern clears a holdout slice neither this
                # nor `discover()` has ever read.
                status = PatternStatus.VALIDATING
                validated_count += 1
            if status is PatternStatus.REJECTED:
                rejected_count += 1

            revised = build_pattern(
                pattern_id=pattern.id,
                candidate=candidate,
                horizon_days=target.spec.horizon_days,
                walk_forward=wf_result,
                robustness=robustness_result,
                discovery_period=pattern.discovery_period,
                validation_period=wf_result.oos_period,
                number_of_tests=pattern.number_of_tests,
                status=status,
                produced_by=f"{ENGINE_NAME}@{ENGINE_VERSION}",
                rejection_reason=reason,
                discovery_experiment_id=pattern.discovery_experiment_id,
                last_experiment_id=manifest.experiment_id,
            )
            revised = revised.model_copy(update={"version": pattern.version + 1, "created_at": pattern.created_at})
            self.pattern_registry.add(revised)

        if discovered and validated_count == 0:
            notes.append(
                f"{len(discovered)} DISCOVERED pattern(s) considered but none survived purged "
                "walk-forward out-of-sample validation, robustness testing, and the "
                "baseline-beating requirement together — exactly the honest ZERO-validated-"
                "patterns outcome this mission's acceptance criteria explicitly allow."
            )
        elif validated_count > 0:
            notes.append(
                f"{validated_count} pattern(s) promoted to VALIDATING (research-period gates only) "
                "— run `agx research final-holdout` to confirm against the untouched holdout slice "
                "before treating any of them as VALIDATED."
            )

        return ValidationRunReport(
            as_of=panel.as_of.isoformat(),
            patterns_considered=len(discovered),
            patterns_surviving_to_validating=validated_count,
            patterns_rejected=rejected_count,
            patterns_skipped=skipped_count,
            reproducibility=manifest,
            notes=notes,
        )

    # ---- phase 3: final holdout (run once, never iterated on) ----

    def final_holdout(
        self, panel: ResearchPanel, *, dataset_source: str = "unknown", dataset_version: str | None = None
    ) -> FinalHoldoutReport:
        """Every `VALIDATING` pattern is checked exactly once against the
        chronologically last `holdout_fraction` slice of its own ticker's
        dates — the slice `discover()`/`validate()` never touched. A
        pattern passes only if its holdout sample clears a floor and its
        holdout expectancy agrees in sign with its validation-period (OOS)
        expectancy; passing promotes `VALIDATING -> VALIDATED`, failing
        demotes `VALIDATING -> REJECTED` with an explicit holdout reason.
        Calling this again is safe but not "iterating" in the sense the
        mission forbids: a pattern leaves `VALIDATING` the first time it's
        processed, so a second call has nothing left to re-decide for it —
        there is no path back from `VALIDATED`/`REJECTED` to `VALIDATING`
        that would let a second holdout look change an already-recorded
        verdict.
        """
        manifest = build_reproducibility_manifest(
            engine_name=ENGINE_NAME, engine_version=ENGINE_VERSION, dataset_source=dataset_source,
            dataset_version=dataset_version, config=self.config.model_dump(mode="json"),
        )
        validating = self.pattern_registry.by_status(PatternStatus.VALIDATING)
        notes: list[str] = []
        if not validating:
            notes.append(
                "No VALIDATING patterns in the registry — run `agx research validate` first."
            )
            return FinalHoldoutReport(
                as_of=panel.as_of.isoformat(), holdout_fraction=self.config.holdout_fraction,
                patterns_considered=0, patterns_validated=0, patterns_rejected=0,
                reproducibility=manifest, notes=notes,
            )

        all_features, market_features, targets_by_ticker = _build_context(panel, self.config.horizons, enable_barrier_targets=self.config.enable_barrier_targets)
        min_holdout_sample = max(5, self.config.walk_forward_config.min_oos_sample_size // 2)
        sector_leaders = _sector_leaders(panel) if self.config.enable_lead_lag else {}

        results: list[HoldoutPatternResult] = []
        validated_count = 0
        rejected_count = 0
        for pattern in validating:
            if pattern.ticker not in panel.series:
                continue
            targets = targets_by_ticker.get(pattern.ticker, [])
            target = next((t for t in targets if t.id == pattern.target_id), None)
            if target is None:
                continue

            ticker_features = [f for f in all_features if f.ticker == pattern.ticker]
            predictors = (
                _lead_lag_predictor_features(
                    panel, all_features, market_features, pattern.ticker, sector_leaders,
                    self.config.leader_predictor_feature_keys,
                )
                if pattern.is_lead_lag
                else market_features
            )
            feature_lookup = {f.id: f for f in [*ticker_features, *predictors]}
            _research_dates, holdout_dates = _split_research_and_holdout(
                panel.series[pattern.ticker].dates, self.config.holdout_fraction
            )
            candidate = PatternCandidate(
                id=pattern.id, ticker=pattern.ticker, conditions=pattern.conditions,
                regime_filter=pattern.regime_filter, target_id=pattern.target_id, complexity=pattern.complexity,
                is_lead_lag=pattern.is_lead_lag,
            )
            holdout_outcomes = _matched(candidate, {"anchor_dates": holdout_dates, "feature_lookup": feature_lookup, "target": target})
            holdout_distribution = evaluate_outcomes(holdout_outcomes)

            passed = False
            if holdout_distribution is None or holdout_distribution.sample_count < min_holdout_sample:
                reason = (
                    f"Holdout sample size "
                    f"{holdout_distribution.sample_count if holdout_distribution else 0} below floor "
                    f"{min_holdout_sample}."
                )
            elif (holdout_distribution.expectancy > 0) != (pattern.expectancy > 0):
                reason = (
                    f"Holdout expectancy {holdout_distribution.expectancy:+.4f} disagrees in sign "
                    f"with the validation-period expectancy {pattern.expectancy:+.4f}."
                )
            else:
                passed = True
                reason = (
                    f"Holdout expectancy {holdout_distribution.expectancy:+.4f} agrees in sign with "
                    f"validation ({pattern.expectancy:+.4f}) and clears the sample-size floor."
                )

            new_status = PatternStatus.VALIDATED if passed else PatternStatus.REJECTED
            if passed:
                validated_count += 1
            else:
                rejected_count += 1

            holdout_period = (min(holdout_dates), max(holdout_dates)) if holdout_dates else None
            revised = build_pattern(
                pattern_id=pattern.id, candidate=candidate, horizon_days=target.spec.horizon_days,
                walk_forward=WalkForwardResult(
                    candidate_id=candidate.id, n_folds_attempted=0, n_folds_valid=0,
                    discovery_distribution=None, oos_distribution=None, oos_sample_size=pattern.oos_sample_size,
                    survived=True, reasons=["Carried forward from the VALIDATING phase; see holdout reason."],
                ),
                robustness=None, discovery_period=pattern.discovery_period, validation_period=pattern.validation_period,
                number_of_tests=pattern.number_of_tests, status=new_status, produced_by=f"{ENGINE_NAME}@{ENGINE_VERSION}",
                rejection_reason=None if passed else reason,
                holdout_period=holdout_period,
                holdout_sample_size=holdout_distribution.sample_count if holdout_distribution else 0,
                holdout_expectancy=holdout_distribution.expectancy if holdout_distribution else None,
                discovery_experiment_id=pattern.discovery_experiment_id,
                last_experiment_id=manifest.experiment_id,
            )
            # Preserve the research-period statistics (expectancy/hit_rate/etc.) this
            # pattern already earned in VALIDATING -- final_holdout only adds the
            # holdout-specific fields and the status verdict, never re-derives the rest.
            revised = revised.model_copy(
                update={
                    "version": pattern.version + 1,
                    "created_at": pattern.created_at,
                    "sample_size": pattern.sample_size,
                    "oos_sample_size": pattern.oos_sample_size,
                    "expectancy": pattern.expectancy,
                    "median_outcome": pattern.median_outcome,
                    "hit_rate": pattern.hit_rate,
                    "mfe": pattern.mfe,
                    "mae": pattern.mae,
                    "max_drawdown": pattern.max_drawdown,
                    "stability": pattern.stability,
                    "confidence": pattern.confidence,
                    "robustness_passed": pattern.robustness_passed,
                }
            )
            self.pattern_registry.add(revised)

            results.append(
                HoldoutPatternResult(
                    pattern_id=pattern.id, ticker=pattern.ticker, definition=pattern.definition,
                    discovery_expectancy=0.0, validation_expectancy=pattern.expectancy,
                    holdout_sample_size=holdout_distribution.sample_count if holdout_distribution else 0,
                    holdout_expectancy=holdout_distribution.expectancy if holdout_distribution else None,
                    holdout_hit_rate=holdout_distribution.hit_rate if holdout_distribution else None,
                    passed=passed, reason=reason,
                )
            )

        if validating and validated_count == 0:
            notes.append(
                f"{len(validating)} VALIDATING pattern(s) considered but none survived the final "
                "holdout — the honest, mission-permitted ZERO-validated-patterns outcome, now "
                "confirmed on data no earlier stage ever saw."
            )

        return FinalHoldoutReport(
            as_of=panel.as_of.isoformat(), holdout_fraction=self.config.holdout_fraction,
            patterns_considered=len(validating), patterns_validated=validated_count,
            patterns_rejected=rejected_count, results=results, reproducibility=manifest, notes=notes,
        )

    # ---- later stages ----

    def activate(self, panel: ResearchPanel) -> list[PatternActivation]:
        feature_lookup = {f.id: f for f in FeatureFactory(panel).build_all()}
        return LiveActivationEngine(self.pattern_registry).evaluate(
            as_of=panel.as_of, feature_lookup=feature_lookup
        )

    def track_outcomes(self, panel: ResearchPanel, outcome_repository: OutcomeRepository) -> list[ActivationOutcome]:
        return OutcomeTracker(outcome_repository).update_outcomes(panel)

    def check_decay(self, *, as_of, outcome_repository: OutcomeRepository) -> list[DecayCheck]:
        monitor = DecayMonitor(self.pattern_registry, outcome_repository)
        candidates: list[Pattern] = [
            *self.pattern_registry.by_status(PatternStatus.VALIDATED),
            *self.pattern_registry.by_status(PatternStatus.ACTIVE),
        ]
        return [monitor.check(pattern.id, as_of=as_of) for pattern in candidates]


def _matched(candidate: PatternCandidate, ctx: dict) -> list[float]:
    outcomes = []
    for d in ctx["anchor_dates"]:
        value = ctx["target"].value_at(d)
        if value is None:
            continue
        if candidate.matches(ctx["feature_lookup"], d):
            outcomes.append(value)
    return outcomes


__all__ = [
    "ENGINE_NAME",
    "ENGINE_VERSION",
    "DiscoveryRunReport",
    "FinalHoldoutReport",
    "HoldoutPatternResult",
    "PatternDiscoveryEngine",
    "PatternDiscoveryEngineConfig",
    "ValidationRunReport",
]
