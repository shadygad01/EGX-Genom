"""Decision Service: the position-aware layer between promoted knowledge
and a Buy/Increase/Hold/Reduce/Exit/No Action action.

Deliberately its own package, not a new stage inside
`orchestration.pipeline.DailyResearchPipeline` or
`production.pipeline.ProductionPipeline` (Architecture Adversarial Review
R10): the daily research pipeline's core, tested property is determinism
-- same inputs produce the same output. A position-aware decision depends
on externally supplied `PositionState`, which a real portfolio's holdings
this platform cannot autonomously discover. Folding that into the
autonomous daily pipeline would silently couple two different kinds of
determinism (research reproducibility vs. decision correctness) that need
to stay separate. See `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md` Section
1.10 and Part 3 for the full reasoning.

Every function/class here is stateless-per-call: given the same
`Recommendation`s, `PositionState`s, and country-risk/liquidity inputs,
the same decisions come out, but nothing here is invoked automatically by
a scheduled run -- it is queried on demand, exactly like a portfolio
query legitimately should be.
"""

from __future__ import annotations
