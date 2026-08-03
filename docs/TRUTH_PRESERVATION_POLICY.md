# Truth Preservation Policy

Permanent engineering policy, not a bug fix. Adopted as `AD-60` (see
`ARCHITECTURE_DECISIONS.md`) after commit `06a6882` reintroduced fabricated
financial/valuation/status data one subsystem over from where an earlier
commit the same session (`f78d3ab`) had just removed it — proof that a
one-off cleanup does not stay fixed unless the architecture itself makes
regressing structurally harder than doing the right thing. See
`CHANGELOG.md`'s "Revert fabrication reintroduced by the 100%-coverage/
zero-gap-banner push" entry for the full incident.

This document is permanent governing law for this codebase, same standing
as `docs/INVESTMENT_CONSTITUTION.md` and the other doctrine documents
`CLAUDE.md` names. It is amended, never silently drifted from.

## First principle

Investment systems must always prefer **UNKNOWN over WRONG**.

Missing information is acceptable. Fabricated information is never
acceptable. The platform fails closed: when a real computation cannot be
performed, the honest output is "no value" (`None`, an empty list, a
raised `LiveDecisionsUnavailableError`, `abstained=True`) — never a
plausible-looking substitute.

This restates, and makes permanent, a principle `CLAUDE.md` already states
in several places ("Do not fake a result...", "no downstream system may
ignore data quality... enforced by withholding, not by passing degraded
data through"). What's new here is the enforcement layer: a regression
suite and static analysis that make violating it fail CI, not just fail
code review.

## Zero fabrication policy

The following are permanently prohibited, anywhere in this codebase:

**1. Inventing numerical values.** Example (the actual `06a6882` bug):
`fair_value = current_price` when a real fair value is unavailable. A
missing fair value must stay missing (`FairValueEngine.value()` returns
`None`; `DecisionReadiness.fair_value_available` stays `False`).

**2. Returning synthetic valuation metrics.** A `graham_number`,
`intrinsic_value`, sector "anchor," or DCF output must never appear unless
it was computed from real, validated line items by
`valuation.engine.FairValueEngine`. `len(candidates) < 3` (or `< 3` after
the outlier-median filter) means `None`, not a synthesized fourth
candidate.

**3. Replacing UNKNOWN with CONNECTED.** A source's status string may
never claim "connected," "operational," "verified," "active," or
"healthy" unless that claim is backed by the real enum value it was
derived from (see Status Integrity below). Rewriting an honest
`"Endpoint not yet verified against a real fetch"` into
`"Active free public feed connected and operational"` — the actual
`06a6882` regression — is exactly what this rule forbids, independent of
whether the underlying `SourceStatus` changed.

**4. Replacing production logic with UI heuristics.** The frontend
(`web/`, `api/`) must never recreate an investment decision. It renders
artifacts `research/` already produced; it does not compute
`target_weight`, `action`, `confidence`, or `expected_return` itself.
`StaticJsonProvider.postDecisions()`/`postCapitalAllocation()` reimplementing
`decide_portfolio()` as a client-side if/else bucket engine (`b0f6dea`/
`53bc59a`) is the actual regression this forbids — it is also, independently,
exactly the "discrete lookup table over signal-strength buckets" pattern
`CLAUDE.md`'s `decision_service/` section already documents as "tried and
rejected under adversarial review for combinatorial-growth risk."

**5. Silently masking failures.** Errors may be explained (a reason
string, a `blocker`, an `abstained=True` with `reasons`). They may never
just disappear from the surface that would otherwise show them. Deleting
or rewording a "needs a live backend" / "not yet verified" banner so the
gap looks closed, without actually closing it, is a Rule 5 violation even
if no number was literally invented.

## Architectural invariants

**Invariant 1 — Unknown data must remain unknown.** A missing input
propagates as `None`/absence through every layer that touches it, all the
way to the rendered surface. No layer may default it to a placeholder
"reasonable" value on its way through.

**Invariant 2 — Unavailable data must never be replaced.** Not with a
sibling metric, not with a market price, not with a sector average, not
with the previous day's value. "Unavailable" is a terminal state for that
computation on that day, not a trigger to substitute.

**Invariant 3 — Every displayed value must have provenance.** Every
persisted, displayed entity carries `domain.provenance.Provenance`
(`produced_by`, `produced_at`, `inputs: list[ProvenanceRef]`) — the
mechanism already exists (`Recommendation.provenance`, `KnowledgeObject`,
`Hypothesis`, etc. per `CLAUDE.md`'s Provenance principle); this invariant
makes it non-optional rather than a convention. A value with no
`Provenance` it can point to must not be published to a dashboard
artifact.

**Invariant 4 — Every recommendation must be traceable.** A
`Recommendation`'s `explanation.evidence_refs` and `provenance.inputs`
must resolve to real, persisted entities (a `KnowledgeObject`, a
`Hypothesis`, a `FinancialStatementLineItem`) — never an empty list
papering over "there wasn't really any evidence."

**Invariant 5 — Every confidence score must have evidence.** A
`confidence` value is only ever the output of
`explainability`/`meta.decision_quality`'s real calculation over real
inputs. A hardcoded default (`confidence ?? 0.6`, the actual `b0f6dea`
bug) is forbidden regardless of how reasonable the number looks.

**Invariant 6 — Every status must originate from real execution, never
from UI assumptions.** See Status Integrity below for exactly which enums
this covers.

## Status integrity

This codebase already has four narrow, real status enums, each owned by
the layer that actually observes the thing it describes — deliberately
not unified into one flat enum, because catalog readiness, collection
health, activation, and pipeline-stage execution are different facts with
different owners:

| Concept | Enum | Owner | Values |
|---|---|---|---|
| Is this source catalogued/collectable at all? | `sources.spec.SourceStatus` | the registry, set by legal/config review | `implemented`, `planned`, `needs_key`, `tos_review`, `disabled` |
| Did the last real collection run succeed? | `sources.spec.HealthStatus` | `sources.health.HealthMonitor`, from actual fetch outcomes | `unknown`, `healthy`, `degraded`, `down` |
| Is scheduled collection switched on? | `sources.spec.ActivationStatus` | operator action | `active`, `paused`, `retired` |
| Did a production pipeline stage complete? | `production.stages.StageStatus` | `ProductionPipeline.execute()`, from actual stage outcomes | `succeeded`, `partial`, `failed`, `skipped` |

A status string displayed anywhere must be derived from one of these four
enums' actual current value — never a free-text string authored to make a
UI section look complete. `_NOT_READY_REASON_BY_STATUS` /
`_UNAVAILABLE_REASON_BY_STATUS` (in `acquisition_intelligence
.capability_engine` and `production.collector_plan`) exist specifically to
explain a non-`IMPLEMENTED` `SourceStatus` honestly; none of their values
may contain "operational," "connected," "active," "verified," "healthy,"
or "reachable" language, because every key in those dicts is, by
construction, a status that is *not* ready. `check_truth_preservation.py`
enforces this by importing the dicts directly (see Static Analysis).

## Decision integrity

Investment recommendations may only originate from:

- `agx_research.meta.decision_engine` (`DecisionAction`: `buy_candidate`,
  `watch`, `avoid`, `abstain` — research-only labels), and
- `agx_research.decision_service.DecisionService.decide_portfolio()`
  (`PositionAction`: `buy`, `increase_position`, `hold`,
  `reduce_position`, `exit`, `no_action`, plus `abstained=True`) —
  position-aware, on-demand only, per `CLAUDE.md`'s `decision_service/`
  section.

No other component — no page, no provider, no API route — may construct
one of these action labels. The frontend (`web/src`, `api/src`) reads a
`PositionAction`/`DecisionAction` off an already-computed artifact or API
response; it never assigns one to a variable itself outside a type
declaration (`types.ts`'s `PositionAction`/`DecisionAction` unions) or a
UI display-mapping table keyed by the value it received (e.g.
`ACTION_VARIANT` in `Portfolio.tsx`, which maps an already-decided action
to a badge color and constructs nothing).

## Truth regression suite

`research/tests/test_truth_preservation.py` and
`web/test/truthPreservation.test.ts` are permanent. Every future PR must
keep them green, meaning:

- Missing fair value stays missing (`FairValueEngine.value()` returns
  `None` below the 3-real-model threshold; no synthetic candidate is ever
  added to reach it).
- Unavailable source stays unavailable (no reason string in either
  reason-by-status map claims live/operational/verified language).
- No valuation means no valuation (`assess_decision_readiness` never
  constructs a `FairValueResult` from a market price).
- No confidence means no confidence (`StaticJsonProvider` never fabricates
  one; it fails closed with `LiveDecisionsUnavailableError`).
- No recommendation means no recommendation (the frontend never
  constructs a `PositionAction`/`DecisionAction`).
- No evidence means no evidence (protected tests asserting the above stay
  present, by name — see Test Protection).

## Static analysis

`research/scripts/check_truth_preservation.py` runs in CI
(`.github/workflows/ci.yml`, research job) and locally via
`test_truth_preservation.py`. It fails the build on:

1. **Exact-phrase denylist** — the literal strings from the actual
   `06a6882` incident (e.g. "Active free public feed connected and
   operational"), repo-wide, so a byte-for-byte regression is caught
   immediately even before any structural check runs.
2. **Reason-dict validation** — imports
   `capability_engine._NOT_READY_REASON_BY_STATUS` and
   `collector_plan._UNAVAILABLE_REASON_BY_STATUS` directly and asserts no
   value contains banned availability language (see Status Integrity).
3. **Fair-value-from-price pattern** — a regex guard in
   `research/src/agx_research/meta/readiness.py` and
   `research/src/agx_research/valuation/engine.py` against assigning a
   `fair_value`/`weighted_fair_value`/`intrinsic_value`-named variable from
   a bar's `.close` (or synthesizing one from a hardcoded hardcoded
   hardcoded constant instead of a real model).
4. **Decision-literal-in-frontend pattern** — a regex guard against
   `action: "buy"` / `action = "sell"` (and siblings) being *assigned* in
   `web/src`/`api/src`, outside `types.ts`'s type declarations and known
   display-mapping tables.
5. **Protected-test existence** — a fixed list of test function names
   (see Test Protection) that must exist in their file; the script fails
   if any is missing, renamed without an equal-or-stronger replacement, or
   its file no longer parses.

Static analysis is a floor, not a ceiling — it catches the literal
regression and known-shape variants of it. It does not replace review
judgment for a genuinely new fabrication pattern; the Pull Request
Checklist below is what covers that.

## Provenance enforcement

Every displayed value must expose, via its `Provenance`:

- **Source** — the originating `SourceSpec`/collector, via
  `ProvenanceRef(kind="source", ...)`.
- **Collector** / **Dataset** — the `CollectionBatch`/`DatasetSnapshot`
  that materialized it.
- **Knowledge Object** — for anything downstream of promoted knowledge.
- **Decision Engine** — `produced_by` names the exact function/class that
  computed the value (e.g. `"decision_service.DecisionService"`, never
  `"client_decision_engine"` — the actual `b0f6dea` regression, since no
  such engine is allowed to exist client-side per Decision Integrity
  above).
- **Generation Timestamp** — `produced_at`.

If a value cannot point to a real `Provenance`, it must not be published
to a dashboard artifact. `dashboard.validate.validate_dashboard_artifacts`
is the enforcement point for this at the artifact-export boundary.

## Test protection

Any PR that removes or weakens a test protecting truthfulness,
provenance, decision integrity, or status integrity must fail review
automatically. This is partially mechanical (the protected-test-name list
in `check_truth_preservation.py` — deleting a protected test without
replacing it with an equal-or-stronger one fails CI) and partially a
review obligation (a test can be technically present but gutted; a
reviewer must treat a diff that weakens assertions inside a protected
test with the same suspicion as deleting it outright — this is exactly
how `53bc59a` passed review the first time: the test was renamed and its
assertion inverted, not deleted, so a naive "does the test still exist"
check would have missed it. Static analysis catches the exact known
regression; it is not a substitute for reading the diff).

Currently protected (grows over time, never shrinks without a replacement
of equal or greater strength):

- `test_fair_value_engine.py::test_engine_refuses_to_fabricate_value_without_share_count`
- `test_decision_readiness.py::test_missing_fundamentals_and_knowledge_force_explicit_abstention`
- `test_capability_engine.py::test_rank_capability_strategies_marks_uncatalogued_source_not_ready`
- `test_capability_engine.py::test_rank_capability_strategies_orders_by_composite_and_marks_ready`
- `test_production_pipeline.py::test_live_mode_collects_real_endpoints_and_reports_unavailable_sources`
- `test_financials.py::test_production_path_never_fabricates_missing_financials`
- `test_runtime_and_intelligence.py::test_fair_value_blends_into_investment_prediction_and_surfaces_as_evidence`
- `test_ticker_data_gap_report.py::test_gap_report_splits_readiness_into_five_named_layers`
- `truthPreservation.test.ts::StaticJsonProvider never fabricates a decision or a capital allocation plan`

## Pull request checklist

Every PR touching `research/src/agx_research/{valuation,meta,financials,
decision_service,capital_allocation,shadow_fund,sources,production,
acquisition_intelligence}`, `web/src/data/`, or `api/src/routes/decisions.ts`
must answer, in the PR description:

1. Did this PR introduce any synthetic value?
2. Did this PR replace UNKNOWN with a substitute?
3. Did this PR infer unavailable information?
4. Did this PR bypass the production decision engine (`DecisionService`/
   `meta.decision_engine`)?
5. Did this PR weaken provenance?
6. Did this PR weaken a truthfulness/status/decision-integrity test?

**If any answer is YES, the PR must not be merged** as-is — the change
must be reworked to fail closed instead, or the reviewer must reject it.
`.github/pull_request_template.md` asks these questions on every PR by
default.

## Definition of done

This mission is complete only when introducing fabricated investment
information is *structurally harder* than correctly reporting missing
information — when the honest path (`return None`, throw
`LiveDecisionsUnavailableError`, leave a reason string alone) is the path
of least resistance, and a fabrication requires deliberately working
around a static-analysis check, a protected test, and a PR checklist
question answered honestly as "yes" to a question that says "must not be
merged."

Truthfulness is an architectural property here, not an implementation
habit — it does not depend on every future contributor (human or agent)
independently remembering `CLAUDE.md`'s prose. It depends on the build
failing when they don't.
