"""Ranking and selection: turn a discovered method's three independent
assessments into one ordering, and pick the best.

Legality is a hard gate, never a weighted-down score -- an `AMBIGUOUS` or
`BLOCKED` method is excluded from ranking entirely, exactly like the seed
catalog's `TOS_REVIEW`/`NEEDS_KEY` sources are catalogued but never
collected. Among methods that clear the gate, the composite is the mean of
stability and historical-availability scores; a method with
`insufficient_data`/no snapshots still ranks (a candidate is better than no
candidate), just lower.
"""

from __future__ import annotations

from dataclasses import dataclass

from agx_research.acquisition_intelligence.historical import HistoricalAvailabilityAssessment
from agx_research.acquisition_intelligence.legality import LegalityAssessment, LegalityVerdict
from agx_research.acquisition_intelligence.stability import StabilityAssessment
from agx_research.discovery.candidate import SourceCandidate


@dataclass
class RankedMethod:
    candidate: SourceCandidate
    legality: LegalityAssessment
    stability: StabilityAssessment
    historical: HistoricalAvailabilityAssessment
    composite_score: float


def _composite(stability: StabilityAssessment, historical: HistoricalAvailabilityAssessment) -> float:
    return (stability.score + historical.score) / 2


def rank_methods(
    entries: list[tuple[SourceCandidate, LegalityAssessment, StabilityAssessment, HistoricalAvailabilityAssessment]],
) -> list[RankedMethod]:
    ranked = [
        RankedMethod(
            candidate=candidate, legality=legality, stability=stability, historical=historical,
            composite_score=_composite(stability, historical),
        )
        for candidate, legality, stability, historical in entries
        if legality.verdict == LegalityVerdict.ALLOWED
    ]
    return sorted(ranked, key=lambda r: r.composite_score, reverse=True)


def select_best(ranked: list[RankedMethod]) -> RankedMethod | None:
    return ranked[0] if ranked else None
