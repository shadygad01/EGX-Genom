"""Pattern decay monitoring: flags a validated pattern whose live results
diverge materially from its historical expectancy, moving it to
`WEAKENING` rather than deleting it — the mission is explicit that decay
detection must trigger *revalidation*, never silent removal.

`MIN_LIVE_SAMPLE_FOR_DECAY_CHECK` is a declared, uncalibrated floor (same
posture as every other declared constant in this codebase): too small a
live sample makes "flagged: False" the honest answer, not evidence the
pattern is healthy.
"""

from __future__ import annotations

import statistics
from datetime import date, datetime

from pydantic import BaseModel, Field

from agx_research.patterns.outcomes import OutcomeRepository
from agx_research.patterns.registry import PatternRegistry, PatternStatus

MIN_LIVE_SAMPLE_FOR_DECAY_CHECK = 10
DEFAULT_HIT_RATE_DROP_THRESHOLD = 0.20
DEFAULT_DECAY_HORIZON_FIELD = "actual_20d"


class DecayCheck(BaseModel):
    pattern_id: str
    as_of: date
    live_sample_size: int
    live_hit_rate: float | None = None
    live_expectancy: float | None = None
    historical_hit_rate: float
    historical_expectancy: float
    flagged: bool
    reasons: list[str] = Field(default_factory=list)


class DecayMonitor:
    def __init__(
        self,
        registry: PatternRegistry,
        outcome_repository: OutcomeRepository,
        *,
        min_live_sample: int = MIN_LIVE_SAMPLE_FOR_DECAY_CHECK,
        hit_rate_drop_threshold: float = DEFAULT_HIT_RATE_DROP_THRESHOLD,
        horizon_field: str = DEFAULT_DECAY_HORIZON_FIELD,
    ):
        self.registry = registry
        self.outcome_repository = outcome_repository
        self.min_live_sample = min_live_sample
        self.hit_rate_drop_threshold = hit_rate_drop_threshold
        self.horizon_field = horizon_field

    def check(self, pattern_id: str, *, as_of: date) -> DecayCheck:
        pattern = self.registry.latest(pattern_id)
        if pattern is None:
            raise KeyError(f"No pattern {pattern_id!r} in registry")

        actuals = [
            getattr(outcome, self.horizon_field)
            for outcome in self.outcome_repository.all_latest()
            if outcome.pattern_id == pattern_id and getattr(outcome, self.horizon_field) is not None
        ]

        if len(actuals) < self.min_live_sample:
            return DecayCheck(
                pattern_id=pattern_id,
                as_of=as_of,
                live_sample_size=len(actuals),
                historical_hit_rate=pattern.hit_rate,
                historical_expectancy=pattern.expectancy,
                flagged=False,
                reasons=[
                    f"Live sample ({len(actuals)}) is below the floor "
                    f"({self.min_live_sample}) for a decay judgment; nothing to flag yet."
                ],
            )

        live_hit_rate = sum(1 for a in actuals if a > 0) / len(actuals)
        live_expectancy = statistics.fmean(actuals)
        reasons: list[str] = []
        if live_hit_rate < pattern.hit_rate - self.hit_rate_drop_threshold:
            reasons.append(
                f"Live hit rate {live_hit_rate:.1%} is more than "
                f"{self.hit_rate_drop_threshold:.0%} below the historical {pattern.hit_rate:.1%}."
            )
        if (live_expectancy > 0) != (pattern.expectancy > 0):
            reasons.append(
                f"Live expectancy {live_expectancy:+.4f} has flipped sign vs. the "
                f"historical {pattern.expectancy:+.4f}."
            )
        flagged = bool(reasons)
        if not reasons:
            reasons.append("Live performance remains consistent with historical expectations.")

        check = DecayCheck(
            pattern_id=pattern_id,
            as_of=as_of,
            live_sample_size=len(actuals),
            live_hit_rate=live_hit_rate,
            live_expectancy=live_expectancy,
            historical_hit_rate=pattern.hit_rate,
            historical_expectancy=pattern.expectancy,
            flagged=flagged,
            reasons=reasons,
        )

        if flagged and pattern.validation_status in (PatternStatus.VALIDATED, PatternStatus.ACTIVE):
            self.registry.transition(
                pattern_id,
                PatternStatus.WEAKENING,
                reason="; ".join(reasons),
                validated_at=datetime.combine(as_of, datetime.min.time()),
            )
        return check


__all__ = [
    "DEFAULT_DECAY_HORIZON_FIELD",
    "DEFAULT_HIT_RATE_DROP_THRESHOLD",
    "MIN_LIVE_SAMPLE_FOR_DECAY_CHECK",
    "DecayCheck",
    "DecayMonitor",
]
