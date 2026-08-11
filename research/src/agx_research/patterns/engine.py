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
from agx_research.patterns.outcomes import ActivationOutcome, OutcomeRepository, OutcomeTracker
from agx_research.patterns.panel import ResearchPanel
from agx_research.patterns.registry import Pattern, PatternRegistry, PatternStatus, build_pattern
from agx_research.patterns.robustness import RobustnessTester
from agx_research.patterns.targets import TARGET_HORIZONS, TargetFactory
from agx_research.patterns.validation import WalkForwardResult, WalkForwardValidator, WalkForwardValidatorConfig

ENGINE_NAME = "pattern_discovery_engine"
ENGINE_VERSION = "1.0.0"


class DiscoveryRunReport(BaseModel):
    run_id: str
    as_of: str
    tickers: list[str]
    features_generated: int
    candidates_generated: int
    candidates_meeting_discovery_floor: int
    candidates_surviving_fdr: int
    patterns_discovered: int
    testing_ledger_id: str
    notes: list[str] = Field(default_factory=list)


class ValidationRunReport(BaseModel):
    as_of: str
    patterns_considered: int
    patterns_validated: int
    patterns_rejected: int
    patterns_skipped: int
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
    panel: ResearchPanel, horizons: tuple[int, ...]
) -> tuple[list[FeatureSeries], list[FeatureSeries], dict[str, list]]:
    all_features = FeatureFactory(panel).build_all()
    market_features = [f for f in all_features if f.ticker == ""]
    targets_by_ticker = {
        ticker: TargetFactory(panel, horizons=horizons).build_all(ticker) for ticker in panel.tickers
    }
    return all_features, market_features, targets_by_ticker


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

    def discover(self, panel: ResearchPanel) -> DiscoveryRunReport:
        run_id = new_id("discovery_run")
        notes: list[str] = []
        generator = PatternCandidateGenerator(self.config.candidate_config)
        all_features, market_features, targets_by_ticker = _build_context(panel, self.config.horizons)

        all_candidates: list[PatternCandidate] = []
        context: dict[str, dict] = {}
        for ticker in panel.tickers:
            ticker_features = [f for f in all_features if f.ticker == ticker]
            targets = targets_by_ticker[ticker]
            anchor_dates = panel.series[ticker].dates
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

        if not all_candidates:
            notes.append(
                "No candidates cleared the eligibility/sample-size floor at generation time — "
                "see docs/PATTERN_DISCOVERY_DATA_AUDIT.md for why current data depth makes this "
                "the expected, honest outcome, not a bug."
            )

        discovery_ok: list[tuple[PatternCandidate, object]] = []
        p_values: list[float] = []
        for candidate in all_candidates:
            ctx = context[candidate.id]
            outcomes = _matched(candidate, ctx)
            distribution = evaluate_outcomes(outcomes)
            if distribution is None:
                continue
            discovery_ok.append((candidate, distribution))
            p_values.append(
                distribution.p_value_bootstrap if distribution.p_value_bootstrap is not None else 1.0
            )

        fdr_accept = benjamini_hochberg(p_values, fdr_alpha=self.config.fdr_alpha) if p_values else []
        surviving = [pair for pair, accept in zip(discovery_ok, fdr_accept) if accept]

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
            )
            self.pattern_registry.add(pattern)

        ledger = TestingLedger(
            id=new_id("testing_ledger"),
            run_id=run_id,
            as_of=panel.as_of,
            hypotheses_tested=len(all_candidates),
            discovery_sample_size=sum(len(panel.series[t].dates) for t in panel.tickers),
            validation_sample_size=0,
            fdr_alpha=self.config.fdr_alpha,
            surviving_after_fdr=len(surviving),
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
            candidates_meeting_discovery_floor=len(discovery_ok),
            candidates_surviving_fdr=len(surviving),
            patterns_discovered=len(surviving),
            testing_ledger_id=ledger.id,
            notes=notes,
        )

    # ---- phase 2: purged walk-forward validation + robustness + baselines ----

    def validate(self, panel: ResearchPanel) -> ValidationRunReport:
        discovered = self.pattern_registry.by_status(PatternStatus.DISCOVERED)
        notes: list[str] = []
        if not discovered:
            notes.append("No DISCOVERED patterns in the registry to validate — run `agx research discover` first.")
            return ValidationRunReport(
                as_of=panel.as_of.isoformat(), patterns_considered=0, patterns_validated=0,
                patterns_rejected=0, patterns_skipped=0, notes=notes,
            )

        all_features, market_features, targets_by_ticker = _build_context(panel, self.config.horizons)
        validator = WalkForwardValidator(self.config.walk_forward_config)
        robustness_tester = RobustnessTester() if self.config.run_robustness else None

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
            feature_lookup = {f.id: f for f in [*ticker_features, *market_features]}
            anchor_dates = panel.series[pattern.ticker].dates
            candidate = PatternCandidate(
                id=pattern.id,
                ticker=pattern.ticker,
                conditions=pattern.conditions,
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
                status = PatternStatus.VALIDATED
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

        return ValidationRunReport(
            as_of=panel.as_of.isoformat(),
            patterns_considered=len(discovered),
            patterns_validated=validated_count,
            patterns_rejected=rejected_count,
            patterns_skipped=skipped_count,
            notes=notes,
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
    "PatternDiscoveryEngine",
    "PatternDiscoveryEngineConfig",
    "ValidationRunReport",
]
