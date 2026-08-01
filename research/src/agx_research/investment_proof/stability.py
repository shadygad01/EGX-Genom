"""Phase 9: Decision Stability.

Verifies that identical evidence always produces identical decisions --
run the same real service call more than once against the same
`KnowledgeStore` and diff the results. `produced_at` timestamps are the
one field expected to differ between runs (audit metadata, not decision
content) and are stripped before comparing; every other field must match
exactly, or the difference is reported, not hidden.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.decision_service.country_risk import CountryRiskAssessment
from agx_research.decision_service.position import PositionState
from agx_research.decision_service.service import DecisionService
from agx_research.knowledge.store import KnowledgeStore
from agx_research.meta.decision_engine import Recommendation
from agx_research.meta.recommendation_service import RecommendationService

_VOLATILE_KEYS = {"produced_at"}


def _strip_volatile(value):
    """Recursively removes `_VOLATILE_KEYS` from a `model_dump(mode='json')`
    tree so a stability comparison judges decision content, never
    audit-trail timestamps that are supposed to change between runs."""
    if isinstance(value, dict):
        return {k: _strip_volatile(v) for k, v in value.items() if k not in _VOLATILE_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


class StabilityResult(BaseModel):
    subject: str
    runs: int
    identical: bool
    differences: list[str] = Field(default_factory=list)


class DecisionStabilityEngine:
    """Real, mechanical determinism proof -- not a claim, a measurement:
    every check here actually calls the real service `runs` times."""

    def verify_recommendation_stability(
        self, knowledge_store: KnowledgeStore, tickers: list[str], as_of: date, *, runs: int = 3
    ) -> StabilityResult:
        service = RecommendationService(knowledge_store)
        snapshots = [
            _strip_volatile(
                {rec.ticker: rec.model_dump(mode="json") for rec in service.recommend(tickers, as_of)}
            )
            for _ in range(runs)
        ]
        return self._compare(f"RecommendationService.recommend({len(tickers)} tickers)", snapshots)

    def verify_portfolio_stability(
        self,
        recommendations: list[Recommendation],
        positions: dict[str, PositionState],
        as_of: date,
        country_risk: CountryRiskAssessment,
        *,
        runs: int = 3,
    ) -> StabilityResult:
        service = DecisionService()
        snapshots = [
            _strip_volatile(
                {
                    d.ticker: d.model_dump(mode="json")
                    for d in service.decide_portfolio(recommendations, positions, as_of, country_risk=country_risk)
                }
            )
            for _ in range(runs)
        ]
        return self._compare(f"DecisionService.decide_portfolio({len(recommendations)} recommendations)", snapshots)

    @staticmethod
    def _compare(subject: str, snapshots: list[dict]) -> StabilityResult:
        baseline = snapshots[0]
        differences: list[str] = []
        for run_index, snapshot in enumerate(snapshots[1:], start=2):
            if snapshot == baseline:
                continue
            keys = set(baseline) | set(snapshot)
            for key in sorted(keys):
                if baseline.get(key) != snapshot.get(key):
                    differences.append(f"run 1 vs run {run_index}, {key!r}: {baseline.get(key)!r} != {snapshot.get(key)!r}")
        return StabilityResult(subject=subject, runs=len(snapshots), identical=not differences, differences=differences)


__all__ = ["DecisionStabilityEngine", "StabilityResult"]
