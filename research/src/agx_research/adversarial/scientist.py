"""The Adversarial Scientist: its sole purpose is to try to invalidate discoveries.

Three attacks are real and mechanical: `SmallSampleBias`, `TimeLeakage`/
`LookAheadBias`, and `WeakEconomicRationale` (which delegates to the
Phase 7 `EconomicRationaleGate`). The remaining five
(`RandomCoincidence`, `Overfitting`, `ParameterInstability`,
`RegimeDependency`, `OutOfSampleDegradation`) each need either a
permutation-test harness or multi-regime historical data this scaffold
doesn't have yet — `attack()` still reports all nine attack types, marking
the unimplemented ones `attempted=False` rather than omitting them or
faking a result.

Successful attacks (a real problem found) reduce confidence; failed
attacks (the check ran and found nothing) strengthen it slightly.
Unattempted attacks contribute nothing either way.
"""

from __future__ import annotations

from datetime import datetime

from agx_research.adversarial.attacks import AttackResult, AttackType
from agx_research.data.snapshot import DatasetSnapshot
from agx_research.domain.provenance import Provenance, ProvenanceRef
from agx_research.hypotheses.experiment import ExperimentResult
from agx_research.hypotheses.hypothesis import Hypothesis

_UNIMPLEMENTED_ATTACKS = (
    AttackType.RANDOM_COINCIDENCE,
    AttackType.OVERFITTING,
    AttackType.PARAMETER_INSTABILITY,
    AttackType.REGIME_DEPENDENCY,
    AttackType.OUT_OF_SAMPLE_DEGRADATION,
)

_UNIMPLEMENTED_NOTES = {
    AttackType.RANDOM_COINCIDENCE: "Needs a permutation-test harness; not yet implemented.",
    AttackType.OVERFITTING: "Needs a train/test split harness across multiple features; not yet implemented.",
    AttackType.PARAMETER_INSTABILITY: "Needs multiple parameter configurations to compare; not yet implemented.",
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
    def __init__(self, *, min_sample_size: int = 30, min_rationale_length: int = 20):
        self.min_sample_size = min_sample_size
        self.min_rationale_length = min_rationale_length

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
            confidence_delta=-0.2 if succeeded else 0.02,
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
            confidence_delta=-0.3 if leaked else 0.02,
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
            confidence_delta=-0.3 if succeeded else 0.02,
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
            confidence_delta=-0.15 if weak else 0.02,
            notes=(
                f"No economic rationale (or one shorter than {self.min_rationale_length} "
                "characters) was provided."
                if weak
                else f"A rationale of {len(rationale_text)} characters was provided "
                "(not evaluated here for correctness -- see EconomistReviewer)."
            ),
            provenance=_provenance("AdversarialScientist.weak_economic_rationale", hypothesis),
        )


def apply_adversarial_review(confidence: float, attack_results: list[AttackResult]) -> float:
    """Successful attacks reduce confidence; failed (attempted) attacks strengthen it slightly."""
    adjusted = confidence + sum(result.confidence_delta for result in attack_results)
    return max(0.0, min(1.0, adjusted))
