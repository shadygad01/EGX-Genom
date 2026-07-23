# AGX Architecture Audit (pre-implementation freeze)

Performed before any feature work landed on top of the foundation scaffold,
against `docs/VISION.md`'s eight principles and knowledge/agent philosophy.
Each finding names the file(s), the principle it threatens, why it's a
bottleneck specifically (not just "could be nicer"), and the resolution
applied in this refactor. Findings are grouped by theme. See
`docs/ARCHITECTURE.md` for the resulting design.

## 1. Versioning covered one entity out of seven

Principle 5 requires **Patterns, Features, Models, Knowledge, Experiments,
Predictions, and Datasets** to all be versioned. The scaffold only
versioned Knowledge (`knowledge/store.py`). Hypotheses, features, dataset
pulls, model artifacts, and predictions had no identity, no version, and in
several cases no persistence at all — a `Hypothesis` lived only in whatever
Python variable held it; a rejected hypothesis simply vanished once its
frame exited, meaning the same negative result could be rediscovered (and
re-spend research effort on) indefinitely, undermining Principle 7's
"continuous learning."

**Bottleneck if left alone:** every one of these entity types would need
its own bespoke persistence layer bolted on later, each with slightly
different (and by then, inconsistent) semantics — exactly the kind of
piecemeal retrofit that becomes a rewrite instead of an addition.

**Resolution:** extracted the versioned-append-only persistence mechanics
that `KnowledgeStore` already had into a generic `storage.Repository[T]` /
`storage.JsonFileRepository[T]` (`research/src/agx_research/storage/`).
`KnowledgeStore` now composes one; a new `HypothesisRepository` uses the
same base and persists every hypothesis regardless of outcome. Adding a
repository for predictions, features, or dataset snapshots later is adding
a one-line subclass, not new plumbing.

## 2. The validation pipeline was a hardcoded enum, not data

`hypotheses/hypothesis.py` encoded the Observation → ... → Peer Validation
sequence as a fixed `IntEnum` with `+1` progression logic baked into
`Hypothesis.advance()`. Principle 2 requires validation before promotion,
but nothing says every hypothesis track needs the *same* gates: Micro Alpha
screening plausibly wants a cheaper pipeline than Investment Alpha, and new
gate types (e.g. a regime-robustness check) are a near-certain future
addition given the vision's emphasis on stress testing markets as a "living
network."

**Bottleneck if left alone:** adding, reordering, or branching gates would
mean editing the enum, the progression logic, and every call site
referencing specific stage names — a coupled, global change for what should
be a per-hypothesis-track configuration decision.

**Resolution:** replaced the enum with `hypotheses/pipeline.py`: a
`GateSpec(name, order)` list is now data, not code. `StageName` still gives
a default, readable vocabulary, but `Hypothesis.pipeline` can be any
sequence of named gates. `Hypothesis.advance()` walks `pipeline` generically
by index. A test (`test_hypothesis_lifecycle.py`) constructs a hypothesis
with a custom 3-gate pipeline to prove this isn't decorative.

## 3. KnowledgeStore was nominally coupled to the concrete Hypothesis class

`KnowledgeStore.promote()` imported `Hypothesis` directly and read its
internal fields. Principle 6 ("AI proposes, evidence approves") means the
promotion gate is one of the most important pieces of business logic in
the system — but as written, only literal `Hypothesis` instances could ever
be promoted, foreclosing future evidence sources (e.g. a meta-hypothesis
synthesizing several prior hypotheses, or a human-curated research note)
that satisfy the same "passed peer validation" contract without being that
exact class.

**Resolution:** `knowledge/store.py` now defines the dependency it actually
needs as a structural `Protocol` (`PromotableEvidence`: id, version,
created_by, created_at, horizon, affected_assets, is_ready_for_promotion,
current_stage_name). `Hypothesis` satisfies it structurally; `knowledge/`
no longer imports `hypotheses/` at all. Any future evidence type can be
promoted by shape, not by inheritance.

## 4. No point-in-time dataset concept — a classic, expensive-to-retrofit gap

`agents/market_structure.py` (the one working agent) called
`data_provider.get_price_history(...)` directly with a caller-chosen date
range. Nothing prevented an agent or experiment from being re-run later
against revised/extended data and silently getting a different answer, and
nothing captured *which* data a finding or experiment actually saw. This
directly undermines Principle 5's "Datasets" versioning and is a well-known
failure mode in quant research systems: retrofitting point-in-time
correctness after a data layer is already load-bearing typically requires
rewriting every consumer.

**Resolution — done now, while it's nearly free:** added
`data/snapshot.py`: `DatasetSnapshot` is an immutable, content-hashed bundle
(price history, corporate events, macro series, news) for a fixed
`as_of` + lookback window; `build_snapshot()` materializes one from any
`DataProvider`. `ResearchAgent.research()` and `Experiment.run()` /
`StressTester.run()` / `Backtester.run()` now take a `DatasetSnapshot`
instead of a live `DataProvider` + date range. Since no concrete
`Experiment`/`StressTester`/`Backtester` existed yet, this cost nothing to
change today; it would have cost a rewrite of every experiment once they
existed.

## 5. "Features" (Principle 5) didn't exist as a concept at all

The correlation math in `MarketStructureAgent` was inline arithmetic with
no identity — not reusable by other agents, not versioned, not traceable.
Principle 5 explicitly names Features as a versioned entity distinct from
raw data and models.

**Resolution:** added `features/` — `FeatureDefinition` (id, version, name,
description, inputs) and a `FeatureRegistry`. Pulled the correlation
computation out into `features/correlation.py` as a registered
`pairwise_return_correlation` feature and made `MarketStructureAgent`
consume it instead of inlining the math, so the abstraction is load-bearing
in the one place that currently needs it, not speculative.

## 6. No provenance/lineage chain — explainability was prose, not evidence

Principle 3 forbids black-box predictions, and the vision's explainability
section demands concrete answers ("what evidence," "what historical
cases"). The original `Explanation` object was free-text fields with no
structured link back to the data/features/knowledge that justified it —
fine for a demo, but it doesn't scale: at real volume nobody can audit "why
this stock" from prose alone.

**Resolution:** added `domain/provenance.py` (`ProvenanceRef`, `Provenance`)
and threaded it through the objects that are actually persisted with
identity: `ResearchFinding` → `Hypothesis` → `KnowledgeObject` →
`Prediction` / `Recommendation`. Each links to its input by id (and version
where the input is versioned), so the full chain from a recommendation back
to the dataset snapshot and feature that started it is walkable via
repository lookups, not just readable as a sentence. Deliberately **not**
added to transient value objects (`ExperimentResult`, `ValidationResult`,
`StressTestResult`, `BacktestResult`) — those are computation outputs, not
identified entities, and forcing provenance onto every return value would
be ceremony without benefit. Only entities with their own lifecycle and
persistence carry it.

## 7. Nothing represented "a trading day's research," despite it being the Core Mission

"Every trading day the platform must answer one question" is the mission
statement, yet there was no object corresponding to a research run —
no way to say which agents (at which versions) ran, against which dataset
snapshot, on a given day.

**Resolution:** added `orchestration/` — `ResearchCycle` (id, run date,
dataset snapshot id, agent versions, findings, timing) and a
`ResearchOrchestrator` that builds a snapshot and runs every registered
agent against it. This is intentionally the smallest useful version: no
scheduling, no retries, no parallelism — those are real future needs but
adding them later means extending this object, not inventing it from
scratch under pressure.

## 8. Volatile placeholder data was mixed into a stable domain module

`config.py` held both `Horizon` (a stable domain concept, needed
everywhere) and `EGX30_UNIVERSE_PLACEHOLDER` (an explicitly-temporary
static dict that a real, likely dynamic, EGX30 membership feed will
replace wholesale). Every future change to how the universe is sourced
would touch a file that dozens of unrelated modules import `Horizon` from.

**Resolution:** moved universe handling to `universe/` with a
`UniverseProvider` interface (mirroring `DataProvider`) and a
`StaticUniverseProvider` wrapping today's placeholder dict.  `config.py`
now holds only `Horizon`/`HORIZON_WINDOWS`.

## 9. Statistical strength was an untyped float

`KnowledgeObject.statistical_strength: float` carried no record of what was
actually measured (p-value? test statistic? effect size?) or by what
method — directly weakening Principle 2's "no pattern enters production
before statistical validation": validation should be auditable, not a bare
number.

**Resolution:** added `StatisticalEvidence` (method, statistic, p_value,
sample_size, optional confidence interval) in `validation/statistical.py`;
`KnowledgeObject.statistical_evidence` replaces the float.

## 10. Model and prediction versioning were absent

`HorizonModel`/`Prediction` had no `model_id`/`model_version`. Since Micro,
Swing, and Investment Alpha are independent models that will each go
through their own training/retraining cycles, predictions need to record
exactly which model artifact produced them — otherwise a monitoring/
retirement decision (Principle 4) can't tell whether a degrading result
came from the same model or a since-replaced one.

**Resolution:** `HorizonModel` now declares `model_id`/`model_version`
class attributes; `Prediction` carries them plus a `provenance` field. No
concrete `HorizonModel` existed yet, so this was a zero-migration-cost
change — exactly the kind of fix that gets expensive once real models ship.

## Deferred (named, not silently dropped)

- **Real database backend.** The repository abstraction (finding #1) is the
  actual fix; swapping `JsonFileRepository` for a Postgres/Timescale-backed
  one later is now additive. Building that backend now, with no real data
  volume yet, would be premature.
- **Full schema codegen for `api/`/`web/` TypeScript types.** The
  hand-maintained TS mirrors of the pydantic schemas (`api/src/types.ts`,
  `web/src/types.ts`) are a known long-term drift risk. Full codegen
  tooling is more investment than today's three types justify; instead
  `research/scripts/export_schemas.py` emits JSON Schema into `contracts/`
  and CI regenerates it, so a schema change that isn't reflected in the
  committed contract fails CI — a cheap tripwire now, with the door open to
  swap in real codegen once the schema surface grows.
- **Orchestration scheduling, retries, distributed execution.** Out of
  scope until there's more than one agent worth parallelizing.
- **API authentication.** Still irrelevant until the API is reachable
  beyond local development.
