"""Transaction cost sensitivity sweep (mission Phase 15).

`robustness.py` already gates every candidate on ONE cost assumption
(`DEFAULT_TRANSACTION_COST_BPS = 20.0`, imported and reused here rather
than redeclared) — this module doesn't change that gate, it reports what
happens across SEVERAL cost assumptions for an already-VALIDATED pattern,
so a reader can see gross vs net expectancy at each level and exactly how
much round-trip cost the pattern's own edge can absorb before it
disappears, rather than only knowing whether it cleared one fixed bar.

Reuses `regimes._reconstruct_matched_outcomes()` (the same candidate/
feature_lookup/target reconstruction `engine.py`'s `validate()`/
`final_holdout()` use, including the lead/lag cross-ticker predictor
fix) rather than a third copy of that logic.
"""

from __future__ import annotations

import statistics

from pydantic import BaseModel, Field

from agx_research.patterns.panel import ResearchPanel
from agx_research.patterns.regimes import _reconstruct_matched_outcomes
from agx_research.patterns.registry import Pattern
from agx_research.patterns.robustness import DEFAULT_TRANSACTION_COST_BPS

# A declared, uncalibrated grid spanning "frictionless" to "conservative
# EGX retail" round-trip cost, same posture as every other declared
# threshold in this package (see TD-70) — not derived from a real EGX
# commission/spread/slippage study.
DEFAULT_COST_GRID_BPS: tuple[float, ...] = (0.0, 5.0, 10.0, 20.0, 50.0, 100.0)


class CostLevelResult(BaseModel):
    cost_bps: float
    net_expectancy: float
    net_hit_rate: float
    survives: bool


class TransactionCostSensitivity(BaseModel):
    pattern_id: str
    sample_size: int
    gross_expectancy: float
    gross_hit_rate: float
    levels: list[CostLevelResult] = Field(default_factory=list)
    # The exact round-trip cost (bps) at which net expectancy crosses
    # zero -- a closed form (net is linear in cost_bps), not another grid
    # search; None when the pattern's gross expectancy is already <= 0
    # (there is no cost level, however small, it would have survived).
    breakeven_cost_bps: float | None = None
    survives_default_cost: bool = False


def analyze_transaction_cost_sensitivity(
    pattern: Pattern, panel: ResearchPanel, *, cost_grid_bps: tuple[float, ...] = DEFAULT_COST_GRID_BPS
) -> TransactionCostSensitivity:
    matched = _reconstruct_matched_outcomes(pattern, panel)
    outcomes = [v for _, v in matched]
    if not outcomes:
        return TransactionCostSensitivity(
            pattern_id=pattern.id, sample_size=0, gross_expectancy=0.0, gross_hit_rate=0.0,
        )

    gross_expectancy = statistics.fmean(outcomes)
    gross_hit_rate = sum(1 for o in outcomes if o > 0) / len(outcomes)

    levels: list[CostLevelResult] = []
    for bps in cost_grid_bps:
        cost = bps / 10_000
        net_outcomes = [o - cost for o in outcomes]
        net_expectancy = statistics.fmean(net_outcomes)
        net_hit_rate = sum(1 for o in net_outcomes if o > 0) / len(net_outcomes)
        levels.append(
            CostLevelResult(
                cost_bps=bps, net_expectancy=net_expectancy, net_hit_rate=net_hit_rate,
                survives=net_expectancy > 0,
            )
        )

    breakeven_cost_bps = gross_expectancy * 10_000 if gross_expectancy > 0 else None
    survives_default_cost = (gross_expectancy - DEFAULT_TRANSACTION_COST_BPS / 10_000) > 0

    return TransactionCostSensitivity(
        pattern_id=pattern.id, sample_size=len(outcomes), gross_expectancy=gross_expectancy,
        gross_hit_rate=gross_hit_rate, levels=levels, breakeven_cost_bps=breakeven_cost_bps,
        survives_default_cost=survives_default_cost,
    )


__all__ = [
    "DEFAULT_COST_GRID_BPS",
    "CostLevelResult",
    "TransactionCostSensitivity",
    "analyze_transaction_cost_sensitivity",
]
