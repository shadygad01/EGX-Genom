# Current Mission

**Implement the first live production collector.**

The prior mission built and proved the first production execution
pipeline (`agx run` → `production.pipeline.ProductionPipeline`): a single
entrypoint that runs the complete chain — Source Registry → Discovery
Engine → Collector Selection → Collector Execution → Raw Archive →
Canonical Transformation → Validation → Event Platform → Market Memory →
Knowledge Base → Research Pipeline → Genome → Investment Case Generator →
Dashboard Artifact Generator → Mission Control Update → Execution Report —
using mock/replay providers standing in for a live collector, exactly as
that mission specified. That pipeline is complete, tested, and is now the
platform's standing production entrypoint (see `docs/PHASE_STATUS.md`'s
"Production Execution Pipeline" section and `docs/ARCHITECTURE_DECISIONS.md`
AD-27–AD-31 for what was decided and why).

## What "first live production collector" means

Swap one of `production/collector_plan.py`'s mock-mode collectors for a
real, `HttpFetcher`-backed one against a verified live endpoint — the
exact same `Collector` subclass, `CollectionService`, and
`ProductionPipeline` wiring already in place, per `AD-28`: "only the data
source changes." This is not new framework work; the framework is done.

**Recommended first candidate: World Bank.** It's already `SourceStatus.
IMPLEMENTED`, uses a stable, free, no-key, decades-old public API (the
same confidence tier as FRED's), and `WorldBankCollector` is already fully
implemented and tested (`test_worldbank_collector.py`). Making it live is
narrowly scoped: give `collector_plan.build_collector_plan` a live-mode
branch that constructs `WorldBankCollector(spec, indicators, fetcher=
HttpFetcher())` instead of a `MockFetcher`, add `ExecutionMode.LIVE` (or
reuse `--mode` with a new value), and prove it end-to-end the same way
`test_production_pipeline.py` already proves mock/replay.

## The one real constraint, stated plainly

This development sandbox has no outbound network egress to arbitrary
hosts (confirmed directly across two prior missions: `curl`/`WebFetch`
both 403 on every real target attempted; only PyPI/npm/anthropic.com are
allowlisted). A live collector run in *this* sandbox will fail to reach
the network — exactly like `agx discover-sources` already does, honestly,
without fabricating a result. The engineering (the collector, the wiring,
the tests against recorded fixtures) can and should be completed here;
the first genuinely live network call happens wherever this runtime is
deployed with egress, or in a sandbox configuration that has it.

## Where things stand otherwise

Every other named next step from the prior mission remains open and
unblocked by this one — see `NEXT_MISSIONS.md`.
