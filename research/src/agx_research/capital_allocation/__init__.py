"""Capital Allocation Intelligence: the platform stops scoring stocks in
isolation and starts allocating one shared, finite capital budget across
every competing opportunity at once.

Deliberately its own package, composing `decision_service.DecisionService`
rather than duplicating it -- `DecisionService.decide_portfolio()` already
evaluates the *entire* INVESTMENT-horizon universe (every ticker with a
`Recommendation`, unioned with every currently held ticker) in one jointly
normalized pass; this package's only job is to make that existing
competition explicit and legible: a global ranking, a capital deployment
queue, an opportunity-cost narrative, and a capital-recycling ledger
(which released position funded which new one, or cash). It reads
`PositionAwareDecision` only -- ticker/opportunity-score/target-weight/
current-weight is all it ever needs -- so it never re-derives the
eligibility or scoring rule `DecisionService` already owns.

Same architectural posture as `decision_service/` (see that package's own
docstring): stateless-per-call, queried on demand, never wired into
`production.pipeline.ProductionPipeline` -- a capital allocation plan is
meaningless without the investor's own real `PositionState` (there is
nothing to "release" or "recycle" without a real holding to release it
from), so it inherits the exact same on-demand-only constraint
`decision_service` already has, not a new one.
"""

from __future__ import annotations

from agx_research.capital_allocation.engine import CapitalAllocationEngine
from agx_research.capital_allocation.models import (
    AllocationChange,
    CapitalAllocationPlan,
    CapitalFlow,
    CapitalQueueEntry,
    CapitalRelease,
    CapitalSource,
    CashWaiting,
    OpportunityCostHighlight,
    RankedOpportunity,
)

__all__ = [
    "AllocationChange",
    "CapitalAllocationEngine",
    "CapitalAllocationPlan",
    "CapitalFlow",
    "CapitalQueueEntry",
    "CapitalRelease",
    "CapitalSource",
    "CashWaiting",
    "OpportunityCostHighlight",
    "RankedOpportunity",
]
