# Architecture Decision Record

Compact ledger of load-bearing decisions and their reasoning. Full context
for the early ones lives in `docs/ARCHITECTURE_AUDIT.md` (Epoch I) and
`docs/EPOCH_II_DESIGN.md`; entries here are the ongoing record.

## AD-64 — Artifact Publication Provenance: every published dashboard artifact must prove which pipeline produced it (TD-68)

**Decision.** Four permanent mechanisms, same shape as AD-60's enforcement
set but targeting a distinct failure mode (provenance, not fabricated
content): (1) `agx_research.dashboard.manifest.ArtifactPublicationManifest`
— one manifest written per exported bundle (`manifest.json`, alongside
every other dashboard artifact) recording `generated_at`, `pipeline_mode`
(`live`/`mock`/`replay`), `git_commit`, `workflow_run_id`, `workflow_name`,
`repository`, `generator_version`, `source_data_as_of`, and
`schema_version`; `workflow_run_id`/`workflow_name`/`repository` are only
ever populated from the real `GITHUB_RUN_ID`/`GITHUB_WORKFLOW`/
`GITHUB_REPOSITORY` environment GitHub Actions sets — a local run leaves
them `None` rather than fabricating a workflow identity it doesn't have,
the same "unknown over wrong" discipline `AD-60` already established.
(2) `is_canonical_production()`/the equivalent web
`web/src/lib/provenance.ts:isProductionVerified()` — both true only when
every field matches `CANONICAL_WORKFLOW_NAME` ("Deploy web dashboard to
GitHub Pages") and `CANONICAL_REPOSITORY` ("shadygad01/EGX-Genom") *and*
`workflow_run_id`/`git_commit` are present; partial evidence (a manifest
merely claiming `pipeline_mode: "live"` with no workflow identity behind
it) is not enough. `ProvenanceBanner` renders a specific, honest reason
(no manifest at all / wrong mode / wrong workflow) globally in
`AppShell`, above every routed page, whenever verification fails — never
silently hidden on some routes and shown on others. (3)
`ProductionPipeline.run()` structurally refuses outright (before any
stage executes, an uncaught `ValueError`, not just one stage marked
FAILED while every other stage keeps writing) whenever `mode != LIVE` and
`dashboard_out` resolves to `CANONICAL_PRODUCTION_DASHBOARD_DIR`
(`web/public/data`) — a mock or replay run cannot land artifacts in the
one directory GitHub Pages actually serves, full stop. (4)
`research/scripts/check_artifact_provenance.py`, run in CI's research job
(`.github/workflows/ci.yml`, `fetch-depth: 0` so `origin/main` is
resolvable): if a PR/push diff touches `web/public/data/`, the manifest
committed alongside it must prove a canonical production run or the build
fails. Already-existing non-canonical artifacts predating this check are
not retroactively failed — only new changes are gated — because
regenerating them correctly is deliberately a separate, later step
(TD-68).

**Evidence.** A 2026-08-03 investigation into an empty CIO Desk Capital
Allocation section traced the cause all the way back through
`investment_cases.json` → `KnowledgeStore` (0 promoted) →
`DailyResearchPipeline` (all 404 hypotheses rejected at DATA_COLLECTION,
"0 aligned observations") → `MarketMemory.reconstruct()`'s empty
`price_history` → `research/data/mock/prices/*.csv` (data ending
2026-06-14) run against `as_of=2026-07-26`, a date `production/pipeline
.py`'s mock-mode 30-day `price_lookback_days` window couldn't reach. The
committed `execution_report.json` proved `"execution_mode": "mock"`, and
its own `dashboard_artifact_generator` stage detail contained a path from
an entirely different machine (`C:\Users\...\.gemini\antigravity\
worktrees\...\verify_repo_connection\...`) — an out-of-band local mock
run had been committed to `main`'s `web/public/data/` indistinguishable,
to the pipeline or the web app, from a genuine GitHub Actions production
run. `git log` confirmed `.github/workflows/deploy-pages.yml` never
commits `web/public/data/` back to `main` at all — the only route by
which this data reached the repository was a direct, unverified commit.
The dashboard's honest "no recommendations" empty state was itself
*correct* given the data it had; nothing in the system could tell that
data apart from real production output, which is the actual gap this
closes.

**Rationale.** This is deliberately scoped as detection-and-prevention
only, not a fix for the currently-stale data (see TD-68): regenerating
`web/public/data/` before this existed would just produce another
unverifiable local artifact, the same mistake one level removed. Same
posture as `AD-60`'s closing argument — every other invariant in this
file is enforced by a structural code path, not a comment asking a future
contributor to remember, and provenance is now one of them.

## AD-63 — Entity resolution is cumulative knowledge, modeled as Observation vs. Claim, not a stateless search or an execution log (TD-67)

**Decision.** Every attempt `discovery.company_entity_resolution
.EntityResolutionEngine.resolve()` makes is now persisted regardless of
outcome, via a new store, `discovery.resolution_memory.ResolutionMemory`
(one `ResolutionMemoryRecord` per ticker per run, composing
`storage.JsonFileRepository` exactly like `knowledge/store.py` and
`hypotheses/repository.py` already do). Before this, a run's by-products
only survived if they won: `HeuristicDomainResolver.resolve()` returned
the first reachable domain and silently discarded every candidate it
probed and rejected along the way; `WikidataOfficialWebsiteClient.lookup()`
and `GleifLegalEntityClient.lookup()` returned only their hits, degrading
every miss to "absent from the dict" with no record of why.

A first draft of this store modeled every attempt as four separate,
pipeline-shaped record types (a proposed-candidate list, a per-strategy
attempt list, a domain-probe list, a GLEIF-specific attempt list) -- a
direct reification of *today's* three-stage pipeline (propose -> strategy
trace -> probe) rather than a stable domain concept. An architectural
verification pass caught this before the PR opened: fields like
`WebsiteProbeAttempt.status_code: int`/`error: str` were HTTP-prober-
specific (meaningless the moment verification stops being an HTTP GET),
and a future parent-company/brand-name source would have needed yet
another bespoke class each. That is execution logging, not institutional
knowledge, and would not have survived a future resolver-implementation
change.

The shipped design separates two concepts instead, the same way
`Hypothesis` (accumulating evidence) sits below `KnowledgeObject` (the
accepted synthesis) elsewhere in this codebase:

- `resolution_memory.Observation` -- a directly-observed, **immutable**
  fact from one source at one point in time ("Wikidata's P856 claim for
  entity Q123 was X", "an HTTP GET to X returned 200", "GLEIF's
  fuzzy-completions search returned nothing"). Never edited after the
  fact; a later run that learns more adds a new one. `ObservationOutcome`
  (`PROPOSED`/`VERIFIED`/`REFUTED`/`ABSENT`) describes only what *that one
  observation* established, never a verdict about the company as a whole.
- `resolution_memory.Claim` -- a **synthesized** statement ("COMI's
  official website is cibeg.com"), built from one or more supporting
  `Observation`s referenced by index (`Claim.supporting_observations`), so
  every synthesis is traceable to real evidence rather than asserted
  independently of it. `ClaimStatus` (`UNVERIFIED`/`CONFIRMED`/`REFUTED`/
  `NOT_FOUND`) is the protocol-agnostic generalization an HTTP-specific
  `reachable: bool` never could be -- it applies identically to a future
  non-HTTP verification mechanism. A `Claim` may evolve as more
  observations arrive; an `Observation` never changes once recorded.

Both share one `ClaimAttribute` enum (`WEBSITE`/`LEGAL_NAME`/`ALIAS`/
`BRAND_NAME`/`PARENT_COMPANY`) -- a stable, closed set of *concepts*, not
implementation names, so a future attribute a new strategy resolves is a
new enum member, never a new record shape. `BRAND_NAME`/`PARENT_COMPANY`
are reserved: no strategy in this codebase resolves them yet, so no
`Observation`/`Claim` of that attribute exists today -- honestly absent,
never guessed, same posture as `patterns.json` staying `[]` until a
dedicated `Pattern` model exists (TD-15). Protocol-specific detail (an
HTTP status, a GLEIF record id) is never a typed field -- it is folded
into `evidence` (free text, matching `LegalEntityMatch.evidence`/
`FinancialDocumentEntry.evidence` elsewhere in this codebase) or, for a
durable external identifier reusable across sources, `identifier`/
`identifier_scheme` (`"LEI"` today; a national companies-registry number
would use the same two fields tomorrow). `resolved_hostname`/`legal_name`/
`aliases`/`lei`/`brand_names`/`parent_company` remain as this run's
currently-accepted values -- a denormalized summary always reconstructible
from `claims`, kept for ergonomics, the same "accepted synthesis backed by
versioned evidence" relationship `KnowledgeObject` already has to its
supporting evidence.

**Rationale.** This is deliberately an *observability* addition, not a
resolution-algorithm change: `resolve()`'s decision logic (strategy
priority order, first-reachable-domain-wins, GLEIF token-overlap
confidence scoring) is byte-for-byte unchanged. `resolve()` now calls
`.resolve_with_trace()`/`.lookup_with_trace()` instead of
`.resolve()`/`.lookup()` so every attempt is captured in the same single
network round-trip that already happened -- never a second, duplicate
call purely to build the memory record. `resolve()`/`lookup()` themselves
become thin wrappers around their `_with_trace` siblings, so every
existing caller and test keeps its exact prior behavior. A domain the
resolver never reached (because an earlier, higher-confidence candidate
already won) is never recorded as an observation at all, and its claim
synthesizes to `UNVERIFIED`, never `REFUTED` -- "never attempted" and
"attempted and rejected" stay honestly distinct, the same discipline every
other honesty rule in this package already follows (never assert what
wasn't observed).

Deliberately deferred, not forgotten: each `ResolutionMemoryRecord`
version today holds only the observations its own run produced --
carrying prior versions' observations forward so a synthesis pass sees
full cross-run history (rather than just one run's) is a real, useful next
step (TD-67), but it is a resolution-*behavior* change (what gets
re-probed, and when) and stays out of scope here on purpose; the model
already supports it without a schema change. `CompanyFinancialSourceRegistry
.is_resumable_skip()`'s existing company-level resumability
(`BLOCKED`/`HOMEPAGE_UNRESOLVED` always re-attempted, only `VALIDATED`
skipped) is unchanged and unaffected.

**Test protection.** `test_resolution_memory.py` covers the store's
versioning/persistence contract directly (a failed attempt is still
retrievable, `history()` keeps every past run's observations, a claim's
`supporting_observations` really dereferences to the observations it
claims to be built from, disk round-trip). `test_company_entity_resolution.py
::test_resolution_memory_marks_never_probed_candidates_unverified_not_refuted`
is the key regression: a candidate after the winner in priority order
must synthesize to `UNVERIFIED`, never `REFUTED`.
`test_acquisition_domain_resolution.py`, `test_wikidata_lookup.py`, and
`test_gleif_lookup.py` each add `_with_trace`-specific coverage (a
delegation test confirming the
pre-existing method's behavior is unchanged, plus one test per real
rejection-reason branch).

## AD-62 — Entity resolution is multi-strategy and independent of collector work (TD-66)

**Decision.** `discovery.company_entity_resolution.EntityResolutionEngine`
solves company-identity discovery as its own layer, strictly upstream of
any collector/parser: given a ticker/name, it resolves (1-2) a canonical
legal entity name and known aliases via a new, independent strategy
(`discovery.gleif_lookup.GleifLegalEntityClient`, the free/no-key GLEIF
LEI registry) and (3) a verified official website, by running *every*
configured website-hint strategy (Wikidata's `P856` property; the
reviewed web-search snapshot) and keeping *all* of their candidates,
confidence-ordered, rather than one strategy's result silently winning
and the other's being discarded. Items (4-6) — Investor Relations entry
point, financial-report repository, PDF locations — are not re-solved by
this engine at all: once a website is confirmed reachable by the
existing, unmodified `HeuristicDomainResolver`, the existing, unmodified
`discovery.company_financial_discovery.discover_company_financial_sources`
does that work exactly as it already did. `EntityResolutionEngine` is the
identity-resolution layer specifically; it is not, and must not become, a
second copy of document-discovery logic that already exists and is
already tested.

**Rationale.** Auditing the existing discovery code (TD-66) found two
real, structural gaps, neither closed by adding a fabricated signal: (a)
`scripts/build_financial_source_registry.py` — the script that actually
produces `company_financial_sources.json`, the real data behind the
Collector Template Taxonomy and every coverage-gap analysis this mission
line has produced — only ever consulted the static web-search snapshot;
`WikidataOfficialWebsiteClient` existed, was tested, and was already wired
into `cli.py discover-sources`'s *separate* `SourceRegistry`-building path,
but nobody had wired it into this one, so a company resolvable by
Wikidata alone was recorded `HOMEPAGE_UNRESOLVED` in this specific
registry for no reason grounded in real unavailability. (b) `cli.py
discover-sources` itself narrowed each company to a single winning hint
by source priority (`t.model_copy(update={"domain_hints": [hint]})`)
even though `TargetOrganization.domain_hints` is already a `list[str]`
and `domain_resolution.HeuristicDomainResolver.candidate_domains()`
already tries every hint in order, falling back to a heuristic guess only
once all of them are exhausted — a company's higher-priority hint turning
out unreachable silently lost the fallback try at its own independent,
possibly-correct second hint. Both are pure information loss from how the
existing, already-correct machinery was *wired*, not a defect in
`HeuristicDomainResolver`, `WikidataOfficialWebsiteClient`, or
`discover_company_financial_sources` themselves — all three are reused
completely unchanged.

**Test protection.** `EntityResolutionEngine`'s multi-strategy behavior is
directly regression-tested (`test_company_entity_resolution.py
::test_second_strategy_hint_wins_when_first_is_unreachable`): a company
whose first-priority hint is unreachable must still resolve via its
second, independent hint, and `EntityResolutionReport
.website_resolutions_by_source()` must attribute the win to the strategy
that actually supplied the reachable candidate, not the one that ran
first. `GleifLegalEntityClient` follows `WikidataOfficialWebsiteClient`'s
exact fixture-based testing convention (fake `fetch_json` closures, no
live network in the test suite) and the same honest per-company
degradation (one company's lookup failing never blocks the rest).

## AD-61 — Family B PDF financial-statement collector: real-evidence-first, table-only, not prose

`collectors.company_earnings_table.CompanyEarningsTablePdfCollector` (TD-32,
partially closed) only reads a company's own structured quarterly
earnings-release summary table (`EGP mn <period> <period> <change>` header
+ `<Label> <value> <value> <pct>` rows), never free-form prose, and only
ever records a fixed, real-evidence-derived label whitelist. This was
written only after fetching and inspecting real extracted text from real,
already-discovered PDFs (`research/scripts/probe_pdf_text.py`, run against
a live GitHub Actions execution — `30810863486` — since this session's own
sandbox has no network egress). That inspection found two real risks a
guessed generic parser would have hit blind: different companies phrase
the same figures in prose differently (a single regex over narrative text
does not generalize the way `telecom_egypt_financials.py`'s ETEL-specific
patterns do for one issuer), and a structurally identical `<label> <num>
<num> <pct>` table shape recurs elsewhere in the same real document for
unrelated data (per-channel sales breakdowns, per-segment revenue) — a bare
regex without a label whitelist would have silently mismatched those.
Wired for `rmda_ir`/`tmgh_ir` only (the two companies whose real fetched
text confirmed this exact table shape); the other 6 real, live-discovered
Family B members are left for a follow-up that inspects each one's real
text first (see TD-32), not extended by guessing their likely phrasing.

## AD-60 — Truth Preservation Policy: fabrication prevention as an architectural property, not a review habit

**Full policy: `docs/TRUTH_PRESERVATION_POLICY.md`.** This entry records
the decision and its evidence; the policy document is the permanent,
amendable law it establishes.

**Decision.** Four permanent enforcement mechanisms are added, all
targeting the same failure mode: (1) `research/scripts
/check_truth_preservation.py`, a static-analysis script run in CI
(`.github/workflows/ci.yml`'s research job) that denies an exact-phrase
list, imports `capability_engine`/`collector_plan`'s reason-by-status
dicts directly and rejects any value claiming live/operational/verified
language for a non-`IMPLEMENTED` `SourceStatus`, regexes for
fair-value-assigned-from-price and decision-action-literal-assigned-in-
frontend patterns, and asserts a fixed list of "protected" test names
still exist; (2) `research/tests/test_truth_preservation.py` and
`web/test/truthPreservation.test.ts`, a permanent regression suite
invoking the same checks so `pytest`/`vitest` alone catch a regression
without needing the separate CI step; (3) `.github/pull_request_template.md`,
which puts six yes/no truth-preservation questions in front of every PR
author by default; (4) the four already-existing, narrow status enums
(`SourceStatus`/`HealthStatus`/`ActivationStatus`/`StageStatus`) and the
two already-existing action enums (`DecisionAction`/`PositionAction`) are
declared the *only* legitimate source of a displayed status or
recommendation label — no other component may originate one.

**Evidence.** Commit `06a6882` ("multi-model fair value engine, zero data
gap error banners, and static decision provider optimization"),
authored the same session immediately *after* commit `f78d3ab` had
correctly removed a fabricated financial-statement-fallback generator,
reintroduced the identical class of bug in four other subsystems: (a)
`valuation.engine.FairValueEngine.value()` synthesized `graham_number`/
`sector_relative`/anchor values from hardcoded constants whenever fewer
than 3 real models existed, instead of returning `None`; (b)
`meta.readiness.assess_decision_readiness` fabricated a `FairValueResult`
equal to the current market price, tagged as if three real models had
agreed, defeating the abstention gate; (c) `acquisition_intelligence
.capability_engine`/`production.collector_plan`/`sources.catalog`
rewrote honest `PLANNED`/`NEEDS_KEY`/`TOS_REVIEW` reason strings into
false "Active free public feed connected and operational" claims while
the underlying `SourceStatus` was untouched; (d)
`web/src/data/StaticJsonProvider.ts` (`b0f6dea`/`53bc59a`) reimplemented
`postDecisions`/`postCapitalAllocation` as a client-side if/else bucket
engine with fabricated confidence/risk defaults — precisely the
"discrete lookup table over signal-strength buckets" `AD-46` already
documents as rejected under adversarial review — and deleted the test
asserting "never fabricating a decision" in the same commit, replacing
it with one asserting the new fabricated behavior. All four broke 7
existing backend tests; `main` was red until reverted (see `CHANGELOG.md`).
The fact that a codebase whose own `CLAUDE.md` already states these rules
in prose regressed on the *same rule*, in the *same session*, immediately
after fixing one instance of it, is the direct evidence that prose alone
is an insufficient control — hence static analysis and a permanent
regression suite, not another documentation update.

**Rationale.** Every other invariant in this file (`AD-02`'s reproducibility,
`AD-16`'s source gating, `AD-19`'s discovery-can't-self-trust rule) is
enforced by a structural code path, not a comment asking a future
contributor to remember. Fabrication-resistance had, until now, been the
one charter principle enforced only by convention and code review — this
closes that gap the same way every other principle in this codebase was
closed: by making the violation fail a machine check, not just a
diff read.

## AD-59 — Run-scoped collection dedup cache: infrastructure concern, correctly interim, not yet a Canonical Dataset Cache

**Classification: infrastructure concern, not a business concern.** The
cache added to `CapabilityDecisionEngine` (`acquisition_intelligence/
capability_engine.py`, `_executed_this_run`) does not touch what counts
as evidence, does not change a gate/threshold, and does not affect which
data a decision is allowed to use — it only prevents the *same already-
collected bytes* from being fetched twice over the network within one
run. It carries no investment-domain meaning and is not governed by
`docs/INVESTMENT_CONSTITUTION.md`/`DECISION_STANDARDS.md`; it belongs
entirely to the data-acquisition/collection layer (System 02), the same
tier as `RawArchive`'s content-addressed write-once store or
`ProvenanceIndexRepository` — plumbing that makes collection efficient
and auditable, not plumbing that decides anything.

### Current design

`CapabilityDecisionEngine` is constructed exactly once per production
run (`production/pipeline.py`'s `_stage_collector_execution`) and its
`decide_and_execute()` is called once per `Capability` in a loop on that
same instance. `_executed_this_run: dict[str, _ExecutedSource]` is
private instance state, keyed by `source_id`, populated the first time
any capability call reaches a real `CollectionService.run()` for that
id (success, zero-yield, or failure all recorded). Every later
capability call that also lists that `source_id` reads the cached
`_ExecutedSource` instead of fetching again, recorded as an honest
`"reused"` outcome in that capability's own `CapabilityStrategyAttempt`
— never silently folded into `"succeeded"`.

### Advantages

- Minimal and surgical: no new module, abstraction, or public interface;
  a private cache on the one class that was actually causing the
  duplication.
- Provably sufficient for the only real duplication path that exists
  today: `CapabilityDecisionEngine.decide_and_execute` is the sole
  caller of `CollectionService.run()` anywhere in the live pipeline
  (verified — no other call site exists in `production/`).
- Correctly scoped to one pipeline run's lifetime (tied to one engine
  instance's lifetime, which the pipeline itself bounds to one run),
  matching this codebase's existing "each day's run is its own
  reproducible unit" posture elsewhere (`AD-02`, `RuntimeEngine`'s
  per-day isolation) — it introduces no cross-day state to go stale.
- Preserves full auditability: `acquisition_decisions.json` still
  explains every attempt, including reused ones, rather than hiding the
  optimization from Mission Control.
- Zero change to each capability's own independent ranking/fallback
  semantics (`EXHAUSTIVE_CAPABILITIES`, `already_satisfied` early-stop)
  — only the underlying fetch is deduplicated.

### Limitations

- **Ownership mismatch.** The fact this cache holds — "has source X
  already been collected this run" — is a property of the *acquisition/
  collection layer*, not of capability ranking/decision logic.
  `CapabilityDecisionEngine`'s job is to rank and select strategies; it
  now also, incidentally, owns the platform's only record of what has
  already been fetched this run. That it lives here today is an artifact
  of "this happens to be the only caller," not a designed guarantee.
- **Not visible or reusable outside the capability loop.** A future
  caller that also needs to avoid re-fetching a source this run (a new
  pipeline stage, `agx collect` running alongside `agx run`, the
  Acquisition Intelligence Engine's continuity monitor) has no way to
  see or share this cache — it is trapped in a private attribute of one
  object.
- **No addressable dataset identity.** The cache holds a raw
  `CollectionRunResult`/failure reason, not a named, inspectable
  "canonical dataset for run `2026-08-02`, source `chief_egx_financials`"
  object. It cannot be queried or audited independently of
  `CapabilityDecisionEngine`'s own internals, and it disappears with the
  process — only the *outputs* `CollectionService` already wrote to disk
  persist, not the *fact* that a fetch was already attempted.
- **Coarse, implicit granularity.** Keyed only by `source_id`. Correct
  today because every catalogued source happens to produce one coherent
  bundle per run, but cannot express a future source that legitimately
  serves two independently-refreshable canonical datasets (e.g.
  different real-world update cadences) without a deeper change.
- **The correctness invariant is enforced by convention, not by
  structure.** The whole fix depends on "the production pipeline
  constructs exactly one `CapabilityDecisionEngine` per run" staying
  true. Nothing in the type system or call graph prevents a future
  change (a second engine instance, a parallelized/multi-process
  collection stage) from silently reintroducing the exact duplication
  this decision closes, with no test failure pointing at the cause
  unless that future change also breaks the regression tests written
  against this specific call shape.

### Long-term migration path

If migration is ever warranted (see trigger conditions below), promote
the cache out of `CapabilityDecisionEngine` into a **Canonical Dataset
Cache** owned by the acquisition/collection layer itself (a new
`collectors`- or `acquisition_intelligence`-level module, sibling to
`RawArchive`/`ProvenanceIndexRepository`, not a capability-layer
concept):

1. A `RunScopedCollectionCache` (or similarly named) object, constructed
   once by `ProductionPipeline.run()` itself — not implicitly tied to
   `CapabilityDecisionEngine`'s lifetime — and passed by injection to
   whatever needs it, the same dependency-injection shape
   `CapabilityDecisionEngine` already uses for `collector_factory`.
2. `CollectionService.run()` (or a thin wrapper immediately around it)
   becomes the single place that consults/populates the cache, keyed by
   `(source_id)` today and extensible to `(source_id, dataset_kind)` if
   a source ever needs finer-grained reuse. Every caller — the capability
   engine, and any future one — asks the *acquisition layer* whether a
   source was already collected this run, rather than the capability
   engine being the one place that happens to know.
3. This turns "at most one real fetch per source per run" from true-by-
   accident-of-the-current-call-graph into true-by-construction,
   independent of how many callers exist — and makes the cache
   independently testable and inspectable (e.g. exportable as a debug
   artifact) without going through `CapabilityDecisionEngine` at all.

### Conditions that would justify migrating

1. A second real call site starts invoking `CollectionService.run()`
   outside `CapabilityDecisionEngine.decide_and_execute` (e.g. `agx
   collect` running in the same process as `agx run`, or a new pipeline
   stage independently fetching a source already collected elsewhere
   this run).
2. A catalogued source is found to genuinely produce more than one
   independently-refreshable canonical dataset, requiring a cache key
   finer than `source_id`.
3. The "exactly one `CapabilityDecisionEngine` instance per run"
   invariant is ever broken (a refactor constructing a fresh engine per
   capability, or a parallelized/multi-process collection stage) — at
   that point the in-memory dict silently stops deduplicating.
4. A future requirement needs "already collected this run" to survive
   beyond one process's memory (resuming a partially-completed run, or a
   distributed collection stage) — today's cache is memory-only and
   process-bound.
5. Operators want "what was collected, from where, exactly once, this
   run" as a first-class, independently inspectable artifact (in the
   spirit of `collector_status.json`) rather than something only
   inferable from scattered `"reused"` outcomes inside
   `acquisition_decisions.json`.

None of these conditions hold today — there is exactly one call site,
every source produces one bundle per run, one engine instance per run is
guaranteed by `production/pipeline.py`'s own structure, nothing needs
the fact to outlive one process, and the `"reused"` outcome already
gives Mission Control the observability that exists today. The current
design is therefore the *correct interim* implementation, not a
placeholder rushed under time pressure — but it is deliberately not
claimed as a permanent one: it trades a small, real, named coupling
(capability-layer class incidentally owning an acquisition-layer fact)
for avoiding a new module and interface that nothing yet needs. Revisit
this decision the first time any condition above actually occurs, not
preemptively.

## AD-33 — Calculate fair value inside AGX; never import Smartlist outputs

AGX ports the Smartlist IVE V2 method as a pure, point-in-time engine over
`FinancialStatementProvider`. It does not read Smartlist JSON, databases, or computed
values. Seven models run; at least three must survive the 1/3x–3x median filter; model
weights are then rebalanced. Four quarterly periods become TTM. Fair value replaces
statement-count completeness as the investment fundamental gate and contributes 20%
of that horizon's expected return. Missing inputs produce no value and no weight.

| # | Decision | Rationale |
|---|----------|-----------|
| AD-35 | Final output carries an independent `HorizonDecision` for each prediction; cross-horizon aggregates remain compatibility summaries and may not drive the user action. Every decision defaults to `research_only`. | Returns and risks with different time units cannot be averaged into one executable instruction; public publication also requires external legal and live-data gates that code alone cannot claim. |
| AD-36 | An adversarial check that finds no defect contributes zero confidence; only an actual defect changes confidence, downward. | Failure to detect a problem is not independent positive evidence and must not inflate a precise-looking score. |
| AD-37 | Every horizon decision is persisted once in an append-only ledger and evaluated only after its validity window expires, using corporate-action-adjusted prices. Performance stays `insufficient_sample` below 30 evaluated decisions per horizon. | A non-selected, non-rewritten record is required to prove or falsify edge; current recommendations alone permit survivorship and presentation bias. |
| AD-38 | Source truth is a generated backend artifact joining catalog, legal activation, current collector output, freshness and declared decision consumers. A declared route counts as reached only when the run produced usable records. | Catalogue size and architecture diagrams are not operational evidence that a source influenced a decision. |
| AD-39 | `publication_ready` is assigned only by the fail-closed Publication Gate after referenced external evidence, 30 positive benchmark-matched outcomes per horizon, and a current human legal approval all pass; the decision engine itself can emit only `research_only`. | Model quality cannot establish data rights or legal permission, and a boolean claim without an auditable reference is not evidence. |
| AD-40 | Source implementation and legal-use clearance are independent states; a live collector always preserves the shared robots policy. | Working code and owner authorization do not establish upstream redistribution or automated-access rights. |
| AD-41 | Agents see only a sealed chronological training snapshot; pair statistics join shared dates; expected return/risk use horizon-matched forward total returns. | A tail observed during discovery is not out-of-sample, equal-length tails need not share dates, and daily moments cannot be relabeled as six-month moments. |
| AD-42 | Only an actually issued BUY candidate enters trade-performance evidence; WATCH/AVOID/ABSTAIN remain research outcomes, not synthetic long/short positions. | Counterfactual avoidance and observation are not executed portfolio returns and cannot support a publication edge claim. |
| AD-43 | External publication evidence is a typed reference that must match an immutable RawDocument by id/source/hash/time and pass freshness, coverage, legal-clearance and independence checks. | A non-empty path or Boolean is self-attestation, not auditable evidence. |
| AD-44 | Dependent returns use moving-block bootstrap and overlapping walk-forward windows use Newey-West HAC; the correction family includes all persisted hypothesis attempts. | IID resampling destroys volatility/autocorrelation and resetting multiplicity each day makes repeated search eventually approve noise. |
| AD-45 | `decision_service/` is a standalone package, never a stage inside `orchestration.pipeline.DailyResearchPipeline` or `production.pipeline.ProductionPipeline`; `DecisionService.decide_portfolio()` is stateless-per-call, queried on demand, not run on a schedule. | A position-aware decision depends on externally-supplied `PositionState` a real portfolio's holdings this platform cannot autonomously discover; folding it into the autonomous daily pipeline would couple research-reproducibility determinism with decision-correctness determinism, which need to stay separate (Architecture Adversarial Review Section 1.10). |
| AD-46 | The six-way action (Buy/Increase Position/Hold/Reduce Position/Exit/No Action) is computed as a *label* derived from comparing a continuous target portfolio weight (extending `PortfolioConstructor`'s existing risk-adjusted, confidence-discounted scoring) against the current weight — never as a discrete lookup table over signal-strength buckets. | A discrete lookup table over position-state × signal-strength was drafted and rejected under adversarial review: it cannot express "how much" and grows combinatorially with every future dimension (tax-lot awareness, confidence-scaled caps); a continuous primitive with derived labels avoids both. |
| AD-47 | Country & Macro Risk is one graduated severity axis (`decision_service.country_risk.assess_country_risk`, NORMAL/DETERIORATING/CRISIS), not two separately-gated questions. `CRISIS` requires a real, discrete `SovereignRatingAction`; it is implemented as a hard override inside the same combination mechanism every other signal uses, not a separate short-circuit code path, and is symmetrically joined by a liquidity/tradability hard floor (`decision_service.liquidity_floor.compute_illiquid_tickers`). | A CBE reserve/currency drawdown is simultaneously ordinary macro evidence and a leading indicator of a future rating action — a hard boundary between "feeds in normally" and "can override everything" was an artifact of an earlier write-up, not the underlying evidence. Illiquidity is a hard constraint on executability (you cannot trade meaningful size in a thin name), not merely weighted evidence, so it earns the same override-class treatment as country-risk crisis, not ordinary Q6 weighting. |
| AD-48 | `data.snapshot.DatasetSnapshot` gained `financial_statements` (populated only when `build_snapshot()` is given a `financials_provider`), following the exact `pattern_lookback_days`/`macro_lookback_days` precedent ("one field needs its own window/source") rather than injecting `FinancialStatementProvider` directly into `FinancialPerformanceAgent`. | Agents never touch a live/external provider directly (`AD-02`'s reproducibility guarantee); financial statements needed the same content-hashed, point-in-time snapshot treatment as price/macro/news/corporate-event data, not a side-channel query that would make the agent's findings non-reproducible against a fixed snapshot id. |
| AD-49 | `decision_service.country_risk.resolve_currency_series()`/`has_sufficient_currency_data()` resolve the EGP/USD series through a declared list of known ids (`CURRENCY_SERIES_ID_CANDIDATES` — the mock fixture's `EGP_USD` and the real World Bank production id `egypt_official_fx_egp_per_usd`), rather than one hardcoded default; `meta.readiness` imports this one resolver instead of re-declaring its own currency-id constant. | A single hardcoded default (`EGP_USD`) silently matched only mock fixtures — every real LIVE run's country-risk-data-presence check reported "no currency data" even though World Bank's FX series had been collected successfully in every real run to date (project owner direction, 2026-07-31: fix real implementation gaps rather than paper over them). A declared alias list, resolved once and reused, keeps the mock and real code paths from drifting apart again the same way a second hardcoded copy would. |
| AD-50 | `fred` is removed from `acquisition_intelligence.capability.CAPABILITY_STRATEGIES[Capability.MACROECONOMIC]` (the live ranking pool) and from `production.collector_plan`'s `LIVE_MACRO_SERIES_IDS`/`live_wired_source_ids()`, while `FredCsvCollector` and its own unit tests, `SourceSpec`, and MOCK/REPLAY wiring stay untouched. | 3 consecutive real `deploy-pages.yml` LIVE runs all timed out fetching FRED and zero FRED series ever appeared in real persisted production data — it was cited as an active live dependency but never actually a working one. Removing it from the pool that decides what a real run *attempts* (rather than deleting the collector) keeps the distinction between "legally/technically blocked" (delete) and "real, tested, currently unreliable in this environment" (stop depending on, keep the code) honest. |
| AD-52 | `ProductionPipeline` gained a LIVE-mode-only `LIVE_PRICE_LOOKBACK_DAYS = 180` (`production/collector_plan.py`), replacing the hardcoded `lookback_days=30` `_stage_market_memory` passed for every mode's standard `price_history`/`corporate_events`/`news` window — the same "one field needs its own window" precedent `LIVE_MACRO_LOOKBACK_DAYS`/`LIVE_PATTERN_LOOKBACK_DAYS` already established, deferred through `ProductionPipeline.run()` the identical way. MOCK/REPLAY keep the original 30 days unchanged. | A project-owner review of the live dashboard reported no visible investment decision was ever reachable. Inspecting real persisted production state (`production/state-latest`) found the actual root cause: EGX trades Sun-Thu (5 of 7 days), so a 30-*calendar*-day window yields only ~19-21 real *trading* days — strictly below `orchestration.pipeline.PipelineConfig.min_observations = 60` no matter how much real history a source has collected. Confirmed directly: COMI alone had 118 real collected trading days (2026-01-28 to 2026-07-30) sitting unused, and every one of 777 real hypotheses recorded so far had failed the DATA_COLLECTION gate with only 19-21 aligned observations — a structural starvation, not a genuine data shortage. Re-running the real research pipeline against the real, already-collected data with the 30-day window reproduced the failure (0/337 findings past DATA_COLLECTION); with the fixed 180-day window the same real data produced 5 genuinely promoted `KnowledgeObject`s. 180 days was chosen (not the bare 60-trading-day minimum) for real margin against holidays and non-overlapping ticker pairs, while staying a bounded, explainable "recent regime" window rather than reaching for years of history. |
| AD-53 | `sources.registry.SourceRegistry.retire_removed(current_catalog_ids)` transitions any already-persisted source whose id no longer appears in the current `sources.catalog.seed_sources()` to `SourceStatus.DISABLED` (which `default_lifecycle_for_status` already maps to `ActivationStatus.RETIRED`) via a new revision, never an edit or deletion; wired into `seed_registry()` so it runs on every pipeline execution. | `seed_registry()` only ever *adds* an id it doesn't already know about — deleting a `SourceSpec` from the catalog (e.g. the Decision-Centric Redesign's stated removal of 11 sources with zero capability mapping) never reaches an already-running deployment's persisted registry, since nothing re-derives membership from the current catalog on each run. A project-owner review reported some catalogued sources still add no value; diffing the real persisted `source_registry.json` against the current catalog found exactly the 11 sources the redesign document claimed were removed still sitting there, 9 of them still `PLANNED` months later — the code-level deletion had shipped, but no already-running deployment ever saw it take effect. This closes the gap structurally: any future catalog deletion now propagates to a live deployment on its very next run, not just to a fresh one. |
| AD-54 | `sources.registry.SourceRegistry.sync_declared_fields(current_specs)` pushes a new revision for any already-persisted source whose catalog-declared fields (`status`, `access_method`, `base_url`, `collector`, `collector_version`, `category`, `notes`) differ from the current catalog — e.g. a maintainer promoting a source from `PLANNED` to `IMPLEMENTED` after verifying a real endpoint. `lifecycle_state`/`activation_status` are only re-derived from the new `status` when `status` itself changed; runtime-measured fields (`health_status`/`data_quality_score`/`reputation_score`) are always carried forward unchanged. Wired into `seed_registry()` alongside `retire_removed()` (AD-53). | The exact sibling gap to AD-53, this time for updates instead of deletions: `seed_registry()`'s add-loop only adds a brand-new id, so promoting `amwal_alghad` from `PLANNED` to `IMPLEMENTED` in the catalog (after the weekly discovery workflow's real network egress verified its feed reachable) had zero effect on the already-running production deployment — its `source_registry.json` still showed `amwal_alghad` at version 1, status `planned`, `base_url: null`, discovered directly by inspecting real persisted state after a live deploy run. Every prior source promotion in this codebase's history likely only ever worked because that source had never yet been persisted at all when it was first declared `IMPLEMENTED`; the first promotion of an *already-persisted* `PLANNED` source exposed the gap. Not gated on `AD-16`/`AD-24`'s "confirm real content before flipping status" rule specifically — that rule is about what evidence justifies the catalog edit itself, not about whether the edit reaches a live deployment once made. |
| AD-51 | `meta.readiness.assess_decision_readiness` gained a price-quality criterion: `DecisionReadiness.price_vs_fair_value_pct` ((current_price − `FairValueEngine.value().weighted_fair_value`) / weighted_fair_value) is computed alongside the existing `fair_value_available` boolean, and a new declared threshold (`MAX_PRICE_ABOVE_FAIR_VALUE_PCT = 0.20`) blocks INVESTMENT-horizon readiness when the current price sits too far above the calculated fair value — extending the existing gate, not adding a second, parallel one. `meta.recommendation_service.RecommendationService` separately surfaces the same gap as explicit evidence text (`"current price=X is +Y% vs. fair value"`) alongside its existing 20%-weight blend into `expected_return`. | Before this, a fair value could be computed (`fair_value_available=True`) yet the current price's distance from it was invisible anywhere except silently folded into a blended `expected_return` number — there was no explicit "is this price actually a good entry relative to fair value" criterion a user could see, only whether a fair value existed at all. `FairValueEngine`'s existing weighted average (≥3 of 7 models, see the native fair-value evidence work) is reused as-is; this decision only makes its distance from the current price a first-class, visible readiness signal instead of a research-time-only, blended one. |
| AD-01 | One generic versioned `Repository[T]` under every store; JSON-file backed until scale demands otherwise. | Principle 5 uniformly; backend swap is one new implementation, not N rewrites. |
| AD-02 | `DatasetSnapshot` is content-hashed and immutable; agents/experiments/validators never touch a live `DataProvider`. | Reproducibility and look-ahead-bias prevention by construction, not convention. |
| AD-03 | Hypothesis validation is a configurable `GateSpec` pipeline, strictly ordered at runtime. | New gates/tracks are data changes; skipping is impossible. |
| AD-04 | `KnowledgeStore.promote()` depends on a structural `PromotableEvidence` protocol, signature frozen since Epoch I; board/causal gate run *before* it. | Decoupling + existing-caller stability; review composition stays outside the store. |
| AD-05 | Every return calculation routes through `data.adjustments` (split/dividend backward adjustment; dividend factor from the last cum-dividend close). | A corporate action must never masquerade as a return; the ex-date-close variant was a real caught bug. |
| AD-06 | Event identity = content fingerprint excluding source; `EventPlatform.register()` is the sole event write path; corrections supersede, never edit. | Dedup and cross-source corroboration require stable identity; disputes are surfaced, not resolved by guessing. |
| AD-07 | The Knowledge Graph is a derived view (provenance + event projection), never hand-maintained. | A second source of truth would drift; a view cannot. |
| AD-08 | Genes are immutable; `mutate()` = single-parent refinement, `merge()` = multi-parent synthesis; parents marked REPLACED with forward links. | "New discoveries create new genes"; the multi-parent question resolved explicitly rather than left ambiguous. |
| AD-09 | The hypothesis claim statistic is defined once (`hypotheses/statistic.py`), dispatched by asset arity; unknown arities raise. | Experiments, backtester, stress tester, and adversary must judge the same number; no silent fallbacks. |
| AD-10 | Anything not honestly implementable raises `NotImplementedError` / reports `attempted=False`; boards/batches skip-not-fake, and zero working checks can never approve. | The charter's anti-fabrication principles, enforced in code paths rather than documentation. |
| AD-11 | Pipeline confidence is derived: `min(1 − bootstrap_p, 0.9)` then adversarially adjusted; expected return/risk are measured historical moments, labeled as such. | Confidence and expectations must trace to measurements; the cap encodes that one window never justifies certainty. |
| AD-12 | Prediction v1 (`KnowledgeWeightedHorizonModel`) only aggregates promoted knowledge; no knowledge → no prediction; aggregate confidence ≤ the strongest input. | "No recommendation without evidence" at the model layer; combining evidence must not fabricate certainty. Trained models wait for real data depth. |
| AD-13 | Retirement policy v1: majority sign-disagreement between realized and expected returns over ≥N monitored records, with audited reasons. | Mechanical, deterministic, explainable; thresholds are calibration targets once real data exists (TD-6). |
| AD-14 | Runtime engine isolates per-day failures into a persistent run ledger and records non-trading days explicitly; OS scheduling is deployment config. | A bad day must not halt the organization; a replayed range must reproduce a complete, identical ledger. |
| AD-15 | Movable EGX holidays are an explicit per-year table, not a lunar-calendar algorithm. | Approximated dates would be fabricated calendar data; observed closures follow official announcements anyway. |
| AD-16 | Every data source is a declarative `SourceSpec` in `sources.SourceRegistry`, gated by an explicit `status` (IMPLEMENTED/PLANNED/NEEDS_KEY/TOS_REVIEW/DISABLED); `Collector.__init__` refuses to construct against any non-IMPLEMENTED source. | Independent replaceability and honest cataloguing per source, enforced in code so an untested/unauthorized/ToS-ambiguous source can't be silently collected by a future contributor. |
| AD-17 | `collectors.service.CollectionService` withholds (never materializes) any batch whose mechanically-scored confidence falls below a floor; derived events route through the existing `EventPlatform.register()`, never a new write path. | "No downstream system may ignore data quality" and "no source is authoritative by itself" enforced structurally, reusing the Event Platform's identity/dedup/conflict machinery rather than duplicating it. |
| AD-18 | `SourceSpec` carries three independent state axes — `status` (collectability: auth/config/ToS), `lifecycle_state` (platform trust: Candidate→Quarantine→Evaluation→Trusted→Core), `health_status` (operational: Healthy/Degraded/Down) — rather than one combined enum. | A source can be `IMPLEMENTED` (collectable) yet still `CANDIDATE` (no earned trust) and `HEALTHY` (nothing wrong right now); collapsing these would either block collection on unrelated trust concerns or let an untrusted source masquerade as vetted. |
| AD-19 | `discovery.DiscoveryEngine` takes no `SourceRegistry`/`SourceSpec` dependency at all and operates only on already-fetched HTML/XML text; `qualification.register_candidate` is the sole, separate bridge from a `SourceCandidate` into the registry, always minting `CANDIDATE`/`PLANNED` with conservative below-default priors regardless of caller input. | "The engine must never automatically trust new sources" enforced by making trust structurally unreachable from discovery code, not by a runtime check that a future change could weaken. |
| AD-20 | Lifecycle promotion (`qualification.evaluate_promotion`) is a pure function of `(SourceSpec, SourceMetrics)` returning a `PromotionDecision`; persisting it (`apply_promotion`) is a separate, explicit call, and a stage moves at most one step per evaluation (with immediate one-stage demotion on `HealthStatus.DOWN`, independent of accumulated history). | Same "propose vs. decide" separation the charter uses everywhere else (agents propose, pipeline decides); one-step-at-a-time movement + immediate demotion means a bad recent signal outweighs a long good history, matching how trust is actually lost. |
| AD-21 | Binary payloads (PDF/Excel/images) are stored via `collectors.archive.RawArchive`, a content-addressed write-once blob store keyed by sha256, separate from `RawDocument.content_text` (which holds text formats inline); `RawDocument.is_binary` + the existing `content_hash` field is the pointer between them — no third id scheme. | Extends "never overwrite the raw archive" to formats that can't be embedded as text, without duplicating the identity scheme `RawDocument` already has. |
| AD-22 | `collectors.provenance_index.ProvenanceIndexRepository` records one versioned `ProvenanceRecord` per materialized value, keyed by `(artifact_type, key, record_date)`, written automatically by `CollectionService` for every price bar and macro observation (previously only news items carried a raw-document link, via event metadata). | "Every value inside AGX must trace back to source/collector/artifact/transformation/timestamp/hash/schema_version" needed to hold at the value level, not just the document level, for the charter's Provenance Layer requirement to be true rather than aspirational. |
| AD-23 | `collectors.archive_replay.ArchiveReplayCollector` implements the ordinary `Collector` interface (`fetch()` returns already-archived documents, `parse()` delegates to a real collector) rather than a bespoke replay method on `CollectionService`; `CollectionService.run()` is idempotent about re-adding an already-stored `RawDocument`. | Replay reuses every existing guarantee (quality scoring, provenance, health/reputation recording, materialization) for free instead of re-implementing a parallel path that could drift from the live one. |
| AD-24 | `TargetOrganization` (the Acquisition Intelligence Engine's input) carries identity (name/category/country/public brand-domain hints), never a URL; `domain_resolution.HeuristicDomainResolver` independently probes every hint and every name-derived guess before trusting a domain, and `config_generation.generate_source_spec`'s output `status` always stays `PLANNED`, never `IMPLEMENTED`, however high the composite score. | "The system must never require manually specified endpoints" needed to hold even for automation *acting on the user's behalf* — a human typing a URL into a config and an engine trusting an unverified domain are the same failure mode; both are closed by requiring an independent, successful probe before anything is trusted, and by keeping "found a legal method" structurally distinct from "collector is tested and ready" (`AD-16`). |
| AD-25 | Legality (`acquisition_intelligence.legality`) is a hard gate in ranking (`BLOCKED`/`AMBIGUOUS` candidates are excluded entirely, never score-weighted and reconsidered), and `AccessMethod.HTML_SCRAPE` can never resolve to `ALLOWED` regardless of robots.txt/ToS signal. | Mirrors the existing `TOS_REVIEW`/`NEEDS_KEY` convention ("ambiguity blocks") at the automated-discovery layer; scraping's charter status as last-resort-only would be silently eroded if a clean robots.txt alone could auto-clear it. |
| AD-26 | `AcquisitionContinuityMonitor` reacts only to `HealthStatus.DOWN` (set by the existing `sources.health.HealthMonitor` during real collection) and re-invokes the same `AcquisitionIntelligenceEngine.run_for_target`, excluding the failed URL, rather than maintaining a separate recovery code path or a ranked shortlist of backup methods kept on standby. | Re-running full discovery on failure is simpler and self-correcting (the web changes; a stale "backup" method chosen once might itself be dead by the time it's needed) and reuses every verification step instead of duplicating a weaker version of it. |
| AD-27 | `agx_research.production` is a new top-level package, not an extension of `orchestration/` or `runtime/`; its `ProductionPipeline` builds its own `MarketMemory` pointed at `--data-dir` (where its own Collector Execution stage materializes data) rather than reusing `cli.build_market_memory`, which is pointed at the separate, static `--mock-data` directory. | `orchestration`/`runtime` are the *research* orchestration layer specifically (Task Graph/Sessions/`DailyResearchPipeline`/`RuntimeEngine`); the production pipeline spans acquisition through dashboard/Mission Control, a genuinely broader integration concern. Reusing `build_market_memory` as-is would have kept collected data and research permanently disconnected — the exact gap this pipeline exists to close. |
| AD-28 | Mock and Replay execution modes are both implemented as the *same* real `Collector` subclasses (`StooqPriceCollector`, `FredCsvCollector`, `RssNewsCollector`, `WorldBankCollector`), differing only in what backs `fetch()`: a `MockFetcher` returning canned wire-format text, or an `ArchiveReplayCollector` reading previously-archived `RawDocument`s. Neither mode has its own parallel "fake collector" implementation. | The mission's own requirement — "the execution path must be identical to the future live path; only the data source changes" — is satisfied structurally: `CollectionService.run()` is called on a real `Collector` either way, so a live `HttpFetcher` swap-in later requires zero changes to `CollectionService`, `ProductionPipeline`, or any collector's `parse()`. |
| AD-29 | `ProductionPipeline.run()`'s per-stage wrapper (`execute()`) catches any exception a stage function raises, records it as a `FAILED` `StageResult` with the error message, and unconditionally continues to the next stage; stages needing a prior stage's output check for `None`/empty state explicitly and return `SKIPPED` with a reason rather than raising. `StageStatus.PARTIAL` exists for a stage that ran but only part of its own work succeeded (e.g. 3 of 4 collectors). | "One stage failing must not corrupt later stages" needed to be true even when a stage's *prerequisite* (not just the stage itself) failed — `SKIPPED`-with-reason is the honest signal for "nothing to do here," distinct from `FAILED`, so a report reader can tell "this stage broke" from "this stage had nothing upstream to work with." |
| AD-30 | Mission Control's `mission_status.json` (`production.mission_control.build_mission_control_status`) is computed entirely from `ExecutionReport`s already persisted in `PipelineExecutionRepository` — it holds no independent mutable state of its own. | "Last successful/failed pipeline" must always agree with the actual execution history; a separately-maintained status object could drift from it (e.g. after a manual data edit or partial failure) in a way a pure derivation over the same versioned repository every other store uses cannot. |
| AD-31 | `agx run` is repurposed to be the single production entrypoint (previously: only the research-pipeline day-range walk against static mock data); `cli.build_engine()` — whose only caller was the old `run` handler — was deleted rather than kept as an unused alternate path. | The mission's literal instruction ("create one production entrypoint... running this command must execute the entire pipeline") ruled out adding a second, parallel command; deleting the now-dead `build_engine` (and its now-unused imports) follows the "delete completely, don't leave unused code" convention rather than leaving a backward-compatibility shim nothing calls. |
| AD-32 | Project owner decision (2026-07-27): no paid/licensed data vendor of any kind, ever — not just the pre-existing no-`NEEDS_KEY` policy for the free registry. `data.provider.DataProvider`'s real-vendor seam and the `EGX market data vendor selection` roadmap item are both closed permanently, not merely deferred; every future data gap (including per-company fundamentals) must be closed exclusively through `sources`/`collectors`/`acquisition_intelligence`'s free, publicly-reachable, ToS-compliant sources. | Removes the platform's one remaining open business question about paid data; reduces "how do we get real EGX data" to a single, already-built path (free-source discovery/collection) instead of two parallel tracks, and rules out re-raising vendor cost/coverage tradeoffs in future sessions. |
| AD-33 | `discovery.wikidata_lookup.WikidataOfficialWebsiteClient` (Wikidata's public, no-key API, matched on its own declared `P856` "official website" property) is a second, independent hint source for per-company `company_ir` targets, alongside `discover_company_directory_links`, wired into `cli.py`'s `discover-sources` before `run_catalog`. A hint from either source still only ever seeds `TargetOrganization.domain_hints`; `HeuristicDomainResolver` independently re-probes it before anything is trusted, unchanged from AD-24. | `generate_company_ir_targets` deliberately supplies no hints and, until now, the only honest way to fill one required `egx_official` itself to already be reachable — a hard single point of failure discovered live (`egx_official` failed independent domain resolution on 2026-07-27's CI run despite being a genuinely live site, most likely anti-bot blocking). Wikidata's declared `P856` property is public structured data, not a guess from training-data recall, and needs no dependency on the exchange's own site being reachable at all — closing the single point of failure without weakening the "never assert a domain, always independently verify" rule. |
| AD-34 | `WikidataOfficialWebsiteClient` searches per company by display name (`wbsearchentities`, then `wbgetclaims` on the matched entity) instead of one bulk `P17`(country)=Egypt-filtered SPARQL query. | The original SPARQL design was live-verified working (2404 real results) but missed real, well-documented companies (Telecom Egypt, Commercial International Bank) outright — confirmed live by a targeted diagnostic showing neither ever appeared among 2404 "P17=Egypt" results, because `P17` is not reliably set on individual company items (organizations more often carry a headquarters location than a direct country statement). Searching by name asks Wikidata "what entity is this", not "what's tagged Egypt", sidestepping that data-modeling gap regardless of whether `P17` happens to be set. |
| AD-55 | `DecisionService.decide_portfolio()`'s `target_weight` now caps at `decision.max_position_pct` in addition to `self.max_position_weight` (matching `PortfolioConstructor.construct()`'s existing three-way `min()`), and a new `elif decision.publication_status != PublicationStatus.PUBLICATION_READY` branch surfaces the real gate's blockers as `reasons`/`abstained=True`; `cli.py`'s `decide` command now calls the real `apply_publication_gate()` (via a new shared `build_publication_gate_report()` helper deduped from `publication-status`'s own inline logic) before `decide_portfolio()`, rather than never applying the gate at all. | Found by the Investment Proof Framework mission directly exercising the CLI decision path: identical evidence sized a position ~6x larger through the position-aware path than through the already-correct `PortfolioConstructor` path, and every real `agx decide`/Decision Center call silently reported `no_action`/zero weight with no reason naming the cause — a real explainability defect (Rule 5), not just a sizing one. See TD-59. |
| AD-56 | New `shadow_fund/` package: a persistent, autonomous virtual portfolio (`ShadowFundLedger`, one continuously-versioned entity, `history()` doubling as the daily NAV time series) driven by feeding the fund's own prior-day state back into the existing, unmodified `DecisionService.decide_portfolio()` as `PositionState` — never a new decision engine, never a real investor's holdings. This is the one deliberate, documented exception to `decision_service/__init__.py`'s "never wire decision_service into a scheduled run" rule: that rule exists to stop a real investor's private position state from being fabricated/autonomously discovered, which categorically does not apply to the fund's own, fully platform-controlled, reproducible-from-inception state. Wired into `production.pipeline.ProductionPipeline._stage_dashboard_artifact_generator`, reusing the same `gated_recommendations`/`country_risk`/`illiquid_tickers` inputs `decision_ledger` already computes there. `capital_allocation.CapitalAllocationEngine.build()` is reused as-is for the fund's own capital-deployment/recycling view (never a second ranking mechanism). New declared, uncalibrated constants (`shadow_fund/engine.py`): `INCEPTION_NAV = 100.0` (a notional NAV-per-unit index convention, not a fabricated real capital figure), `REBALANCE_THRESHOLD_PCT = 0.01` (a weight move below this is treated as price drift, not a real rebalance, to avoid manufacturing daily transaction noise out of `decide_portfolio`'s continuous score wobble), `MIN_RISK_SAMPLE_DAYS = 20` (same honesty-gate posture as `DecisionPerformanceSummary.sample_status`); `DEFAULT_TRANSACTION_COST_BPS` is reused from `meta.decision_ledger` rather than re-declared. An abstained held ticker's `target_weight=0.0` is never treated as a real exit signal (mirrors `capital_allocation`'s existing exclusion rule) — the fund holds it unchanged instead of fabricating a liquidation nothing recommended. All `_pct`-suffixed fields are fractions (e.g. `0.0432` = 4.32%), matching every other `_pct` field in this codebase (`MAX_PRICE_ABOVE_FAIR_VALUE_PCT = 0.20`) and the shared `formatPercent()`/`formatSignedPercent()` frontend formatters, not pre-multiplied percentages. | Project owner mission (2026-08-01, "Zero-Cost Production Deployment" → "define Shadow Fund as the persistent portfolio state of the investment methodology"): the platform needed a real, continuously-tracked institutional-portfolio state (holdings, NAV, P/L, transaction/rebalancing/capital-deployment history, risk, attribution) as one of nine required daily-pipeline outputs, explicitly distinct from `meta.decision_ledger.DecisionLedger` (why decisions were made) and `investment_cases`/`investment_proof` (reasoning/validation) — "DecisionLedger becomes only one input to the Shadow Fund... the Shadow Fund is the owner of portfolio state," not a rename of the existing ledger and not a new NAV-only bolt-on. Growth is bounded by real trading activity (one snapshot per day, transactions only where the rebalance threshold is actually crossed), not by elapsed-time × universe-size — the specific axis that made `provenance_index.json` unbounded (TD-63) — but see TD-64 for what's still honestly open. |
| AD-57 | The platform's permanent production deployment architecture is static-only: GitHub Actions runs the complete daily research/decision/Shadow Fund cycle and publishes every result as static JSON consumed by GitHub Pages (`.github/workflows/deploy-pages.yml`, unchanged by this decision). No live backend is ever deployed for the public site — `StaticJsonProvider` throws `LiveDecisionsUnavailableError` synchronously, before any network request leaves the browser, so the deployed site issues zero POST requests and runs zero server-side Python/Node. Personalized, position-aware decisions (`agx decide`/`POST /decisions`, real holdings) remain a deliberate, permanent, local-only/self-hosted capability (`npm run dev -w api` + `DECISION_DATA_DIR`) — not a gap pending a future paid deployment. | Project owner mission (2026-08-01, "Zero-Cost Production Deployment"): explicitly forbids a VPS, paid hosting (Render/Railway/Fly.io named specifically), or any always-on backend, "while preserving the full investment workflow." A same-session exploration of a Render-hosted live `api/` (to make Portfolio's personalized-decision feature work on the public site) was abandoned mid-design once this mission superseded it — no code from that exploration was committed. This closes System 18's "cloud provider + payment" business-blocker permanently for the *public* deployment specifically (see `docs/PHASE_STATUS.md`'s System 18 entry) — it does not reopen or relax any other part of System 18 (secrets management, managed scheduling for `discover-sources`, monitoring/alerting), which remain open exactly as before. |
| AD-58 | Project owner direction (2026-08-02): the publication gate (`meta.publication_gate.evaluate_publication_gate`/`apply_publication_gate`) is replaced by three explicitly decoupled layers. (1) **Decision Quality** (`meta.decision_quality.evaluate_decision_quality`/`apply_decision_quality_gate`) — evaluated per ticker per horizon, directly against that decision's own `Explanation`/`HorizonDecision`: evidence present and traceable, thesis complete, confidence calculated, invalidation conditions defined, monitoring conditions defined, internal consistency (a `BUY_CANDIDATE` carries numeric entry/invalidation levels). This alone now determines `PublicationStatus.PUBLICATION_READY`. (2) **System Maturity** (`meta.system_maturity.compute_system_maturity`, new, non-blocking) — reports `early`/`validating`/`developing`/`established`/`verified` from the exact same `DecisionPerformanceSummary` math the old gate's 30-result/95%-confidence performance check used, purely as an informational credibility label; never gates anything. (3) **Publication Governance** (`meta.publication_gate.LegalPublicationApproval`, kept, unchanged shape) — an optional human sign-off that can only ever raise System Maturity's ceiling to `verified`, reserved for a future regulated/officially-published distribution mode; never read by, or blocking, `agx decide`/`agx run` (this platform's only mode today, which is research/personal-use). `ExternalPublicationEvidence`/`PublicationGateReport`/`evaluate_publication_gate`/`apply_publication_gate` and the `publication_evidence.json` input are deleted outright, not kept as unused code; `dashboard.validate`'s cross-artifact safety check now independently re-derives each shipped `publication_ready` decision's quality rather than trusting a separate global report file. `agx publication-status` now reports System Maturity and always exits 0. New dashboard artifact `system_maturity.json` (API route `GET /system-maturity`) replaces `publication_gate.json`. | The old gate required a human-authored legal-approval file *and* 30+ historical results outperforming EGX30 at 95% confidence *simultaneously*, system-wide, before *any* decision of *any* quality could ever size a position — neither condition had been satisfied once in this platform's history, so every decision stayed `RESEARCH_ONLY` regardless of completeness. The project owner's explicit correction, given directly in response to that finding: "the objective is not to prove the system permanently outperforms EGX30 before publishing decisions... publishing should be governed by decision quality... long-term performance should govern credibility, not permission to publish" — with a further refinement separating engineering (Decision Quality), investment methodology (System Credibility/Maturity), and operational compliance (Publication Governance) into three independent layers so they are never conflated again. This is not a loosening of the platform's anti-fabrication discipline — a decision still cannot publish without genuinely complete evidence, thesis, and internal consistency; what changed is that *completeness* is now the bar, not an unrelated system-wide track record or sign-off that could never accumulate without decisions publishing in the first place. |
