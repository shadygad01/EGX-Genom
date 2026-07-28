"""The Adversarial Scientist: its sole purpose is to try to invalidate discoveries.

Six attacks are real and mechanical: `SmallSampleBias`, `TimeLeakage`,
`LookAheadBias`, `WeakEconomicRationale`, `RandomCoincidence` (a seeded
permutation test of the hypothesis statistic against a shuffled null), and
`ParameterInstability` (sign stability of the statistic across estimation
windows). The remaining three (`Overfitting`, `RegimeDependency`,
`OutOfSampleDegradation`) need either a multi-model comparison harness,
labeled multi-regime history, or a live monitoring record that doesn't
exist yet — `attack()` still reports all nine attack types, marking the
unimplemented ones `attempted=False` rather than omitting them or faking
a result.

Successful attacks (a real problem found) reduce confidence. A check that
finds no problem is neutral: absence of a detected flaw is not independent
positive evidence. Unattempted attacks also contribute nothing.
"""

from __future__ import annotations

from datetime import datetime

from agx_research.adversarial.attacks import AttackResult, AttackType
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.hypotheses.experiment import ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis

_UNIMPLEMENTED_ATTACKS = (
    AttackType.OVERFITTING,
    AttackType.REGIME_DEPENDENCY,
    AttackType.OUT_OF_SAMPLE_DEGRADATION,
)

_UNIMPLEMENTED_NOTES = {
    AttackType.OVERFITTING: "Needs a multi-model train/test comparison harness; not yet implemented.",
    AttackType.REGIME_DEPENDENCY: "Needs labeled multi-regime historical data; not yet implemented.",
    AttackType.OUT_OF_SAMPLE_DEGRADATION: "Needs a live monitoring history to compare against; not yet implemented.",
}


def _provenance(attack_name: str, hypothesis: Hypothesis) -> Provenance:
    return Provenance(
        produced_by=attack_name,
        produced_at=datetime.now(),
        inputs=[ProvenanceRef(kind="hypothesis", ref_id=hypothesis.id, ref_version=hypothesis.version)],
    )


class AdversarialScientist:
    def __init__(
        self,
        *,
        min_sample_size: int = 30,
        min_rationale_length: int = 20,
        permutation_iterations: int = 500,
        permutation_seed: int = 42,
        permutation_alpha: float = 0.05,
    ):
        self.min_sample_size = min_sample_size
        self.min_rationale_length = min_rationale_length
        self.permutation_iterations = permutation_iterations
        self.permutation_seed = permutation_seed
        self.permutation_alpha = permutation_alpha

    def attack(
        self,
        hypothesis: Hypothesis,
        experiment_results: dict[str, ExperimentResult],
        snapshot: DatasetSnapshot,
        *,
        economic_rationale: str | None = None,
    ) -> list[AttackResult]:
        results = [
            self._attack_small_sample_bias(hypothesis, experiment_results),
            self._attack_time_leakage(hypothesis, snapshot),
            self._attack_look_ahead_bias(hypothesis, snapshot),
            self._attack_weak_economic_rationale(hypothesis, economic_rationale),
            self._attack_random_coincidence(hypothesis, snapshot),
            self._attack_parameter_instability(hypothesis, snapshot),
        ]
        for attack_type in _UNIMPLEMENTED_ATTACKS:
            results.append(
                AttackResult(
                    attack_type=attack_type,
                    attempted=False,
                    succeeded=False,
                    confidence_delta=0.0,
                    notes=_UNIMPLEMENTED_NOTES[attack_type],
                    provenance=_provenance("AdversarialScientist", hypothesis),
                )
            )
        return results

    def _attack_small_sample_bias(
        self, hypothesis: Hypothesis, experiment_results: dict[str, ExperimentResult]
    ) -> AttackResult:
        if not experiment_results:
            return AttackResult(
                attack_type=AttackType.SMALL_SAMPLE_BIAS,
                attempted=True,
                succeeded=True,
                confidence_delta=-0.2,
                notes="No experiment results available to check sample size against.",
                provenance=_provenance("AdversarialScientist.small_sample_bias", hypothesis),
            )
        smallest = min(r.sample_size for r in experiment_results.values())
        succeeded = smallest < self.min_sample_size
        return AttackResult(
            attack_type=AttackType.SMALL_SAMPLE_BIAS,
            attempted=True,
            succeeded=succeeded,
            confidence_delta=-0.2 if succeeded else 0.0,
            notes=(
                f"Smallest experiment sample size ({smallest}) is below the "
                f"{self.min_sample_size} threshold."
                if succeeded
                else f"Smallest experiment sample size ({smallest}) clears the threshold."
            ),
            provenance=_provenance("AdversarialScientist.small_sample_bias", hypothesis),
        )

    def _attack_time_leakage(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> AttackResult:
        leaked = hypothesis.created_at > snapshot.as_of
        return AttackResult(
            attack_type=AttackType.TIME_LEAKAGE,
            attempted=True,
            succeeded=leaked,
            confidence_delta=-0.3 if leaked else 0.0,
            notes=(
                f"Hypothesis created_at ({hypothesis.created_at}) is after the dataset "
                f"snapshot's as_of ({snapshot.as_of}) -- it could not have been discovered "
                "from this snapshot alone."
                if leaked
                else "Hypothesis created_at is on or before the snapshot's as_of."
            ),
            provenance=_provenance("AdversarialScientist.time_leakage", hypothesis),
        )

    def _attack_look_ahead_bias(self, hypothesis: Hypothesis, snapshot: DatasetSnapshot) -> AttackResult:
        """Audits the snapshot itself for the point-in-time guarantee `build_snapshot`
        is supposed to enforce, rather than trusting it blindly -- defense in depth,
        distinct from `_attack_time_leakage`'s check of the hypothesis's own dates.
        """
        violations: list[str] = []
        for ticker, bars in snapshot.price_history.items():
            violations += [f"{ticker}@{bar.trade_date}" for bar in bars if bar.trade_date > snapshot.as_of]
        for ticker, events in snapshot.corporate_events.items():
            violations += [
                f"{ticker} corporate_event@{event.event_date}"
                for event in events
                if event.event_date > snapshot.as_of
            ]
        for series_id, observations in snapshot.macro_series.items():
            violations += [
                f"{series_id}@{observation.observation_date}"
                for observation in observations
                if observation.observation_date > snapshot.as_of
            ]
        violations += [
            f"news@{item.published_at}" for item in snapshot.news if item.published_at > snapshot.as_of
        ]

        succeeded = bool(violations)
        return AttackResult(
            attack_type=AttackType.LOOK_AHEAD_BIAS,
            attempted=True,
            succeeded=succeeded,
            confidence_delta=-0.3 if succeeded else 0.0,
            notes=(
                f"Found {len(violations)} record(s) in the snapshot dated after its as_of "
                f"({snapshot.as_of}): {violations[:5]}"
                if succeeded
                else "No records in the snapshot are dated after its as_of."
            ),
            provenance=_provenance("AdversarialScientist.look_ahead_bias", hypothesis),
        )

    def _attack_weak_economic_rationale(
        self, hypothesis: Hypothesis, economic_rationale: str | None
    ) -> AttackResult:
        rationale_text = (economic_rationale or "").strip()
        weak = len(rationale_text) < self.min_rationale_length
        return AttackResult(
            attack_type=AttackType.WEAK_ECONOMIC_RATIONALE,
            attempted=True,
            succeeded=weak,
            confidence_delta=-0.15 if weak else 0.0,
            notes=(
                f"No economic rationale (or one shorter than {self.min_rationale_length} "
                "characters) was provided."
                if weak
                else f"A rationale of {len(rationale_text)} characters was provided "
                "(not evaluated here for correctness -- see EconomistReviewer)."
            ),
            provenance=_provenance("AdversarialScientist.weak_economic_rationale", hypothesis),
        )


    def _attack_random_coincidence(
        self, hypothesis: Hypothesis, snapshot: DatasetSnapshot
    ) -> AttackResult:
        """Seeded permutation test: shuffle away the claimed structure and see
        whether the observed statistic is actually unusual against that null."""
        import random as _random

        from agx_research.hypotheses.statistic import hypothesis_statistic, series_for_hypothesis

        try:
            series = series_for_hypothesis(hypothesis, snapshot)
            observed = hypothesis_statistic(series)
        except ValueError as exc:
            observed, series = None, None
            failure_note = f"Statistic could not be computed: {exc}"
        if observed is None:
            return AttackResult(
                attack_type=AttackType.RANDOM_COINCIDENCE,
                attempted=True,
                succeeded=True,
                confidence_delta=-0.2,
                notes=(
                    failure_note
                    if series is None
                    else "Statistic undefined on this snapshot."
                ),
                provenance=_provenance("AdversarialScientist.random_coincidence", hypothesis),
            )

        rng = _random.Random(self.permutation_seed)
        exceed = 0
        for _ in range(self.permutation_iterations):
            if len(series) == 2:
                shuffled = list(series[1])
                rng.shuffle(shuffled)
                permuted = hypothesis_statistic([series[0], shuffled])
            else:
                # Single-asset drift claim: the null randomizes each return's sign.
                permuted = hypothesis_statistic(
                    [[r * rng.choice((-1.0, 1.0)) for r in series[0]]]
                )
            if permuted is not None and abs(permuted) >= abs(observed):
                exceed += 1
        empirical_p = exceed / self.permutation_iterations
        succeeded = empirical_p > self.permutation_alpha
        return AttackResult(
            attack_type=AttackType.RANDOM_COINCIDENCE,
            attempted=True,
            succeeded=succeeded,
            confidence_delta=-0.2 if succeeded else 0.0,
            notes=(
                f"Permutation test ({self.permutation_iterations} shuffles, seed "
                f"{self.permutation_seed}): empirical p={empirical_p:.4f} "
                f"{'>' if succeeded else '<='} alpha={self.permutation_alpha} -- the observed "
                f"statistic {'is consistent with' if succeeded else 'is unlikely under'} "
                "pure chance."
            ),
            provenance=_provenance("AdversarialScientist.random_coincidence", hypothesis),
        )

    def _attack_parameter_instability(
        self, hypothesis: Hypothesis, snapshot: DatasetSnapshot
    ) -> AttackResult:
        """Does the claim's statistic keep its sign as the estimation window varies?"""
        from agx_research.hypotheses.statistic import (
            hypothesis_statistic,
            series_for_hypothesis,
            slice_series,
        )

        try:
            series = series_for_hypothesis(hypothesis, snapshot)
            full_value = hypothesis_statistic(series)
        except ValueError as exc:
            return AttackResult(
                attack_type=AttackType.PARAMETER_INSTABILITY,
                attempted=True,
                succeeded=True,
                confidence_delta=-0.15,
                notes=f"Statistic could not be computed: {exc}",
                provenance=_provenance("AdversarialScientist.parameter_instability", hypothesis),
            )
        n = len(series[0])
        if full_value is None or n < 6:
            return AttackResult(
                attack_type=AttackType.PARAMETER_INSTABILITY,
                attempted=True,
                succeeded=True,
                confidence_delta=-0.15,
                notes="Too little data to assess stability; instability assumed, not excused.",
                provenance=_provenance("AdversarialScientist.parameter_instability", hypothesis),
            )

        flips = 0
        settings = 0
        for fraction in (0.5, 0.66, 0.83):
            window = max(3, int(n * fraction))
            value = hypothesis_statistic(slice_series(series, n - window, n))
            if value is None:
                continue
            settings += 1
            if (value <= 0) != (full_value <= 0):
                flips += 1
        succeeded = settings == 0 or flips > 0
        return AttackResult(
            attack_type=AttackType.PARAMETER_INSTABILITY,
            attempted=True,
            succeeded=succeeded,
            confidence_delta=-0.15 if succeeded else 0.0,
            notes=(
                f"Statistic sign flipped in {flips}/{settings} trailing-window settings."
                if settings
                else "No alternative window produced a valid statistic."
            ),
            provenance=_provenance("AdversarialScientist.parameter_instability", hypothesis),
        )


def apply_adversarial_review(confidence: float, attack_results: list[AttackResult]) -> float:
    """Apply only evidence-backed penalties; clean checks are confidence-neutral."""
    adjusted = confidence + sum(result.confidence_delta for result in attack_results)
    return max(0.0, min(1.0, adjusted))
