# Changelog

## Unreleased — EGX Investment Methodology (permanent investment doctrine)

The project owner declared the platform architecture complete and asked
for the investment methodology itself: a permanent constitution, a
market-situation playbook, exact decision/portfolio standards, and a
complete operational handbook — documentation-only by explicit
instruction, becoming the permanent governing doctrine for every future
decision. See `docs/PHASE_STATUS.md`'s "EGX Investment Methodology"
section for the full report.

**Delivered**: `docs/INVESTMENT_CONSTITUTION.md` (11 articles: why
invest/reject, when to hold cash/increase/reduce/exit, how capital is
allocated, how confidence and evidence are interpreted, how conflicts and
mistakes are handled — each grounded in a real, cited mechanism, never
free-floating policy); `docs/INVESTMENT_PLAYBOOK.md` (12 market
situations, each explicitly separating real mechanically-detected signals
from honestly-named doctrine awaiting a future detector);
`docs/DECISION_STANDARDS.md` (exact minimum bar for every one of the
six-way action labels plus Abstain); `docs/PORTFOLIO_STANDARDS.md`
(concentration/diversification/liquidity/cash/sizing/recycling rules);
`docs/INVESTMENT_HANDBOOK.md` (13-chapter rebuild-without-source-code
walkthrough with a full constant glossary).

**No code changed.** One real gap in the mission's own working
understanding — not in the platform — was caught while writing and
corrected before delivery: the prediction model's confidence aggregation
is a plain arithmetic mean, not a genuine confidence-weighted one (the
weight term mathematically cancels), and a separate, real, previously
undocumented event-driven risk-inflation/confidence-deflation mechanism
exists alongside it. Both documents state the real formula.

## Unreleased — Capital Allocation Intelligence

The project owner redefined the platform again: no longer a research or
decision system, a capital allocation system — every recommendation
competes for the same finite capital rather than being scored in
isolation ("is this the best use of capital available today?", not "is
this stock good?"). See `docs/PHASE_STATUS.md`'s "Capital Allocation
Intelligence" section for the full report, including the Mandatory Final
Review the mission required before declaring completion.

**Backend**: `PositionAwareDecision` gained 3 additive fields
(`opportunity_score`, `expected_return`, `expected_risk`) exposing
numbers `DecisionService.decide_portfolio()` already computed internally.
New `capital_allocation/` package (`CapitalAllocationEngine`) — a
read-only ranking/opportunity-cost/recycling layer strictly on top of
`decide_portfolio()`'s output: a global rank for every ticker it
evaluated, a deterministic capital-flow matcher (idle cash drawn before
any holding is displaced; the weakest-ranked holding displaced before a
stronger one), and a `CapitalAllocationPlan` (ranking, deployment queue,
capital released/recycled, best new opportunities, highest opportunity
cost, allocation changes, cash waiting). Caught and fixed a real bug via
its own tests before shipping: an abstained held ticker's `target_weight
=0.0` (no fresh evidence, not a decisive sell) was initially read as a
real capital release — fixed with `_effective_target()`. New `agx
allocate-capital` CLI command, sharing `decide`'s own setup via a new
`build_position_aware_decisions()` helper rather than duplicating it. 15
new tests; 855 backend tests pass; `ruff check` clean.

**API**: `POST /capital-allocation`, the same live-bridge shape as
`POST /decisions` (shells out to the CLI, no business logic in
TypeScript), sharing a new `runCli()` helper with `/decisions` rather
than duplicating the shell-out logic. 4 new tests; 31 `api` tests pass;
clean build.

**Frontend**: CIO Desk's "Today's Actions" section is now "Capital
Allocation," rendering the mission's 7 named sub-sections (Capital
Deployment Queue, Capital Recycling, Capital Released Today, Best New
Opportunities, Highest Opportunity Cost, Allocation Changes, Capital
Waiting For Better Opportunities) from a live `CapitalAllocationPlan`
when the investor has entered holdings, with an honest fallback (the
existing decisions table + a ranked model-portfolio preview) otherwise —
never fabricating a capital competition that doesn't exist without real
capital. New `postCapitalAllocation()` on `DashboardDataProvider`
(`ApiProvider` live; `StaticJsonProvider` always reports itself
unavailable, same posture as `postDecisions`). 4 new tests; 51 `web`
tests pass; clean `tsc`/build. Live-verified in English and Arabic/RTL
via headless Chromium against real demo data — all 7 sub-sections render
the platform's honest current state (an empty plan, since no real EGX
vendor is licensed yet), no overflow in either direction.

**Named, not silently left out**: the position-unaware CIO Desk fallback
(no holdings entered) deliberately does not get ranking/opportunity-cost/
recycling treatment — there is nothing real to displace or recycle
without real capital and real holdings, the same architectural boundary
`decision_service/` already lives by. `Portfolio.tsx` was not extended
with the same view in this pass (new TD-62).

## Unreleased — EGX-Genom Final Product Mission: Institutional Investment Operating System (IOS)

The project owner redefined AGX from a research platform into an
institutional-grade Investment Operating System: research becomes an
internal capability, investment decisions are the product. Explicit
Product Law (every screen answers exactly one primary investment
question), a mandated 5-section CIO Desk landing page and 19-section
Investment Case page, portfolio-aware thinking everywhere, a 7-item
navigation hierarchy with Research never the default destination, and a
mandatory product audit before completion — see
`docs/PHASE_STATUS.md`'s "EGX-Genom Final Product Mission" section for
the full report.

**Backend**: 3 new dashboard artifacts, each composing an existing
engine rather than adding new judgment logic — `dashboard.
portfolio_summary.build_portfolio_summary()` (wraps `investment_proof.
portfolio_validation.PortfolioValidationEngine`), `dashboard.monitoring.
build_warnings()` (new `WarningCategory` taxonomy: broken_thesis,
macro_risk_increased, catalyst_expired, liquidity_deterioration,
portfolio_concentration, review_required — scans the whole
`KnowledgeStore`, not just current positions, so a knowledge retirement
that drops a ticker out of the model portfolio is correctly surfaced),
`dashboard.committee_summary.build_committee_summary()` (wraps
`investment_proof.committee_validation.CommitteeValidationEngine`, adds
Risk/Portfolio committees + a mechanical CIO tally row). Wired into
`production.pipeline.ProductionPipeline`'s existing dashboard-artifact
stage, `None`-safe on non-trading days, schema-exported, 7 new tests. 840
backend tests pass (up from 833); `ruff check` clean.

**API**: `GET /portfolio-summary`, `GET /warnings`,
`GET /committee-summary` (thin passthrough, same pattern as every
existing route). Removed one confirmed-dead duplicate route
(`GET /ticker-data-gap-report`). 27 `api` tests pass; clean build.

**Frontend**: full navigation/page-hierarchy redesign. New pages —
`CIODesk` (landing page, `/`), `Portfolio` (`/portfolio`),
`InvestmentCases`/`InvestmentCaseDetail` (`/cases`, `/cases/:ticker`),
`Monitoring` (`/monitoring`), `Settings` (`/settings`, merging Mission
Control + System Administration). `ResearchCenter` extended in place to
absorb Decision Readiness/Data Coverage. Nav collapsed from 9 to 7
top-level items; Knowledge Graph/Source Intelligence stay reachable via a
"More Research Tools" link on Research rather than the primary nav.
Deleted outright (not kept as dead code): `AIBriefing`, `DecisionCenter`,
`OpportunityCenter`, `CompanyWorkspace`, `MissionControlPage`,
`SystemAdministration` (+ their CSS), and the already-dead
`ComingSoon.tsx`. New `usePortfolioPositions` localStorage hook backs
both CIO Desk's and Portfolio's "my holdings" state — the backend never
stores real portfolio data. i18n fully restructured (6 old namespaces
removed, 5 new ones added, bilingual EN/AR). 47 `web` tests pass; clean
`tsc`/build.

**Mandatory product audit** (per the mission's explicit requirement):
every screen, widget, nav item, API endpoint, and report reviewed against
"does this improve investment decisions?" One real gap named rather than
silently dropped or force-built: `getRuntimeStatus()`/`getSourceTruth()`/
`getEndpointCandidates()` remain unused by any page (TD-61).

**Live-verified** in a real running `api`+`web` dev server pair, English
and Arabic/RTL, via headless Chromium — including one real RTL CSS bug
found and fixed (`CIODesk.module.css`'s `.thesisCell`/`.riskCell` were
inline `<span>`s with a non-functional `max-width`, which has no effect
on `display: inline` elements; fixed with `display: block` + an explicit
`width` + ellipsis truncation, re-verified via `boundingBox()`/
`scrollWidth` that the page no longer overflows in either direction).

## Unreleased — Investment Proof Framework (Capital Trust Report)

The project owner's final mission for this phase: build the complete
architecture to prove — not just claim — that the platform's decisions are
trustworthy enough for capital, with the explicit instruction that missing
*data* (not missing *engineering*) should be reported as `READY FOR DATA`
rather than block the work.

**Delivered**: new `investment_proof/` package, composing rather than
duplicating `institutional_validation/` —

- `categories.py`: the Macro/Sector/Quality/Value/Catalyst/Risk/Liquidity/
  Portfolio/Execution/Technical taxonomy and the real `creator_agent ->
  Category` map every other engine below shares.
- `attribution.py` (`DecisionAttributionEngine`): decomposes a real
  `KnowledgeWeightedHorizonModel`+`FairValueEngine` expected return into
  named category contributions, with `attribution_residual` as a real
  reconciliation check (verified ~1e-18, i.e. exact).
- `counterfactual.py` (`CounterfactualEngine`): real ablation — removes
  each evidence category and recomputes the decision with the same real
  `MetaDecisionEngine`, reporting which categories are actually decisive
  rather than assumed important.
- `committee_validation.py` (`CommitteeValidationEngine`): aggregates
  attribution + counterfactual results across a ticker batch into
  per-category agreement/decisiveness rates; `historical_usefulness`
  honestly stays `ready_for_data` (see TD-59).
- `portfolio_validation.py` (`PortfolioValidationEngine`): Herfindahl
  concentration, sector exposure, weight reconciliation, an explicitly-
  named `expected_downside_proxy` (never presented as a true VaR), and
  position-aware vs. position-unaware decision-conflict detection.
- `stability.py` (`DecisionStabilityEngine`): calls
  `RecommendationService`/`DecisionService` multiple times against
  identical evidence and diffs the results — determinism measured, not
  claimed.
- `calibration.py` (`ConfidenceCalibrationFramework`): Brier score, a
  10-bin reliability curve, and expected calibration error over
  `DecisionLedger` records — honestly `sample_status="insufficient"`
  below a 30-record floor, never a fabricated statistic.
- `walk_forward.py` (`WalkForwardInfrastructure`): a real day-by-day
  driver connecting `RecommendationService` + `DecisionLedger` over the
  real EGX trading calendar (proven against 8 real mock trading days, 0
  errors); `required_datasets()` names exactly what real EGX history is
  still needed, each honestly `ready_for_data`.
- `thesis_survival.py` (`ThesisSurvivalEngine`): compares a
  `PositionAwareDecision` against a later re-evaluation of the same
  ticker, detecting broken assumptions (cited knowledge later retired),
  new contradicting evidence, and lapsed catalysts — mechanically, never
  a sentiment guess.
- `capital_trust.py` (`InvestmentProofEngine`/`CapitalTrustReport`): the
  top-level orchestrator. Runs `institutional_validation` plus every
  engine above against one shared scenario and answers "would a rational
  institutional investment committee trust this system with capital?" as
  YES/NO/PARTIALLY, computed mechanically from the dimension verdicts
  (any FAIL -> NO; any BLOCKED with no FAIL -> PARTIALLY; otherwise YES).

New `agx investment-proof` CLI command (JSON + optional Markdown Capital
Trust Report, same `--out`/`--markdown-out` shape as `validate-investment`).

**Current verdict: PARTIALLY.** Every dimension that can be exercised
today (decision determinism, attribution, counterfactual ablation,
committee agreement, portfolio consistency, thesis-break detection) is
architecturally complete and passes; `confidence_calibration` and
`walk_forward_backtest` remain `BLOCKED` only for lack of real historical
EGX data (a licensed vendor is still a pending business decision — see
`CLAUDE.md`). No fabricated data or invented statistic stands in for
either gap.

**Two real, pre-existing production bugs found and fixed** while building
this framework's own attribution/decide checks (not by the framework
itself, but by directly exercising `DecisionService`/`agx decide` the way
this mission required): (1) `DecisionService.decide_portfolio()` never
capped `target_weight` at `decision.max_position_pct`, so identical
evidence could size a position ~6x larger through the position-aware path
than through `PortfolioConstructor`; (2) `agx decide` never called
`apply_publication_gate()` at all, so every CLI/Decision-Center decision
silently reported `no_action`/zero weight with no reason naming the real
cause. Both fixed; see `docs/ARCHITECTURE_DECISIONS.md` (AD entry) and
`docs/TECHNICAL_DEBT.md`.

833 backend tests pass (up from 809, 24 new); `ruff check` clean.

## Unreleased — Institutional Investment Validation framework

The project owner redefined the mission from engineering implementation to
proving, with real evidence, that the decision engine is internally
consistent, explainable, and economically meaningful — 10 named
questions, answered by repeatable scenarios that attempt to falsify the
platform's own conclusions, not more passing software tests.

**Delivered**: new `institutional_validation/` package (deliberately
separate from System 11's statistical hypothesis validator) —
`scenarios.py` (deterministic builders exercising real
`RecommendationService`/`PortfolioConstructor`/`DecisionService`/
`ContinuousLearningMonitor`/`DecisionLedger` against both the real
101-ticker EGX30+EGX70 universe and clearly-labeled synthetic stress
data), `diffing.py` (a genuinely new capability Q9 revealed was missing —
`diff_knowledge_history()`, built on existing versioning, scoped honestly
to knowledge only), `checks.py`/`report.py`/`runner.py` (PASS/PARTIAL/
BLOCKED/FAIL per question with concrete evidence, never a bare boolean),
and a new `agx validate-investment` CLI command.

A real scenario-construction bug was found and fixed by the framework's
own falsification attempt during development (hand-setting
`publication_status` without going through the real
`apply_publication_gate()` silently zeroed `max_position_pct`, making
every synthetic buy portfolio-ineligible) — caught because
`check_complete_portfolio` refused to accept 26 positions summing to a
0.0 weight. The platform code itself had no defect; the test scenario did.

Current report: 4 PASS, 4 PARTIAL, 1 BLOCKED, 0 FAIL, overall PARTIAL —
two new named, scoped gaps (TD-57: `ContinuousLearningMonitor` not
autonomously wired; TD-58: no real EGX30 index-level price series to
benchmark against). 807 backend tests pass (up from 788, 21 new); `ruff
check` clean. See `docs/PHASE_STATUS.md`'s matching section for the full
report.

## Unreleased — Market Regime classification (trend/volatility), wired end to end

Immediate follow-up to the decision-object work below: the mission brief's
landing-page checklist names "current market regime" explicitly, and it
was a confirmed real gap (no `MarketRegime` model/artifact anywhere in
`research/src/`).

**Closed**: new `market_memory.regime.compute_market_regime()`, built the
same way `market_memory.breadth.compute_market_breadth()` already is
(adjusted, equal-weighted returns, no live lookups). Reports `trend`
(bullish/bearish/neutral) and `volatility` (low/elevated/high) as two
independent axes rather than one fused label, per this codebase's existing
"a label over a continuous number, never a lookup table" discipline.
Declared, uncalibrated thresholds (new debt TD-56). Wired end to end like
Market Breadth: `market_regime.json` (every `agx run`) → dashboard
validator → `GET /market-regime` → both `DashboardDataProvider`s → a new
banner on the AI Briefing landing page and a real card on Market
Intelligence (previously a permanent empty state). 788 backend tests pass
(up from 778, 10 new); 24 `api` tests pass; 46 `web` tests pass; all three
workspaces' `build`/`lint` clean; verified live end to end in a real
headless browser. See `docs/PHASE_STATUS.md`'s matching section.

## Unreleased — complete the decision object's 12 mandated fields; make it reachable from the web

Audited `decision_service.PositionAwareDecision` against the mission's
full institutional-decision field list (Decision, Target Weight, Horizon,
Confidence, Thesis, Supporting/Contradicting Evidence, Key Risks, Active
Catalysts, Monitoring Events, Invalidation Conditions, Expected Review
Date) and found 6 of 12 missing, plus a separate, larger gap: the service
was completely unreachable from `api/`/`web/` (CLI-only).

**Closed**: added `horizon`, `investment_thesis`, `key_risks`,
`contradicting_evidence`, `active_catalysts`, `monitoring_events`, and
`expected_review_date` to `PositionAwareDecision`, each derived from data
already computed or newly threaded through `decide_portfolio()`
(`corporate_events`, `knowledge_store` — both optional, honest-empty when
omitted), never fabricated. New `POST /decisions` route in `api/` shells
out to the same `agx decide` CLI on each request (on-demand, never
autonomous — `decision_service` still must never enter a scheduled run);
new web page **Decision Center** (`/decisions`) lets an investor enter
their own holdings and get the full six-way decision, linked prominently
from the AI Briefing landing page. `StaticJsonProvider` honestly reports
itself unavailable (no live backend on GitHub Pages) rather than
fabricating a result. 778 backend tests pass (up from 764, 12 new); 23
`api` tests pass (4 new); 46 `web` tests pass (7 new); all three
workspaces' `build`/`lint` clean; verified live end to end in a real
headless browser against a real mock-mode `agx run`. See
`docs/PHASE_STATUS.md`'s matching section for full detail.

## Unreleased — fix a malformed guessed hostname crashing the whole acquisition sweep

While expanding free source coverage (this session triggered
`discover-sources.yml`'s full ~101-company EGX30/EGX70 acquisition sweep
via real GitHub Actions egress), the run failed outright 56 minutes in.
Fetched the real job log directly (the raw-log blob-storage host isn't in
this coding sandbox's egress allowlist, so used the GitHub MCP server's
`get_job_logs` instead of a direct fetch) and found the real traceback: one
company's name-derived guessed domain produced an empty/too-long IDNA
label, and `socket.getaddrinfo` raised a bare `UnicodeError` that
propagated straight past `collectors.fetcher.HttpFetcher.fetch_bytes()`'s
retry loop (`UnicodeError` isn't an `OSError` subclass, so it wasn't
caught by the existing `except (OSError, TimeoutError)` clauses) and
crashed the entire sweep — losing all prior progress, since
`discover-sources.yml` deliberately persists nothing mid-run.

**Closed**: `fetch_bytes()` now also catches `UnicodeError` in both the
primary attempt and the Windows-certificate-trust fallback path, so a
malformed hostname reports as an ordinary per-target fetch failure
(`FetchError`, already correctly handled by `acquisition_intelligence.live
.build_live_prober`) instead of crashing the caller — the same class of
defensive fix as the earlier `UnicodeEncodeError`-on-non-ASCII-URLs and
unbounded-robots.txt-timeout bugs this module has already been hardened
against. 1 new regression test (`test_http_fetcher.py`); 770 backend
tests pass (up from 769); `ruff check` clean.

## Unreleased — fix source promotions silently not reaching an already-running deployment

**Real bug found while verifying the Amwal Al Ghad promotion below**:
after merging and deploying it, real persisted `source_registry.json`
still showed `amwal_alghad` at version 1, `status: planned`,
`base_url: null` — the promotion had zero effect on the live deployment.
Root cause: `sources.catalog.seed_registry()`'s add-loop only adds a
brand-new source id; it never revisits one that already exists, so a
catalog-level field change (status, base_url, collector, ...) for an
*already-persisted* source never reaches a deployment that had already
seen that source before the edit — the exact sibling gap to AD-53's
retire-on-deletion fix, this time for updates. Every prior source
promotion in this codebase's history likely only worked because that
source had never yet been persisted when first declared `IMPLEMENTED`;
this is the first time an already-persisted `PLANNED` source was promoted,
and it exposed the gap immediately.

**Closed**: new `sources.registry.SourceRegistry.sync_declared_fields()`
reconciles the catalog's declared fields (status/access_method/base_url/
collector/collector_version/category/notes) into any already-persisted
source whose values differ, via a new revision — never an edit or
deletion. Runtime-measured fields (health_status/data_quality_score/
reputation_score) are always preserved untouched; `lifecycle_state`/
`activation_status` are only re-derived from the new status when status
itself actually changed, so a source's own qualification-pipeline-earned
lifecycle stage is never reset by an unrelated catalog edit. Wired into
`seed_registry()` alongside `retire_removed()`. Verified directly against
the real, already-broken persisted registry: `amwal_alghad` now correctly
reconciles to `IMPLEMENTED`/`TRUSTED`/`ACTIVE` with its real base_url and
collector. See AD-54.

5 new tests (`test_source_registry.py`); 769 backend tests pass (up from
765); `ruff check` clean.

## Unreleased — Amwal Al Ghad promoted to IMPLEMENTED via real verified discovery

Project owner request: expand free source coverage for the universe.
Rather than guess at new endpoints, triggered the two workflows this
codebase already built for exactly this purpose but that no prior session
had actually run to completion from here: `discovery.yml`
(workflow_dispatch) and `discover-sources.yml` (the full per-company
acquisition sprint), both using real GitHub Actions network egress this
coding sandbox doesn't have.

**Real result**: `discovery.yml`'s run (866s, 23 sources checked) found 3
`verified_reachable` results. Two were already-known/stale (`african_markets_egx`
is a deliberate company-directory hint source with no standalone collector
planned; `skynews_arabia_economy`'s cached "reachable" entry carries 0.0
confidence and no successful probe, consistent with its prior documented
404). The third, **`amwal_alghad`**, was a genuinely fresh result
(`from_cache: false`, confidence 0.875): `https://amwalalghad.com/feed/atom/`
— robots.txt permits it, a live probe succeeded, and the Wayback Machine
shows 143 archived snapshots spanning 1229 days.

**Closed**: promoted `amwal_alghad` from `PLANNED` to `IMPLEMENTED`
(`sources/catalog.py`, `RssNewsCollector`, matching Enterprise/Al Borsa/
Masrawy's exact precedent), added its decision route
(`production/decision_lineage.py`) — it was already present in
`CAPABILITY_STRATEGIES[Capability.NEWS]`'s candidate pool from a prior
phase, so no capability-mapping change was needed. Following this
codebase's own established practice (Enterprise's original promotion),
real content parsing is confirmed by the next live production run rather
than a separate manual check; will revert to `PLANNED` immediately if
that run shows zero real items, the same self-correction
`skynews_arabia_economy`'s own history already went through once.

1 new regression test (`test_amwal_alghad_is_implemented_with_a_real_verified_feed_url`);
765 backend tests pass (up from 764); `ruff check` clean.

## Unreleased — fix the FairValueEngine's shares-outstanding over-gating (with an honest caveat)

Project owner request: "A reliable fair value cannot be computed from
current inputs" shows for real tickers — find the bug and fix it so the
correct number shows.

**Real bug found and fixed**: `valuation.engine.FairValueEngine.value()`
nested its `ddm` (dividend discount) and `pe` (P/E multiple) models inside
`if shares and shares > 0:`, even though neither formula actually divides
by `shares` — dividend-per-share and EPS are already per-share figures.
Moved both out of that gate so a source reporting EPS or DPS directly
(without ever stating total share count) no longer loses two computable
models to an unrelated precondition.

**Honest caveat, verified against real persisted production data, not
assumed**: this fix has **zero observable effect today**. `value()`
still requires ≥3 of 7 models to agree before returning a result, and only
2 of the 7 (`ddm`, `pe`) can ever compute without `shares_outstanding` — no
combination of currently-collectable fields reaches 3 without it. Worse,
inspecting the real data found the deeper, dominant cause: only 2 of 101
tickers (ETEL, ORAS) have *any* financial-statement line items collected
at all, and both only carry 3-4 raw metrics from a quarterly highlights
press release (revenue/ebitda/net_income/free_cash_flow) — never share
count, EPS, dividend-per-share, equity, cash, debt, or operating income.
Making a real number appear for any of these tickers needs real collected
data this platform doesn't have yet, not a code fix — inventing one would
violate the platform's core anti-fabrication principle. New debt: TD-55.

4 existing `test_fair_value_engine.py` tests still pass unchanged (no
regression); 764 backend tests pass; `ruff check` clean.

## Unreleased — fix the real reason no investment decision was ever reachable, and retire dead sources for real

Project owner review of the live dashboard: no clear investment decision
was reachable, some catalogued sources still looked unconnected, and some
sources still looked like they add no value. Investigated against the
real persisted production state (`production/state-latest`) rather than
mock data — two real, previously-undetected engineering bugs found and
fixed, not data/business blockers:

- **The DATA_COLLECTION-starvation bug (AD-52).** `ProductionPipeline`
  passed a hardcoded `lookback_days=30` (calendar days) for every mode's
  standard `price_history`/`corporate_events`/`news` window — the window
  every agent and the hypothesis pipeline's DATA_COLLECTION gate actually
  sees. EGX trades Sun-Thu (5 of 7 days), so 30 calendar days yields only
  ~19-21 real trading days, strictly below
  `orchestration.pipeline.PipelineConfig.min_observations = 60` — a
  structural ceiling no amount of real accumulated history could ever
  cross. Confirmed directly against real data: COMI alone has 118 real
  collected trading days (2026-01-28 to 2026-07-30), yet **every one of
  777 real hypotheses recorded in production had failed DATA_COLLECTION**
  with only 19-21 aligned observations each. Re-running the real research
  pipeline against the real, already-collected data reproduced this
  exactly (0 of 337 findings passed DATA_COLLECTION at the old window);
  with a new LIVE-mode-only `LIVE_PRICE_LOOKBACK_DAYS = 180`
  (`production/collector_plan.py`, deferred through `ProductionPipeline`
  the same way `LIVE_MACRO_LOOKBACK_DAYS`/`LIVE_PATTERN_LOOKBACK_DAYS`
  already are), the identical real data produced **5 genuinely promoted
  `KnowledgeObject`s**, reaching PEER_VALIDATION. MOCK/REPLAY keep the
  original 30-day window unchanged — no test fixture or assertion
  affected. New debt: TD-53 (180 days is a declared, uncalibrated
  margin-above-the-floor choice, not a measured optimum).
- **The dead-source-that-never-actually-died bug (AD-53).** The Decision-
  Centric Redesign's "registry cleanup" (removal of 11 sources with zero
  capability mapping) deleted them from `sources/catalog.py`'s code, but
  `seed_registry()` only ever *adds* an id it doesn't already know about —
  it never removes one no longer in the catalog. Diffing the real
  persisted `source_registry.json` against the current catalog found
  exactly those same 11 ids still present, 9 of them still `PLANNED`
  months later: the code shipped, but no already-running deployment ever
  saw it take effect. New `sources.registry.SourceRegistry.retire_removed()`
  transitions any such id to `DISABLED`/`RETIRED` via a new revision
  (never an edit or deletion — full history intact), wired into
  `seed_registry()` so it runs on every pipeline execution going forward.
  Verified directly against the real registry: all 9 correctly retired
  with a clear reason in `notes`, while still-catalogued sources
  (`fred`, `global_benchmarks`, `rss_generic`, provider legs) were left
  completely untouched. New debt: TD-54 (this only catches outright
  catalog deletions, not a still-catalogued source silently orphaned from
  every capability's candidate pool).
- 6 new backend tests (4 in `test_source_registry.py`, 2 in
  `test_production_pipeline.py`, plus assertions added to an existing
  test); 764 backend tests pass (up from 758); `ruff check` clean.

The remaining complaint (some sources are still unconnected) is not a new
engineering gap: it's the same, already extensively evidenced state this
project has documented across many prior missions (`docs/ACQUISITION_STRATEGY.md`,
`docs/TECHNICAL_DEBT.md`) — most `PLANNED` sources are blocked by real
network/ToS/anti-bot walls or a named business decision (a licensed
vendor, explicitly declined per AD-32), not a code gap this session could
close without fabricating a connection.

## Unreleased — Market Breadth artifact (advance/decline + volume breadth)

Closes the last named item from `NEXT_MISSIONS.md`'s "genuinely next,
engineering-closeable" list that wasn't gated on external evidence or a
business decision: a market-wide breadth/liquidity rollup, derivable
entirely from already-collected Price Data. Also closes the Market
Intelligence page's own named honest gap ("Breadth and liquidity require a
backend-computed artifact... this platform doesn't export yet").

- New `market_memory.breadth.compute_market_breadth()` / `MarketBreadthReport`:
  per-day advancers/decliners/unchanged, advance/decline ratio, average
  daily return, and above-/below-trailing-average-volume counts, derived
  from a reconstructed `MarketState` — return calculations go through
  `data.adjustments.adjusted_dated_returns()`, never raw
  `[bar.close for bar in bars]`, per `CLAUDE.md`'s standing rule.
- Wired into `production.pipeline.ProductionPipeline._stage_dashboard_artifact_generator`
  as a new, optional `market_breadth.json` artifact (`None` until a
  `MarketState` has actually been reconstructed, the same honest-absence
  convention `runtime_status.json` already uses); validated by
  `dashboard.validate.validate_dashboard_artifacts`.
- `api`: new `GET /market-breadth` route + `ArtifactsReader.marketBreadth()`.
- `web`: `DashboardDataProvider.getMarketBreadth()` (both `ApiProvider` and
  `StaticJsonProvider`); Market Intelligence's "Market Breadth & Liquidity"
  card now renders real advancers/decliners/unchanged/ratio/average-return/
  volume-breadth stat tiles instead of an empty-state placeholder,
  bilingual EN/AR. Market Regime remains an honest gap (no classification
  artifact exists upstream).
- New declared, uncalibrated constant: `TRAILING_VOLUME_WINDOW_DAYS = 20`
  (TD-52) — a conventional trading-month length, not derived from a real
  EGX volume-distribution study, same posture as every other declared
  threshold in this codebase.
- 7 new backend tests (4 in `test_market_breadth.py`, 2 in
  `test_production_artifacts.py`, 1 in `test_production_pipeline.py`, plus
  assertions added to 2 existing pipeline tests), 1 new api test, and a
  web fixture update (`App.test.tsx`'s fake provider); 758 backend tests
  pass (up from 751), `ruff check` clean; `api` (19 tests, up from 18) and
  `web` (41 tests) build and test suites green.

## Unreleased — expose price-vs-fair-value as an explicit decision-quality criterion

Project owner request: make the fair-value engine's average distance from
the current price into one of the criteria that determines the quality of
a ticker's current price for the decision, not just a silently-blended
research input.

- `meta.readiness.DecisionReadiness` gained `price_vs_fair_value_pct`
  ((current close − `FairValueEngine.value().weighted_fair_value`) /
  weighted_fair_value, `None` when no fair value could be computed) —
  reuses the existing seven-model, ≥3-method weighted-average fair value
  engine (see the native fair-value evidence entry below) rather than
  building a new calculation.
- New declared threshold `MAX_PRICE_ABOVE_FAIR_VALUE_PCT = 0.20` (AD-51/
  TD-51): when the current price sits more than 20% above the calculated
  fair value, INVESTMENT-horizon readiness is now blocked with an explicit
  reason ("Current price is +NN% vs. the calculated fair value (weak entry
  quality).") in both the per-horizon and overall blocker lists — extending
  the existing readiness gate, not adding a parallel one.
- `meta.recommendation_service.RecommendationService`'s existing fair-value
  blend (20% weight into INVESTMENT `expected_return`) now also states the
  gap explicitly in its evidence text: "current price=X is +Y% vs. fair
  value", alongside the fair value figure and the models it was averaged
  from.
- Web: `DecisionReadiness`'s new field is rendered as a "Price vs. Fair
  Value" column on Opportunity Center's Decision Readiness table
  (color-coded: red when the price is above fair value, green when below),
  bilingual EN/AR.
- 3 new backend tests (`test_decision_readiness.py` x2 covering the
  blocked/not-blocked cases, `test_runtime_and_intelligence.py` x1
  verifying the evidence text and expected-return blend); 751 backend
  tests pass (up from 748); `ruff check` clean; `api`/`web` build and test
  suites (18 + 41 tests) unaffected except the new column/types.

## Unreleased — native fair-value evidence

- Ported the Smartlist IVE V2 calculation method—not its results—into a native,
  point-in-time seven-model AGX engine with TTM, robust blending and scenarios.
- Investment readiness now depends on a calculable fair value rather than statement
  count; available value carries a 20% research-only investment-horizon weight.

## Unreleased — fix hardcoded Arabic backend prose (investor walkthrough)

Investor-perspective walkthrough (project owner request, Arabic: "put
yourself in an investor's place opening the system"): a live headless-browser
pass through the AI Briefing, Opportunity Center, and Company Workspace pages
against a real mock-mode `agx run` (748 backend tests, `ruff check`, `npm run
build`/`test` for `api`/`web` all verified green first) surfaced a genuine,
previously-unnoticed bug distinct from any already-documented data gap:
`meta.publication_gate`, `meta.readiness`, and `meta.decision_engine` had
hardcoded Arabic-language strings baked directly into `PublicationGateCheck.label`/
`blocker`, `DecisionReadiness.blockers`/`horizon_blockers`, and
`Explanation.why_this_stock`/`why_now`/`why_not_others`/`entry_condition`/
`review_condition`/`abstention_reasons` — a direct violation of this
codebase's own documented rule (`CLAUDE.md`, "Bilingual EN/AR dashboard"
section) that free-form backend-generated prose stays English so the
i18next layer is the only place translation happens. In practice this meant
an English-mode user saw raw untranslated Arabic mixed into the Publication
Gate card and every ticker's readiness blockers/decision explanation — the
exact "why can't I get a decision" text a fund manager opening the platform
would read first. `test_meta_decision_engine.py` even had a test asserting
the language *was* Arabic (`test_executable_decision_language_is_arabic`),
confirming this was a deliberate but incorrect prior choice, not an
accidental leak.

Fixed: translated every hardcoded string in the three files to English,
preserving exact meaning/thresholds/currency figures; renamed the test to
`test_executable_decision_language_is_english` and updated its and
`test_decision_readiness.py`'s assertions to the new English substrings;
updated a misleading `cli.py` comment that claimed the publication-status
report "intentionally contains Arabic" (it no longer does — the comment now
describes the encode-fallback generically) and `test_infrastructure.py`'s
matching cp1252-encoding regression test, which no longer has a non-ASCII
character to exercise incidentally. Deliberately left untouched:
`collectors/corporate_event_classifier.py`'s Arabic keyword list, which
correctly matches *real Arabic-language news headlines* (Enterprise/FRA/Al
Borsa/Masrawy) rather than generating prose — not the same rule at all.
Verified live in a headless browser in both English and Arabic UI modes
against real mock-run artifacts: the Publication Gate card, ticker
readiness blockers, and Opportunity Center now render entirely in English
regardless of dashboard language, matching the documented bilingual design
(UI chrome translates via i18next; backend prose stays English in both
modes). 748 backend tests pass (2 renamed/updated); `ruff check` clean;
`api`/`web` unaffected (no dashboard-facing schema change).

## 0.40.2 — Close free-data gaps: currency-series-id fix, drop unreliable FRED live dependency

Project owner direction (2026-07-31, following an investor-perspective
walkthrough): delete dependency on sources that are legally free but
operationally blocked, and fix genuine implementation gaps rather than
paper over them. Two real bugs found and fixed (TD-50 has the full detail):

- `decision_service.country_risk`'s country-risk-data-presence check
  hardcoded the mock fixture's currency-series id (`EGP_USD`), which never
  matched real production's actual World Bank series id
  (`egypt_official_fx_egp_per_usd`) -- every real LIVE run reported "no
  currency data" even though the FX series had been collected
  successfully every time. New `resolve_currency_series()`/
  `has_sufficient_currency_data()` recognize both ids; `meta.readiness`
  reuses the same resolver instead of its own copy (AD-49). Verified
  directly against real persisted `production/state-latest` data: now
  correctly reports `DETERIORATING` (EGP moved +8.67% over the real
  lookback window) where it previously reported nothing at all.
- `fred` removed from the live `MACROECONOMIC` capability pool and from
  `production.collector_plan`'s live-wired source set (AD-50): 3
  consecutive real live runs timed out fetching it, and zero FRED series
  ever appear in real persisted production data -- it was never actually
  a working live dependency. `FredCsvCollector`, its `SourceSpec`
  (`IMPLEMENTED`, legally cleared), and its own unit tests are untouched;
  only the live capability ranking stopped depending on it.
- `agents.macro._SERIES_MECHANISMS` gained real production series ids
  (`DCOILBRENTEU`, `egypt_official_fx_egp_per_usd`, etc.) so real findings
  get a real mechanism sentence instead of a generic fallback.
- 5 new regression tests; 741 backend tests pass; `ruff check` clean.

Explicitly out of scope (confirmed, not silently skipped): paid-only
sources (consensus estimates, forward EGP rate, CDS spreads, full rating
reports, XBRL) and already-`DISABLED` free-but-blocked sources
(`egx_official`, `cbe`, `imf`, `yahoo_finance`, `mubasher`, `investing_com`)
needed no code change -- they were already structurally un-depended-upon
by `SourceStatus != IMPLEMENTED` refusing collector construction. Real
sector/peer-comparison data and a working sovereign-rating collector
remain genuine, undisguised gaps -- closing them needs either real network
egress to verify a source, or a verified source appearing; fabricating
either would violate this platform's anti-fabrication discipline.

## 0.40.1 — Fix a real live-deployment incident: three cascading production-pipeline crashes

`deploy-pages.yml` run #92 (2026-07-31, commit `ce1a8a6`) failed on merge
to `main`. Root-caused against the actual persisted production state, not
assumed, and fixed same day (TD-49 has the full detail):

- Restored `SourceCategory.ALTERNATIVE` in the enum. 0.40.0 removed it as
  dead weight in the seed catalog, but real, already-persisted
  `source_registry.json` state (the `production/state-latest` branch)
  has real historical revisions carrying that category -- removing the
  enum member broke deserializing them. Never remove an enum value real
  persisted data depends on; only stop emitting new records with it.
- Fixed `ProductionPipeline._stage_investment_case_generator` calling
  `self._tickers(as_of)` before checking `as_of is None` -- any run whose
  entire requested range fell on non-trading days (this incident: a
  single day landing on an EGX Friday) crashed instead of skipping
  cleanly. Pre-existing bug, unrelated to 0.40.0, that simply never
  triggered until a scheduled run happened to land on a real non-trading
  day with no other date in range.
- Fixed `_stage_dashboard_artifact_generator`'s financial-coverage export
  passing a possibly-`None` `as_of` into a report that requires a real
  date -- same pre-existing bug class, fixed with the `as_of or end`
  fallback the same stage already used elsewhere, just not consistently.
- 2 new regression tests (`test_legacy_alternative_category_still_deserializes`,
  `test_entire_range_on_non_trading_days_skips_investment_cases_instead_of_crashing`);
  736 backend tests pass; `ruff check` clean. Verified by reproducing all
  three failures directly against the real persisted production data tree
  and confirming each fix resolves it, not just by reasoning about the
  code.

## 0.40.0 — Decision-Centric Redesign: position-aware Decision Service + real FinancialPerformanceAgent

Full implementation of the roadmap four research/architecture documents
(`docs/DECISION_CENTRIC_AUDIT_2026-07-30.md` →
`docs/FREE_DECISION_DATA_BLUEPRINT.md` → `docs/DECISION_EVIDENCE_MATRIX.md`
→ `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md`) settled on, with continued
adversarial scrutiny during implementation itself.

- **`decision_service/`** (new package): the position-aware layer between
  promoted knowledge and a Buy/Increase Position/Hold/Reduce Position/
  Exit/No Action action. `DecisionService.decide_portfolio()` computes a
  continuous target weight per ticker (extending `PortfolioConstructor`'s
  existing scoring) and derives the six-way action as a label from
  target-vs-current weight -- never a discrete lookup table.
  `country_risk.assess_country_risk()` classifies Country & Macro Risk
  severity (NORMAL/DETERIORATING/CRISIS); `CRISIS` requires a real,
  discrete `SovereignRatingAction`, never inferred from a currency move
  alone. `liquidity_floor.compute_illiquid_tickers()` is a second,
  symmetric hard override for tradability. Deliberately its own package,
  never a stage inside the autonomous daily pipeline. Exposed as a
  read-only, on-demand `agx decide --date ... [--positions
  positions.json]` CLI command.
- **`agents.financial_performance.FinancialPerformanceAgent`** is real:
  revenue-growth-trend and leverage-trend findings from a new
  `DatasetSnapshot.financial_statements` field (populated via a new
  optional `financials_provider` parameter on `build_snapshot()`/
  `MarketMemory`). All 8 of 8 Scientist Framework agents are now real.
- **`meta.readiness.assess_decision_readiness`** extended with a
  liquidity-floor blocker (all horizons) and a country-risk-currency-
  data-presence blocker (INVESTMENT, checking specifically for `EGP_USD`
  coverage) -- reusing the same `decision_service` mechanisms, not a
  second parallel gate.
- **Registry cleanup**: removed 11 sources with zero mapping in
  `acquisition_intelligence.capability.CAPABILITY_STRATEGIES`
  (`wikipedia_pageviews`/`google_trends`/`github_releases`/
  `company_social_official`/`public_telegram`/`patents`/`hiring_signals`/
  `google_scholar`/`researchgate`/`investing_com`/`tradingview`), which
  also emptied and removed `SourceCategory.ALTERNATIVE`. Merged
  `Capability.ECONOMIC_RELEASES` into `MACROECONOMIC`. Added
  `moodys_ratings`/`sp_global_ratings`/`fitch_ratings` (Sovereign & Credit
  Context) and `amwal_alghad` (Egypt-specific news) as new `PLANNED`
  sources and `TargetOrganization` candidates.
- 41 new tests (`test_country_risk.py`, `test_decision_service.py`,
  `test_capability_catalog.py`, plus new cases in existing files); 734
  backend tests pass; `ruff check` clean.
- See `docs/PHASE_STATUS.md`'s "Decision-Centric Redesign implementation"
  section for what deliberately deviated from the prior documents under
  further scrutiny, and `docs/MISSION_COMPLETION_REVIEW.md` for the final
  full-system review.
## 0.39.0 — GDELT evidence-tier gate: discovery-only, never independent evidence

Project owner direction after inspecting the real backfilled content
(0.38.0's successful run collected 14,984 articles, but only ~3.8%
mentioned Egypt): GDELT must never independently become evidence. Every
GDELT event must resolve to an independent PRIMARY source (Enterprise,
FRA, Al Borsa, Masrawy, company IR, official announcements) before it
counts.

- **`sources.spec.EvidenceTier`** (`PRIMARY`/`DISCOVERY`): a new
  `SourceSpec` field. `gdelt`'s catalog entry is now `DISCOVERY`-tier.
- **`collectors.service.CollectionService`** now routes a DISCOVERY-tier
  source's news items to `news_discovery.csv` instead of `news.csv`, and
  never registers them with the Event Platform directly -- structural,
  not a downstream filter an agent could bypass. `_append_news` split
  into `append_news`/`append_discovery_news` (shared `_append_news_to`
  helper) to serve both paths.
- **`collectors.discovery_reconciliation.reconcile_discovery_news()`**:
  the only promotion path. A discovery candidate becomes a real
  `news.csv` row only once a PRIMARY source independently reports the
  same ticker within a tolerance window (default 2 days). Wired into
  `ProductionPipeline`'s Event Platform stage, runs every `agx run`, and
  a new `agx reconcile-discovery-news` CLI subcommand for manual/one-off
  runs.
- **Tightened GDELT's default query** (daily-live and backfill) to
  require an Egypt term AND a finance term, cutting the same
  false-positive class the query itself can address.
- **Reprocessed the already-collected historical batch** (PR from
  0.38.0): filtered 13,463 raw articles down to 284 genuinely
  Egypt-relevant headlines; ticker re-resolution was attempted but
  proved unreliable (`EAST`/`ARAB` collide with common English words,
  a real false-positive bug filed as TD-42) so tickers are left empty
  rather than propagate a false attribution. Renamed the PR's
  `news.csv` to `news_discovery.csv` to match the new architecture.
- `docs/TECHNICAL_DEBT.md` (TD-41 updated, TD-42/TD-43 new),
  `docs/ROADMAP.md` updated accordingly.

## 0.38.0 — GDELT historical backfill: per-window resilience + widened rate limit

A third live re-trigger of `news-history-backfill.yml` refined the 0.37.1
evidence: window 1 succeeded this time, window 2 hit HTTP 429 -- proving
GDELT's throttle is real per-request cadence, not an outright IP block,
and exposing a real bug: `GdeltDocCollector.fetch()` collected every window
into one list and only returned it at the end, so one failed window
discarded every already-fetched window's real data.

- `GdeltDocCollector`'s historical mode now catches a per-window failure,
  records it in `self.fetch_warnings` (same posture as `FredCsvCollector`'s
  per-series resilience), and continues to the next window -- raising only
  if every single window fails. New tests cover skip-and-continue and the
  all-fail case.
- `gdelt`'s `SourceSpec.rate_limit` widened from 5 req/min (12s) to 2
  req/min (30s), a bounded adjustment motivated directly by the observed
  failure point (not a blind guess).
- `docs/TECHNICAL_DEBT.md` (TD-41) updated with the refined evidence.

## 0.37.1 — Document real GDELT 429 evidence from the fixed backfill workflow

The 0.37.0 fix was re-verified live: re-triggering `news-history-backfill.yml`
now fails loudly (as intended) instead of silently reporting success —
GDELT's DOC 2.0 API returned HTTP 429 Too Many Requests on the very first
windowed historical request, all 3 retries still 429. Not our own client
pacing (this was the first request of the run); likely GDELT rate-limiting
the shared GitHub Actions IP range, or a stricter real quota on bulk
historical queries than assumed. Documented as evidence in TD-41 rather
than guessed at with an unverified "fix" — no `news-history/latest`
branch/PR exists yet; `research/data/news_history/` stays empty pending a
successful run.

## 0.37.0 — Close TD-40: daily cross-run persistence; fix news-history-backfill bug

Project owner approval to proceed with the TD-40 fix flagged in 0.36.0.

- **`deploy-pages.yml` gains real cross-run persistence**: `--data-dir`
  changed from an ephemeral `/tmp` path to `data/production`, restored
  from and force-committed back to a dedicated `production/state-latest`
  branch around each run (same restore/commit discipline `discovery.yml`
  already used, auto rather than PR-gated — this is accumulated
  operational state, not evidence for human review). Every calendar day's
  research cycle now builds on yesterday's promoted knowledge/genome/event
  history instead of starting empty.
- **Same-date dedup guard**: `RuntimeEngine.run_day` has no built-in
  same-date dedup (by design, for replay/backfill), so persistence alone
  would let a same-day double trigger (e.g. the daily `schedule` plus a
  same-day `push`) duplicate a date's hypotheses/knowledge. A new step
  checks the restored `RunRecordRepository` for an existing `SUCCEEDED`
  run for today's date and, if found, skips the rest of the `build` job
  and the `deploy` job entirely rather than rebuilding/republishing
  redundantly.
- **Real bug found and fixed in `news-history-backfill.yml`**: its first
  real run (2026-07-29) silently collected zero articles. `--data-dir` was
  placed after the `collect` subcommand instead of before it (a global
  `argparse` argument added before `add_subparsers()` in `cli.py`, not a
  `collect`-specific one) — `agx: error: unrecognized arguments` was
  raised and then swallowed by an unguarded `| tee` (no `pipefail`), so the
  step falsely reported success. Fixed (argument order corrected,
  `set -o pipefail` added) and verified locally against a real invocation.
- `docs/TECHNICAL_DEBT.md` (TD-40 closed, TD-41 updated), `docs/ROADMAP.md`,
  `docs/PHASE_STATUS.md` updated accordingly.

## 0.36.0 — GDELT historical news backfill; daily cross-run persistence gap named

Project owner request: with no paid data vendor (permanent per AD-32),
investigate why the platform produces few confident recommendations and
collect/employ real old news.

- **Root-cause finding (TD-40)**: the daily production pipeline
  (`deploy-pages.yml`'s `agx run --mode live`) has no cross-run
  persistence — it runs against an ephemeral `/tmp` data directory with no
  restore/commit step, unlike `discovery.yml`. Every calendar day starts
  from an empty knowledge store/genome/event repository; real multi-year
  price history is refetched fine, but promoted knowledge and news/event
  history never carry from one day to the next. Flagged as the highest-
  leverage engineering-closeable gap (`docs/ROADMAP.md`), pending
  project-owner sizing given its repo-growth/CI-behavior implications —
  not implemented in this change.
- **`GdeltDocCollector` historical backfill mode** (TD-41): real
  windowed `startdatetime`/`enddatetime` queries (`start_date`/`end_date`/
  `window_days`), going around GDELT DOC 2.0's 250-articles-per-response
  cap, alongside the existing relative `timespan` daily-live behavior
  (unchanged). Wired into `cli.py collect --source gdelt` and a new
  `.github/workflows/news-history-backfill.yml` (`workflow_dispatch`,
  real network egress, review-gated PR into `main` under
  `research/data/news_history/`, same discipline as `discovery.yml`).
  Tested with fakes (windowing, cross-window dedup); not yet wired into
  the production data-dir the daily pipeline reads (see TD-40/41).

## 0.35.0 — Retire evidence-dead-end PLANNED sources, no-paid-services enforced

Project owner request: the dashboard's Source Intelligence page showed
dozens of sources stuck at `PLANNED`/`TOS_REVIEW` indefinitely with no
visible progress. Audited every non-`IMPLEMENTED` catalog entry against
the concrete live evidence already gathered across prior sessions
(`docs/ACQUISITION_STRATEGY.md`) and today's automated weekly discovery
run (`research/data/discovery/discovery_report.json`, 2026-07-29).

- **10 sources moved `PLANNED` -> `DISABLED`**, each with a notes
  citation of its specific dead-end evidence rather than a generic label:
  `egx_official` (TCP reset, network-level anti-bot), `cbe` (WAF
  rejection page), `imf` (403 on every real DataMapper indicator probed),
  `yahoo_finance`/`tradingview`/`investing_com` (quoted ToS
  prohibition/403), `mubasher` (robots.txt disallow), `stockanalysis`
  (redundant standalone entry -- already live as an `egx_price_composite`
  leg, no separate collector was ever going to be built), `investing_news`
  (same domain as the already-403'd `investing_com`), and
  `trading_economics` (free tier insufficient for real use -- per the
  existing no-`NEEDS_KEY`/no-paid-service policy that already removed
  FMP/AlphaVantage/Polygon/Tiingo, a source whose only real path is a
  paid subscription does not stay `PLANNED`).
- Genuinely still-open `PLANNED` sources (no documented permanent block
  yet -- the ~28 remaining outlets/APIs/research feeds the weekly
  Discovery workflow keeps retrying with real network egress) are
  unchanged; `PLANNED` now means "actively re-attempted," not "abandoned."
  `egid_financial_filings` stays `TOS_REVIEW` (a genuine legal-ambiguity
  case needing the issuer's own confirmation, not an engineering dead end).
- `docs/DATA_ACQUISITION.md`'s status-policy section documents this
  convention: `DISABLED` for a source with repeatable dead-end evidence or
  a paid-only requirement, reversible by a human once the real blocker
  clears -- never silent deletion, the spec and its evidence stay in the
  versioned registry.
- Verified `discovery_report.plan_discovery_targets()` already filters to
  `status == PLANNED` only, so the 10 newly-`DISABLED` sources are
  automatically excluded from future weekly re-probing with no code
  change needed there.
- 682 backend tests pass (one assertion updated for `egx_official`'s new
  status/reason text); `ruff check` clean.

## 0.34.0 — EGX30+EGX70 Financial Source Registry (TD-39)

Follow-up to 0.33.0: build a per-company Financial Source Registry
(Investor Relations, financial statements, quarterly/annual reports,
source type, collector recommendation) on the existing `SourceRegistry`/
`JsonFileRepository` architecture, resumable and incremental.

- **New `discovery.financial_document.classify_financial_document()`** —
  generic, keyword-based classification of a discovered link into annual
  report / quarterly report / financial statements / presentation /
  disclosure / investor-relations home.
- **New `discovery.engine.discover_financial_documents()` /
  `DiscoveryEngine.scan_financial_documents()`** — reuses the existing
  page parser; no discovery logic duplicated.
- **New `discovery.company_financial_registry.CompanyFinancialSourceRegistry`**
  — one resumable, versioned record per company. `is_resumable_skip()`
  only skips `VALIDATED` companies, so re-runs never restart completed
  work.
- **New `discovery.company_financial_discovery.discover_company_financial_sources()`**
  — fetch → scan → classify → recommend a collector
  (`acquisition_intelligence.config_generation.suggest_collector`), one
  real `HttpFetcher` attempt per company.
- **New `scripts/build_financial_source_registry.py`**, wired into
  `.github/workflows/discovery.yml` (same `discovery/latest` bot branch
  and weekly schedule as the existing source-discovery job; PR summary
  extended to report registry coverage).
- **Run for real against all 101 EGX30+EGX70 companies this session**:
  0 `DISCOVERED`/`VALIDATED`, 26 `BLOCKED` (real fetch attempts, real
  proxy-403 evidence), 75 `HOMEPAGE_UNRESOLVED`. The mechanism is
  complete; the data needs a real run with network egress (queued in
  `.github/workflows/discovery.yml`). See `docs/TECHNICAL_DEBT.md` TD-39.
- 680 backend tests pass (16 new); `ruff check` clean.

## 0.33.0 — EGX30 company domain-hint coverage (TD-38)

Project owner request to resume large-scale EGX30/EGX70 company source
discovery, scoped (with confirmation) to extend the existing
`acquisition_intelligence`/`discovery` architecture rather than a parallel
system:

- **New `discovery.web_search_hints.load_web_search_domain_hints()`** — a
  third, independent `domain_hints` source for
  `acquisition_intelligence.target.generate_company_ir_targets()`,
  alongside `discovery.wikidata_lookup` and `discover_company_directory_links`
  (TD-28). Reads a reviewed, evidenced snapshot
  (`research/data/universe/egx30_web_search_domain_hints.json`) built from
  real, live web searches for each EGX30 company's own name — 26/31
  tickers resolved with a citable source; 5 (EGCH, HELI, MCQE, OIH, PHDC)
  deliberately left unresolved rather than guessed.
- Wired into `cli.py`'s `discover-sources` command, applied only to
  tickers Wikidata's structured `P856` claim didn't already resolve.
  Nothing from this source is trusted directly — `HeuristicDomainResolver`
  still independently probes every hint before anything is registered.
- **Not yet run live**: the sandbox this was built in denies outbound
  connections to arbitrary external hosts (confirmed directly against
  `egx.com.eg`/`cibeg.com`/`fawry.com`/`telecomegypt.eg`/`wikidata.org`/
  `archive.org`), so the actual domain-resolution/legality/stability/
  historical verification this feeds still needs a real
  `agx discover-sources` run in an environment with network egress. See
  `docs/TECHNICAL_DEBT.md` TD-38 and `CURRENT_MISSION.md` for full detail.
- 664 backend tests pass (4 new); `ruff check` clean.

## 0.32.1 — Supporting Evidence cleanup, part 2: id prefixes and duplicate lines

The 0.31.2 `humanizeEvidence()` fix only handled inline `key=value` pairs;
real production output showed it was still incomplete for real
opportunities -- raw internal id prefixes, bare tokens, and duplicated
lines were all still visible on the live site. This closes every remaining
gap, purely at render time (no backend evidence string changed):

- **`hyp_<id> v<N>:` and `event event_<id>:` prefixes** (every
  `KnowledgeWeightedHorizonModel` evidence line opens with the raw
  `KnowledgeObject`/`Event` id -- real provenance, unreadable to a person)
  are now relabeled to `Knowledge: ` / `Event: `.
- **Bare `micro:`/`swing:`/`investment:` horizon prefixes** (from
  `MetaDecisionEngine`'s per-horizon evidence lines) are now title-cased.
- **Bare snake_case tokens with no `=`** -- an event's `.subtype`
  (`large_price_move`, `macro_news`) appended straight after its
  headline -- are now humanized the same way `key=value` pairs are.
- **Exact-duplicate evidence lines** are gone from both Opportunity Center
  and Company Workspace. `MetaDecisionEngine` concatenates each horizon
  prediction's full evidence list when combining them into a
  `Recommendation`, so a knowledge object or event supporting more than
  one horizon had its lines repeated verbatim; the list is now
  deduplicated at render time (`dedupeEvidence()`), order-preserving,
  before display.
- Verified against a real mock-mode dashboard export with production-shaped
  evidence strings, in a real browser, in both English and Arabic (RTL).

## 0.32.0 — Council review follow-through: disclaimer, surfaced rationale, priority ordering

Five independent review passes (data sources, decision clarity, value,
content structure, audience/risk) against the live dashboard's actual
source code surfaced one critical and several high-value, zero-backend
fixes, all implemented here:

- **New `Disclaimer` primitive**, shown on every page that displays a
  concrete decision (AI Briefing, Opportunity Center, Company Workspace):
  "AGX is an autonomous research scaffold, not a licensed investment
  advisor..." -- previously there was no investor-facing disclaimer
  anywhere in the product, the single largest trust/legal gap the audit
  found.
- **Backend-computed rationale now actually reaches the screen.** AI
  Briefing's "Top Opportunities" table shows each recommendation's
  `explanation.why_this_stock` under its ticker; the Portfolio section
  shows the portfolio-level `explanation.why_this_stock` as a "Why this
  allocation" summary. Both fields already existed in every artifact --
  the UI was discarding them.
- **Honest-abstention empty states, not blank ones.** When there are
  zero opportunities/portfolio positions but knowledge objects exist and
  are being monitored, the empty state now says so explicitly ("Monitoring
  N knowledge object(s) -- none has cleared the promotion bar yet")
  instead of implying the pipeline hasn't run.
- **AI Briefing reordered**: System Health and Changes Since Yesterday
  (operational/meta content) move from the top of the page to the bottom,
  so Market Summary, Top Opportunities, and Portfolio -- the sections an
  investor actually opens the page for -- lead.
- **Decision Readiness table now ranks by proximity to a decision**
  (ready → degraded → blocked, ticker as tiebreak) instead of raw backend
  insertion order.

## 0.31.2 — Human-readable Supporting Evidence

Agent/pipeline evidence strings (`ResearchFinding.evidence`, threaded
unchanged into `KnowledgeObject`/`Explanation.supporting_evidence`) are
internal `snake_case_key=value` notation by design -- the right shape for
every agent/gate to parse, but it read as symbol noise ("macro_correlation=
0.532", "directional_agreement=100.00%") in the dashboard's Supporting
Evidence lists. New `lib/format.ts#humanizeEvidence()` reformats each
inline `key=value` it finds into "Key: value", leaving any surrounding
free text (a headline, a stress-test note) untouched. Applied everywhere
`supporting_evidence` renders: Opportunity Center's evidence panel and
Company Research Workspace's investment thesis. New `test/format.test.ts`
covers single/multi-pair/embedded/free-text shapes.

## 0.31.1 — Rank opportunities by expected return, not confidence

Both places the dashboard lists discovered opportunities -- the AI
Briefing's "Top Opportunities" widget and the Opportunity Center's main
table -- now sort by `combined_expected_return` descending (highest
expected return first) instead of by confidence. Matches how an investor
actually wants candidates ordered: confidence is still shown per row (and
still gates whether a recommendation exists at all), it just no longer
decides row order. Updated the matching EN/AR copy ("Ranked by expected
return, highest to lowest").

## 0.31.0 — HistoricalPatternsAgent: real analog-matching over live long-history

Closes the last data-blocked half of System 08's `HistoricalPatternsAgent`
stub. It turned out to be a methodology gap, not a data gap: LIVE mode's
`egx_price_composite` collector already returns full history (Yahoo
`range=max`) on every run, but every agent shared one 30-day
`DatasetSnapshot` window. `data/snapshot.py` gains `pattern_lookback_days`
(default 0, opt-in) populating a new `long_price_history`/
`long_corporate_events` pair — the same "one field needs its own window"
precedent `macro_lookback_days` already set for macro series, not a
redesign of the shared snapshot. `MarketMemory`/`ProductionPipeline` thread
it through; LIVE mode requests `LIVE_PATTERN_LOOKBACK_DAYS` (~4 years),
mock/replay stay at 0 (their fixtures are far too short regardless).

`HistoricalPatternsAgent` itself: for each ticker, mean-centered Euclidean
distance between the most recent `window`-day adjusted-return path and
every non-overlapping earlier window in its own history selects the
`top_k` closest historical analogs; each analog's actual subsequent
`forward_horizon`-day return is the "what happened next" evidence. A
finding is proposed only when at least `min_analogs` exist *and* they
agree in direction beyond `agreement_threshold` — anything weaker is an
honest skip, never a forced signal. `contracts/market_state.schema.json`
regenerated; `api/src/types.ts`/`web/src/types.ts` updated to match.

Verified: a hand-built synthetic fixture with a bit-for-bit repeating
20-day pattern produces the exact expected 5/5 analog match and 100%
directional agreement; a variant with alternating pattern outcomes
correctly abstains (3/5 agreement, below threshold). Full mock-mode `agx
run` re-verified against the pre-change baseline: identical output.
622 Python tests green (was 616), `npm run lint`/`build`/`test` clean for
both `api` and `web`.

## 0.30.0 — Free daily automatic refresh (GitHub Actions cron)

`.github/workflows/deploy-pages.yml` gains a `schedule:` trigger (`30 15
* * 0-4` UTC — after EGX's Sun-Thu close) alongside its existing
push/`workflow_dispatch` triggers. The dashboard now re-runs the full live
production pipeline and redeploys once a day automatically, at zero cost
(GitHub Actions cron is free for a public repository) and with no
deployment target or paid scheduler required. Closes the GitHub-Pages half
of ROADMAP.md's "Schedule `agx run` itself" item; a hosted `api/`'s own
periodic refresh (TD-14) still needs a real deployment target, unchanged.

## 0.29.0 — Bilingual EN/AR dashboard with full RTL layout

The web dashboard is now bilingual: an EN/AR toggle in the top bar
(`LanguageToggle`) switches the whole UI, persisted to `localStorage` and
seeded from `navigator.language` on first visit. Backed by `i18next`/
`react-i18next` with one JSON namespace per page under
`web/src/i18n/locales/{en,ar}/`.

Arabic renders full RTL (`dir="rtl"` on `<html>`, driven by
`i18n/index.ts`'s `applyDocumentDirection`), achieved almost entirely
through CSS logical properties (`inset-inline-start/end`,
`padding-inline-start/end`, `border-inline-end`, `text-align: start/end`)
rather than per-component RTL overrides — only 7 stylesheets needed
physical-to-logical conversions across the whole `web/src` tree. Numeric
and ticker data (prices, percentages, IDs, dates) always render LTR via a
new `.num` utility class (`direction: ltr; unicode-bidi: isolate;`),
matching real Arabic financial-dashboard convention; a `useFormatters()`
hook forces `numberingSystem: "latn"` so locale-aware date formatting
never switches to Eastern Arabic numerals.

Translation scope is deliberately bounded, following this project's own
"never fabricate" principle: UI chrome and closed backend vocabularies
(the `Horizon`/`Decision`/`SourceStatus`/... unions in `web/src/types.ts`,
translated via a new `useEnumLabel()` hook with a safe title-case
fallback for any value the dictionary doesn't cover) are translated.
Free-form backend-generated content — explanations, evidence, news
headlines, notes, company names, macro series ids, financial-statement
line items — stays English, since translating those would require either
fabricating financial/legal Arabic terminology or a backend
LLM-translation feature that doesn't exist.

## 0.28.0 — `ticker_data_gap_report.json` web/API wiring (TD-34)

Closes the last purely-engineering item on the post-freeze punch list.
The backend artifact (`meta.readiness.build_ticker_data_gap_report`) was
correct and tested but had no route, provider method, TS type, or UI
surface. Wired following `financial_statements.json`'s exact existing
pattern: `api/src/artifactsStore.ts`/`routes/dashboard.ts`
(`GET /ticker-data-gap-report`), `web/src/data/{DataProvider,ApiProvider,
StaticJsonProvider}.ts`, `web/src/types.ts` (`TickerDataGapReport`/
`DataLayerGap`).

UI: Opportunity Center's "Decision Readiness" table gained `onRowClick`
paired with a new "Data Coverage" detail card — the same click-to-select
pattern the Opportunities table above it already uses — showing the
5-layer completeness breakdown, blockers, and next actions per ticker.

Verified in a real headless browser against a real mock-mode `agx run`
output served through a production Vite build: clicking a Decision
Readiness row correctly populates the detail panel. `npm run lint`/
`build`/`test` clean for both workspaces.

## 0.27.0 — Monte Carlo stress simulator (block bootstrap)

Closes the one Experiment Factory gap docs had explicitly named as a
design decision rather than a data blocker: `MonteCarloExperiment` had
been a `NotImplementedError` placeholder since System 10 was built. New
`validation.stress_test.MonteCarloBlockBootstrapStressTester` stays
faithful to the existing stress tester's "locate/derive from real data,
never simulate" philosophy — every simulated path resamples contiguous
blocks of the hypothesis's real observed returns with replacement
(preserving real autocorrelation, unlike `BootstrapExperiment`'s
single-observation resampling), never a parametric distribution.

`MonteCarloExperiment` is now a real adapter over this tester (mirroring
`StressTestExperiment`'s shape); `DailyResearchPipeline`'s STRESS_TEST
gate now requires both the historical worst-window and the Monte Carlo
tester to pass. Verified: an identical mock-mode run produces the same 5
hypotheses as before this change.

8 new tests (616 total, up from 608); `ruff check` clean.

## 0.26.0 — Macro frequency alignment + no-look-ahead discipline

`MacroAgent` aligned macro observations to trading days by exact date
equality, silently starving every lower-frequency series (monthly/
quarterly/annual) of correlation evidence since their dates almost never
land on a trading day. Fixed with `agents/macro.py`'s
`_forward_fill_onto()` — standard last-observation-carried-forward step
alignment, never assigning a change to a trading day before the
observation that produced it.

Separately, nothing distinguished a macro value's `observation_date`
(the period it describes) from when it actually became known —
real look-ahead bias. New `data/point_in_time.py` (`is_knowable`) applies
a declared, deliberately conservative per-source publication-lag floor
(new debt TD-37); `data.snapshot.build_snapshot()`'s new
`macro_series_sources` param drops any not-yet-knowable observation
before it reaches an agent, wired in `ProductionPipeline` for LIVE mode
only (mock/replay default to no filtering change).

An initial 365-day World Bank/UN SDG lag assumption was caught
contradicting this codebase's own live-verified evidence (a real
collected observation only ~165 days old) before merging — scaled back
to a 30-day floor.

8 new tests (608 total, up from 600); `ruff check` clean.

## 0.25.0 — Real entity resolution for news-to-ticker matching

`RssNewsCollector`/`GdeltDocCollector` attributed news to a ticker via a
bare case-insensitive substring check (`ticker.lower() in
title.lower()`) — the exact "VLMR matches inside VLMRA" false-positive
risk named in the project owner's own completion plan. New module
`universe/entity_resolution.py` (`resolve_ticker_mentions`) fixes this:
ticker matching is now a real word/token match, and when a real company
display name is available, the full name is matched too via the same
conservative "every significant token present" discipline
`discover_company_directory_links()` already uses (shared
`significant_tokens()` helper, not a parallel implementation).

`production.pipeline.ProductionPipeline._ticker_companies()` threads real
company names from `research/data/universe/EGX30.csv`/`EGX70.csv` (the
already-reviewed, EGX-sourced 101-ticker seed with real English names and
ISINs) through `collector_plan.build_collector_plan`/`build_live_collector`
into both news collectors, so live/mock runs get genuine entity
resolution, not a ticker-only guess. Both collectors stay backward
compatible with a plain `ticker_hints: list[str]` for callers with no
company-name data (still upgraded from substring to exact-token
matching). No Arabic alias list yet — no verified Arabic-language EGX
source exists in this codebase (new debt, TD-36); inventing
transliterations would risk a wrong match, worse than a missed one.

8 new tests (600 total, up from 592); `ruff check` clean.

## 0.24.0 — NewsIntelligenceAgent: real news sentiment now produces findings

`agents.news_intelligence.NewsIntelligenceAgent` was an honest
`NotImplementedError` stub since System 08 was built, correctly deferred
because no real Egyptian news flow existed to research. That stopped being
true once `enterprise_press`/`fra_egypt` started producing real, dated
`NewsItem` records every live run (see `docs/PHASE_STATUS.md`'s "Egyptian
Live Data Sprint" phase) — this was the most directly-unblocked stub in
the codebase, named explicitly in `NEXT_MISSIONS.md`.

Implemented as a real, mechanical event-study-lite, mirroring
`CorporateEventsAgent` exactly: `agents.news_sentiment.classify_headline_sentiment()`
is a declared, headline-only keyword heuristic (positive/negative phrase
lists, negative checked first) — the same honesty tier as
`collectors.corporate_event_classifier`, never a fabricated NLP/sentiment
score (new debt, TD-35). For each ticker's sentiment-classified news item
with enough return history on both sides, the agent compares mean adjusted
return after the item to before it and proposes a MICRO-horizon
post-news-drift hypothesis when the shift clears a threshold. Wired into
`production.pipeline.ProductionPipeline`'s Research Pipeline stage
alongside the other five real agents.

Building this surfaced and fixed a real, previously-latent bug:
`collectors.service._append_news` was the only per-record materialization
writer that blindly appended instead of merging idempotently by natural
key (unlike prices/macro/corporate-events/index-constituents) — collecting
the same feed twice (e.g. a mock run followed by a replay run reading the
same archive) silently duplicated every news row. Harmless while nothing
consumed `news.csv` for hypothesis generation; caught immediately once
`NewsIntelligenceAgent` did, via `test_production_pipeline.py`'s existing
mock/replay-determinism test (5 vs. 7 hypotheses on the same input). Fixed
by merging on `(date, source, headline)`, matching every sibling writer.

24 new tests (592 total, up from 568); `ruff check` clean.

## 0.23.0 — Macro data now reaches the decision engine in live runs

A live production run's `investment_cases.json` showed all 62 published
recommendations at MICRO horizon only, and the Macro Dashboard showed all
23 `LIVE_MACRO_SERIES_IDS` (FRED/World Bank/UN SDG) with zero observations.
Root cause: `_stage_market_memory` used one `lookback_days=30` window for
prices, news, corporate events, *and* macro series — but World Bank/UN
SDG report annually (often with a 1-2 year publication lag) and CAPMAS
monthly, so an annual observation almost never falls inside the last 30
days. Since `DailyResearchPipeline` (the agents feeding the Meta Decision
Engine) reconstructs from this exact same snapshot, `MacroAgent` — the
only agent that turns macro data into SWING-horizon knowledge — had
nothing to correlate against in any live run.

`data.snapshot.build_snapshot()` now takes an independent
`macro_lookback_days` (default: `lookback_days`, so mock-mode callers are
unaffected); `DatasetSnapshot` gained the field so the window actually used
is explainable, not just assumed. `MarketMemory` and `ProductionPipeline`
thread it through; LIVE mode uses a new `LIVE_MACRO_LOOKBACK_DAYS = 900`
constant. Also closed a separate, independent gap: `LIVE_CAPMAS_INDICATORS`'
local ids were never added to `LIVE_MACRO_SERIES_IDS` at all, so CAPMAS
data was structurally excluded regardless of window size.

This does not create SWING/INVESTMENT recommendations by itself — it
removes the specific reason `MacroAgent` was structurally starved of data.
INVESTMENT horizon still has no agent implemented at all
(`FinancialPerformanceAgent` remains an honest `NotImplementedError`,
blocked on a fundamentals data source).

`contracts/market_state.schema.json` regenerated; `api/src/types.ts` and
`web/src/types.ts` updated to match. 4 new/extended backend tests; 584
backend tests pass.

## 0.22.0 — TargetOrganization entries for 14 previously-untargeted sources

The first real, live `agx discover-planned-report` run (2026-07-27, manual
`workflow_dispatch`) reported 20 catalogued `PLANNED` sources as
`not_targeted`. Of those, 14 have a single, unambiguous, publicly-known
organization domain (the same category of public knowledge already used
for every existing target — Reuters is reuters.com, CBE is cbe.org.eg —
independently re-verified for reachability before anything is trusted,
never asserted): IMF, OECD, Egypt's Ministry of Finance, Egypt's Open
Data portal, the Suez Canal Authority, Investing.com, TradingView,
Google Trends, the Wikimedia Foundation, arXiv, SSRN, NBER, Google
Scholar, ResearchGate.

The remaining 6 (`github_releases`, `company_social_official`,
`public_telegram`, `patents`, `hiring_signals`, plus `company_ir`'s own
per-constituent marker) stay untargeted on purpose: each names more than
one candidate organization or is inherently per-company/per-channel
(which of EPO vs. WIPO, which Telegram channel, which company's own
career page) — picking one for the catalog would be exactly the kind of
guess this program's own rules forbid.

Reduces the report's `not_targeted` count from 20 to 5 (`company_ir`'s
marker is separately, correctly excluded). 568 backend tests pass; `ruff
check` clean.

## 0.21.0 — Surface already-computed data the dashboard was hiding

The project owner reviewed the live Mission Control and Source
Intelligence pages and found real, already-computed backend data with no
frontend path to it at all.

- **Mission Control's Collectors table**: added a "Breakdown" column
  (`collector_status.json`'s per-record-type counts -- price bars, macro
  observations, news, corporate events, index constituents, financial
  statement line items -- previously collapsed into one summed "Yield"
  number), a "Withheld" column (quality-rejected batches, previously
  shown nowhere), and a "Reputation" column (the composite score,
  previously computed but never rendered).
- **Source Intelligence's Reputation Dimensions**: added the 3 of the
  charter's 9 dimensions that were computed (`compute_reputation()`) and
  typed but never rendered (`correction_rate`, `duplicate_rate`,
  `historical_usefulness`), plus a "Composite Reputation" stat tile for
  the overall score.
- **Weekly Discovery workflow wired into both pages** (previously zero
  frontend path at all): new `discovery_report.json`/`discovery_metrics.json`/
  `endpoint_candidates.json` types, `DashboardDataProvider` methods,
  `ArtifactsReader`/API routes, `StaticJsonProvider`/`ApiProvider`
  implementations. Mission Control gets a new "Weekly Discovery" section
  (metrics + per-source verification table); Source Intelligence's detail
  panel gets a "Discovery Evidence" block for the selected source, when
  available. `deploy-pages.yml` copies the three files from
  `research/data/discovery/` into the dashboard data directory if present
  (a plain file copy -- they're already final-shaped JSON committed by
  the Discovery workflow's PR, not reprocessed); an honest empty state
  renders until the first such PR merges.
- `npm run build`/`test` clean for both `api` and `web` workspaces.

## 0.20.0 — Weekly Discovery workflow

Closes "dozens of sources stay PLANNED, waiting on network egress" for
real: this dev sandbox has none, but the GitHub Actions production
deployment does, and nothing was scheduled to use it for discovery until
now.

- New `acquisition_intelligence/discovery_report.py`: `plan_discovery_targets`
  scopes the catalog to `PLANNED`/`CANDIDATE` sources with a real
  `TargetOrganization`, excluding per-constituent markers and provider
  legs already wired via `integrated_via`; `run_discovery_report` runs the
  existing `AcquisitionIntelligenceEngine.run_for_target` (unmodified —
  its own qualification-pipeline promotion already applies) with a
  TTL + input-fingerprint incremental cache; `build_discovery_metrics`
  aggregates counts. 9 new tests, all fake-backed.
- New CLI subcommand `discover-planned-report` writing
  `discovery_report.json`/`discovery_metrics.json`/`endpoint_candidates.json`.
- New `.github/workflows/discovery.yml`: weekly cron + `workflow_dispatch`,
  entirely separate from `deploy-pages.yml` (never blocks or slows the
  production deploy). Commits evidence only to a dedicated `discovery/latest`
  branch and opens/updates one PR against `main` — never a direct commit,
  never an automatic `SourceSpec.status` flip.
- New `research/data/discovery/README.md`; new
  `research/scripts/build_discovery_pr_summary.py` (PR body from the
  committed JSON, no second source of truth).
- Smoke-tested directly: a cold run against the real (egress-less) sandbox
  honestly reports `no_reachable_domain`/`not_targeted` for all 34
  in-scope sources (~82s); a second run within the TTL served every
  result from cache with zero new probes (~0.002s).
- Updated `docs/DATA_ACQUISITION.md` ("Discovery workflow" section),
  `docs/ROADMAP.md`, `docs/TECHNICAL_DEBT.md` (TD-23 partially closed).
- 568 backend tests pass; `ruff check` clean.

## 0.19.0 — No-API-key-sources policy: remove NEEDS_KEY entirely

The project owner made an explicit, permanent policy call: the platform
relies exclusively on genuinely free, no-registration sources, so waiting
on a `NEEDS_KEY` credential serves no goal — if a capability's only real
solution is a keyed API, drop it rather than leave it catalogued and idle.

- Removed the four `NEEDS_KEY` seed catalog entries (`fmp`,
  `alphavantage`, `polygon`, `tiingo`) from `sources/catalog.py`.
- Deleted `AlphaVantageCollector`/`FmpCollector` and their tests — dead
  code once their only catalog entries were removed.
- Dropped their ids from `acquisition_intelligence/capability.py`'s
  `CAPABILITY_STRATEGIES` pools (`PRICE_DATA`, `FINANCIAL_STATEMENTS`).
- Updated `test_capability_engine.py`'s synthetic fallback tests to use a
  still-catalogued id instead of the removed `fmp` placeholder (those
  tests exercise the generic ranking/fallback engine, not FMP itself).
- Registry is now 51 sources (14 IMPLEMENTED / 37 PLANNED / 0 NEEDS_KEY /
  0 TOS_REVIEW). `SourceStatus.NEEDS_KEY` stays in the enum as a
  structural classification — no seed source uses it, and any future
  source proposal needing a credential should be rejected the same way.
- Updated `docs/DATA_ACQUISITION.md`, `docs/ARCHITECTURE.md`,
  `docs/ROADMAP.md`, `docs/TECHNICAL_DEBT.md` (TD-21), and
  `docs/ACQUISITION_STRATEGY.md` (an inline note over the now-historical
  FMP/AlphaVantage analysis, preserving the original text).
- 559 backend tests pass; `ruff check` clean.

## 0.18.0 — Provider-leg health/reputation measured directly

The project owner flagged, from a review of the live source dashboards,
that a source integrated as a provider leg inside a composite collector
(`yahoo_finance`/`stockanalysis`/`mubasher` inside
`EgxCompositePriceCollector`, via `SourceSpec.integrated_via`) could show
`health_status: unknown`/`data_quality_score: null` in `source_registry.json`
even while actively serving real traffic through the composite — because
`CollectionService` only ever recorded metrics/health against the parent
collector's own id, never against the provider id a document was actually
attributed to (`Collector.provider_for_document`). The previous session's
`export_collector_status` fix addressed this for the dashboard's derived
per-run status table only (COLLECTED/STANDBY rows), by borrowing the
parent composite's `health_status` as a stand-in — the registry's own
`SourceSpec.health_status`/`reputation_score`/`data_quality_score` for
each provider leg were untouched and any consumer reading the registry
directly still saw permanently `unknown`/`null` fields.

- `CollectionService._record_provider_outcome` (new): records
  `SourceMetrics`/`HealthStatus` against a provider leg's own registry id,
  using the same per-document quality assessment already computed for
  that document (each raw document is already attributable to exactly one
  provider) — called alongside the existing collector-level
  `_record_run_outcome` for every document a `provider_for_document`-aware
  collector produces, on both the success and parser-failure paths.
- `production.artifacts.export_collector_status` no longer overwrites a
  provider-leg row's `health_status` with the parent composite's value —
  `_collector_status_row`'s own `registry.latest(provider_id)` lookup
  already returns the provider's own, now-measured status.
- New test: `test_provider_leg_health_and_reputation_are_measured_directly`
  (`test_collection_service.py`) — a good and a bad provider leg wired
  behind one stub composite collector each get their own, independently
  correct metrics/health, not a shared or borrowed value.
- 567 backend tests pass (1 new); `ruff check` clean. No new source,
  collector, or acquisition-architecture change — this is strictly a
  measurement-accuracy fix for sources already integrated, so it does not
  reopen the acquisition-architecture freeze (see `NEXT_MISSIONS.md`).

## 0.17.0 — Ticker Data Gap Report

- `meta.readiness.build_ticker_data_gap_report` decomposes
  `assess_decision_readiness`'s per-ticker counts into five named data
  layers (Financials/Disclosures/News/Macro/Knowledge), each with an
  explicit completeness percentage — a pure re-derivation of the existing
  readiness gates, never a second set of thresholds.
- New `ticker_data_gap_report.json` dashboard artifact
  (`production.artifacts.export_ticker_data_gap_report`), wired into
  `ProductionPipeline._stage_dashboard_artifact_generator` and validated
  in `dashboard/validate.py` for schema + universe-membership parity.
- Verified with a real mock-mode run against the full 101-ticker
  EGX30+EGX70 universe: 99 tickers `blocked`, 2 `degraded`, 0 Swing-ready,
  0 Investment-ready — the honest starting point, published as a
  filterable/sortable Artifact.
- 5 new tests (`test_ticker_data_gap_report.py`); 560 backend tests pass.
- New debt: TD-34 (no web/API wiring for the new artifact yet).

## 0.16.0 — Frontend: the remaining 8 sections (Opportunity Center through System Administration)
Completes the Production User Experience mission's 9-section rollout
(0.15.0 delivered the shell and AI Briefing). Every section composes only
from existing dashboard artifacts, per the mission's no-frontend-
calculation constraint.

- **Opportunity Center** — recommendations ranked by confidence,
  master/detail: ranked table + full `Explanation` breakdown (research/
  risk summary, supporting/contradicting evidence, historical similar
  cases, per-ticker upcoming catalysts) for the selected row.
- **Company Research Workspace** (`/company/:ticker`) — investment
  thesis, upcoming catalysts, knowledge timeline, research papers and
  gene lineage (cross-referenced via knowledge object ids), financial
  statements, corporate actions, news timeline. Market Regime & Macro
  Exposure is an honest "not yet available" gap.
- **Market Intelligence** — universe/sector composition, macro
  dashboard, market-wide corporate actions. Market Breadth & Liquidity
  and Market Regime & Historical Comparison are honest gaps — the
  frontend must not compute returns from raw price bars itself.
- **Research Center** — the 8-gate hypothesis pipeline (master/detail:
  ranked list + full stage history), covering "Experiments,"
  "Validation Queue," "Active Research," and "Discovery History" as
  views over the same `Hypothesis.stage_history`; Knowledge Objects;
  Scientific Papers. Review Board is an honest gap.
- **Knowledge Graph** — interactive, searchable, pan/zoomable rendering
  of `getKnowledgeGraph()`. New `web/src/lib/forceLayout.ts`: a small,
  dependency-free Fruchterman-Reingold-style force simulation, chosen
  over adding a graph-rendering library for a single page.
- **Mission Control** — mission status, pipeline health (stage-by-
  stage), knowledge/genome status, collectors, source health rollup,
  current blockers, execution history. Discovery Engine detail is an
  honest gap.
- **Source Intelligence** — every registered source, master/detail:
  health, lifecycle, reputation dimensions (availability, coverage,
  freshness, latency, accuracy, schema stability) as meters, joined
  across the source registry, source metrics, and the most recent
  collector run.
- **System Administration** — runtime/versions, configuration, replay
  capability, artifact inventory, per-stage performance (slowest
  first), execution history with error/session detail. Logs is an
  honest gap.
- Every page verified in a headless browser (dark theme) against real
  artifacts from a mock-mode `agx run` or a synthetic fixture where the
  mock pipeline currently produces no data (e.g. zero promoted
  knowledge/recommendations).
- 25 web tests total (was 19 after 0.15.0), all green. `npm run build`
  (`tsc -b && vite build`) passes clean.

## 0.15.0 — Frontend: design system, routed app shell, AI Briefing landing page
Start of the Production User Experience mission: the backend, research
engine, and production pipeline are declared complete by the project
owner; the remaining work is the complete frontend rebuild across 9
sections (AI Briefing, Opportunity Center, Company Research Workspace,
Market Intelligence, Research Center, Knowledge Graph, Mission Control,
Source Intelligence, System Administration).

- New institutional dark-theme-first design token system
  (`web/src/styles/tokens.css`) plus a shared primitive library: `Card`,
  `Badge`, `StatTile`, `Meter`, `DataTable`, `Section`,
  `EmptyState`/`LoadingState`/`ErrorState` — every page builds from these,
  no bespoke per-page styling.
- `AppShell`/`Sidebar`/`TopBar` (new): a persistent left-nav-across-9-
  sections layout with a live system-health status strip, replacing the
  single hardcoded knowledge table `App.tsx` previously rendered.
- `react-router-dom` v7.18 wired for all 9 sections; 8 render as honest
  "under construction" placeholders pending their own milestones.
- `useArtifact` hook (new): the one seam every page uses to pull data
  through `DashboardDataProvider` with consistent loading/error states —
  no page calls the provider directly.
- **AI Briefing** (landing page, fully built): System Health, Changes
  Since Yesterday (from `ExecutionReport`'s before/after counts), Market
  Summary, Top Opportunities, Biggest Risks, Most Important News,
  Upcoming Catalysts, Knowledge Changes, Scientific Discoveries, and
  Portfolio — composed entirely from existing dashboard artifacts with no
  frontend-side calculation, per the mission's explicit constraint.
- Fixed a real test-infra gap found while rewriting `App.test.tsx`:
  `@testing-library/react`'s `cleanup()` was never registered as a global
  `afterEach`, so previous tests' rendered DOM silently accumulated across
  tests in the same file — invisible before because no two tests' fixtures
  ever shared literal text. Fixed in `web/test/setup.ts`.
- 18 web tests green (was 5); `tsc --noEmit` and `vite build` both clean.

## 0.14.0 — Backend: dashboard artifacts for genes, papers, hypotheses, knowledge graph, financial statements, source reputation
Thin `model_dump(mode="json")` exports (no new calculations) for six
domain models that already existed but had no dashboard artifact:
`genes.json`, `papers.json`, `hypotheses.json`, `knowledge_graph.json`,
`financial_statements.json`, `source_metrics.json`. Wired into
`production/pipeline.py`'s dashboard-artifact stage and
`dashboard/validate.py` (optional — absent is not a failure).

- Fixed a real pre-existing bug while wiring the knowledge graph export:
  `ProductionPipeline._stage_research_pipeline` never passed a persisted
  `KnowledgeGraph` into `DailyResearchPipeline`, so graph edges were
  computed every run but silently discarded, never reaching
  `knowledge_graph.json`. Fixed by pointing it at `<data-dir>/graph_nodes.json`
  / `graph_edges.json`, matching how `hypothesis_repository`/
  `paper_repository`/`genome` are already wired.
- Extended both `StaticJsonProvider` and `ApiProvider` (`web/`/`api/`) with
  12 new `DashboardDataProvider` methods, and closed a pre-existing parity
  gap: the 6 "bonus" production-pipeline artifacts from the prior mission
  (`investment_cases`, `collector_status`, `runtime_status`,
  `dashboard_metrics`, `mission_status`, `execution_report`) were only ever
  wired into `StaticJsonProvider`, never into `api/`'s `ArtifactsReader` or
  routes — both providers now serve the full 18-method interface.
- 487 Python tests total, all green; `ruff` clean.

## 0.13.2 — Production-readiness audit for merge into main
Full audit before merging this branch into `main`: all tests green (477
Python / 14 API / 19 web), `ruff` clean, `contracts/` drift-free, no merge
conflicts with `main` (confirmed via `git merge-tree` — a clean
fast-forward, `main` hadn't moved), no TODO/FIXME/debug artifacts, no
unresolved conflict markers, no architecture-invariant violations found
(agents never write to `KnowledgeStore` directly; every real fetch goes
through `HttpFetcher`; no direct `EventRepository` writes bypass
`EventPlatform.register()`; every schema class defined exactly once).

One real duplication found and fixed: the same four-line header-matching
helper and the same single-URL-fetch-and-wrap pattern had been written
three times over (`RssNewsCollector`, plus this mission's
`IndexConstituentCollector` and `FinancialStatementCollector`).
Consolidated:
- `collectors/csv_columns.py` (new): `find_column()`, the shared
  header-text column matcher.
- `collectors/raw.py`: `fetch_single_text_document()` (new), the shared
  "one URL, one text document" `fetch()` body.

All three collectors now call the shared helpers instead of carrying
their own copies; behavior is unchanged (same tests, same assertions,
all still passing). No functional changes, no new features — a pure
deduplication refactor ahead of merge.

## 0.13.1 — Dashboard observability fix: report every collected record type
- `production/artifacts.py`'s `export_collector_status()` reported
  `price_bars_written`/`macro_observations_written`/`news_items_written`/
  `events_registered` but silently omitted `corporate_events_written`,
  `index_constituents_written`, and `financial_statement_line_items_written`
  — a real observability gap found while auditing for unblocked
  engineering work after Financial Statement Collection: `collector_status.json`
  was blind to genuine capability the platform already had (confirmed via
  a mock-mode `agx run`: `corporate_events_written` now correctly reports
  `2`, matching the real `COMI/EARNINGS` + `MFPC/DIVIDEND` rows already
  being written). Fixed by adding all three fields.
- 2 new tests (477 total); `ruff` clean.

## 0.13.0 — Financial Statement Collection
- `financials/` (new package): `FinancialStatementLineItem` — `{ticker,
  period_end_date, period_type, statement_type, line_item, value,
  currency}`; `STANDARD_LINE_ITEMS` (a small IFRS/GAAP-style vocabulary,
  reused where possible, never hard-enforced). `FinancialStatementProvider`
  (new, small ABC — mirrors `universe.UniverseProvider` rather than
  growing `data.provider.DataProvider`'s existing method set) +
  `CollectedFinancialStatementProvider` (reads collected CSV, empty when
  nothing's collected).
- `collectors/base.py`: `CollectionBatch` gained
  `financial_statement_line_items`. `collectors/service.py`:
  `CollectionService` materializes to `financial_statements/<TICKER>.csv`
  (merged by `period_end_date,statement_type,line_item`), provenance-traced,
  matching the existing writer pattern. `collectors/quality.py` counts the
  new record type.
- `collectors/financial_statements.py` (new): `FinancialStatementCollector`
  — a generic, header-matching CSV parser for a structured financial-
  statement export. Built and tested; not yet wireable into the live
  pipeline (`company_ir` stays `PLANNED` until its real endpoint is
  verified, `AD-24`).
- Deliberately **not** built: a generic PDF-based statement extractor —
  real filing layouts vary enough that a generic heuristic risks silently
  reading the wrong line item's value, the same reason
  `PdfDocumentCollector.parse()` stays abstract for every other PDF source.
- Confirms this closes a real, already-named gap:
  `agents.financial_performance.FinancialPerformanceAgent` has been an
  honest `NotImplementedError` stub since System 08, explicitly waiting on
  "a financial statement data source." The agent's own fundamental-factor
  logic remains separate, later work.
- 13 new tests (475 total, up from 462); `ruff` clean; `contracts/`
  unchanged. New technical debt: TD-31 (column detection, uncalibrated),
  TD-32 (PDF extraction, deliberately deferred). New risk: R-21 (guard
  against a future generic PDF-numeric-extraction attempt).

## 0.12.0 — Universe Engine + Corporate Disclosures
- `universe/constituent.py` (new): `IndexConstituent` — `{index, ticker,
  company_name, as_of_date}`, point-in-time correct (a date per row, not
  one overwritten snapshot).
- `collectors/base.py`: `CollectionBatch` gained `index_constituents` and
  `corporate_events`. `collectors/service.py`: `CollectionService` now
  materializes both (`universe/<INDEX>.csv` merged by `ticker,as_of_date`;
  `corporate_events.csv` merged by `ticker,date,event_type`), with full
  provenance tracing, matching the existing price/macro writer pattern.
  `collectors/quality.py`'s `produced`/`completeness_score` counts both.
- `universe/collected.py` (new): `CollectedUniverseProvider` (reads the
  collected CSV, latest snapshot at-or-before the query date, `{}` if
  nothing collected) + `FallbackUniverseProvider` (mirrors
  `FallbackDataProvider` exactly). Wired into `production.pipeline`'s
  `_stage_market_memory` and `cli.py`'s `discover-sources`.
- `collectors/index_constituents.py` (new): `IndexConstituentCollector` —
  a generic, header-text-matching CSV parser for a constituent-list
  export (ticker/name columns found by header content, not fixed order).
  Built and tested; not yet wireable into the live pipeline since
  `egx_official` stays `PLANNED` until its real endpoint is verified
  (`AD-24`) — same honest boundary as the AlphaVantage/FMP collectors.
- `collectors/corporate_event_classifier.py` (new): headline keyword
  heuristic (dividend/split/merger/acquisition/buyback/delisting/
  earnings/guidance/management-change), reusing `events.adapters.
  _CORPORATE_SUBTYPES`'s exact raw keys. `RssNewsCollector` gained a
  `classify_corporate_events` flag applying it per entry (exactly one
  ticker match required), populating `batch.corporate_events` alongside
  the always-produced `NewsItem` — closes TD-24.
- `production/collector_plan.py`: `rss_generic`'s mock/replay collector
  now runs with `classify_corporate_events=True`. Verified live: a
  mock-mode `agx run` now writes real `COMI/EARNINGS` and `MFPC/DIVIDEND`
  rows to `corporate_events.csv` from the existing mock RSS headlines.
- 31 new tests (462 total, up from 431); `ruff` clean; `contracts/`
  unchanged. New technical debt: TD-29 (classifier keyword list,
  uncalibrated), TD-30 (`IndexConstituentCollector`'s column detection,
  unverified against a real EGX export). TD-24 closed. New risk: R-20
  (classifier misclassification and the `events_from_corporate_events`
  confidence-modeling mismatch it exposes).

## 0.11.0 — Priority-Ordered Live Source Connection
- `acquisition_intelligence/target.py`: new `TargetOrganization.priority`
  field (and `company_ticker`) carrying the project owner's explicit
  business-value order — EGX official (1), EGX30/EGX70 company Investor
  Relations (2/3), CBE (4), FRA (5), CAPMAS (6), Enterprise (7), Mubasher
  (8), Zawya (9), Reuters (10), Trading Economics (11), anything else
  discovered (12, catch-all default). World Bank/IMF/FRED demoted to
  enrichment-only per the re-prioritization; every seeded target reassigned
  accordingly.
- `generate_company_ir_targets(companies)` (new): expands the prior
  `company_ir` per-constituent marker into one real `TargetOrganization`
  per EGX30 constituent — deliberately **no fabricated domain hints**;
  scales automatically to a real EGX30/EGX70 list the moment one exists,
  with zero code changes.
- `discovery/engine.py`: `discover_company_directory_links()` (new) —
  extracts a company's own homepage link from an already-fetched directory
  page via real anchor-text token matching against the company's name (not
  a guess), plus a `_PageLinkParser` extension to track anchor text.
  `AcquisitionIntelligenceEngine.run_catalog()` (new) processes targets in
  priority order and feeds any company hints discovered from an earlier
  target (e.g. EGX's own directory) into not-yet-run company IR targets.
- `cli.py discover-sources` now runs the full expanded catalog (named
  organizations + generated company IR targets) through `run_catalog`, in
  priority order, by default.
- Fixed a real pre-existing circular-import bug: `agx_research.discovery`
  failed to import if it was the first AGX module touched in a fresh
  process (`sources.qualification` imported `discovery.candidate.
  SourceCandidate` at module level while `discovery.candidate` imports
  `sources.spec`). Fixed with a `TYPE_CHECKING`-guarded import; regression-
  tested with a fresh-subprocess import test.
- Verified: the full 21-target priority-ordered catalog runs correctly
  end to end, in exact priority order, with an honest "no reachable
  domain" for every target (this sandbox still has no outbound network
  egress) — no crash, no fabrication.
- 14 new tests (427 Python tests total, up from 413); `ruff` clean;
  `contracts/` unchanged (no new pydantic model exposed to the API).
- New technical debt: TD-28 (company-directory-match heuristic
  uncalibrated against a real page). New risk: R-19 (guard against
  future fabrication of domain hints/constituent lists).
- Closed TD-16's remaining half: `HttpFetcher.fetch_bytes` now times each
  real request (excluding rate-limit/backoff sleeps); `CollectionService.
  run()` feeds the average into `SourceMetricsRepository.record_run()`.
  `reputation.py`'s `latency` dimension stays honestly `None` until a live
  collector runs, but the mechanism no longer needs building later. 4 new
  tests (431 Python tests total).

## 0.10.0 — First Production Execution Pipeline
- `agx_research.production` (new package): `ProductionPipeline` wires every
  stage the mission specifies, in order — Entry Point, Source Registry,
  Discovery Engine, Collector Selection, Collector Execution, Raw Archive,
  Canonical Transformation, Validation, Event Platform, Market Memory,
  Knowledge Base, Research Pipeline, Genome, Investment Case Generator,
  Dashboard Artifact Generator, Mission Control Update, Execution Report —
  by composing `CollectionService`, `DailyResearchPipeline`, `RuntimeEngine`,
  `RecommendationService`, `PortfolioConstructor`, `write_dashboard_artifacts`,
  and the Acquisition Intelligence Engine's continuity monitor. Nothing
  redesigned; this closed a real gap instead — `agx collect` wrote to
  `--data-dir` but `agx run` always read from a separate static
  `--mock-data` directory. They're connected now.
- `production/collector_plan.py`: the platform's *real* collectors
  (`StooqPriceCollector`, `FredCsvCollector`, `RssNewsCollector`,
  `WorldBankCollector`) run against a `MockFetcher` (execution mode
  `mock`, clearly-synthetic wire-format-correct content — the same
  numbers `research/data/mock/` uses, reformatted) or an
  `ArchiveReplayCollector` reading previously-archived documents
  (mode `replay`). `CollectionService.run()` is called identically either
  way — no live collector was built yet, per the mission's own instruction.
- `production/stages.py`+`report.py`: `StageResult`/`ExecutionReport` —
  every stage's status (`succeeded`/`partial`/`failed`/`skipped`),
  duration, detail, and error; per-stage failure isolation (a raised
  exception becomes a `FAILED` result, execution continues regardless).
- `production/mission_control.py`: `mission_status.json`, derived purely
  from `ExecutionReport` history (`PipelineExecutionRepository`) — pipeline
  status/version, last successful/failed pipeline, current execution mode,
  duration, artifacts produced, knowledge/genome updated.
- `production/artifacts.py`: `investment_cases.json` (the Investment Case
  Generator — composes the existing but previously-unwired
  `RecommendationService` + `PortfolioConstructor`), `collector_status.json`,
  `runtime_status.json`, `dashboard_metrics.json`.
- `collectors/fetcher.py`: `HttpFetcher.robots_status()` reused; no change
  needed there this phase beyond what Acquisition Intelligence already added.
- `cli.py`: `run` is now the single production entrypoint (`--mode mock`/
  `replay`, `--dashboard-out`); `build_engine()` (whose only caller this
  replaced) deleted along with its now-unused imports.
- `dashboard/validate.py`: extended to optionally validate the six new
  artifacts when present, without changing `export-dashboard`'s existing
  eight-artifact contract.
- `.github/workflows/deploy-pages.yml`: now calls the single `run` command
  instead of separate `run` + `export-dashboard` steps.
- 16 new integration tests (`test_production_pipeline.py`): full stage
  order, collected-data-reaches-research proof, replay reproduces the same
  research outcome, no duplicate archiving on replay, honest empty-replay
  behavior, deterministic execution, failure isolation (stage-level and
  per-collector), artifact generation + validation, Mission Control history
  tracking, CLI entrypoint. 413 Python tests green (up from 397); 33
  TypeScript tests unaffected; `ruff` clean; `contracts/` unchanged.

## 0.9.0 — Acquisition Intelligence Engine
- `acquisition_intelligence/` (new package): given only a `TargetOrganization`'s
  identity (name/category/country/public-brand domain hints — never a
  manually supplied URL), autonomously discovers how to legally acquire its
  data:
  - `domain_resolution.py`: `HeuristicDomainResolver` probes every hint and
    name-derived guess for actual reachability before trusting a domain.
  - `legality.py`: robots.txt (three-state, via new `HttpFetcher.robots_status`)
    + ToS red/green-flag keyword heuristics -> `ALLOWED`/`AMBIGUOUS`/`BLOCKED`;
    `HTML_SCRAPE` can never auto-clear to `ALLOWED`.
  - `stability.py`: URL-shape heuristics (canonical extension vs. session
    token/opaque id) + repeated-probe status-code consistency.
  - `historical.py`: Wayback Machine `available`/CDX API client + pure
    parsers, scored by archived-snapshot span.
  - `ranking.py`/`config_generation.py`: legality as a hard gate, composite
    ranking of the rest, auto-generated `SourceSpec` (collector suggested
    where unambiguous) that always stays `PLANNED` — never silently
    `IMPLEMENTED`.
  - `engine.py`: `AcquisitionIntelligenceEngine` orchestrates all of the
    above and begins qualification (records a reachability run, evaluates
    promotion) on success.
  - `continuity.py`: `AcquisitionContinuityMonitor` re-runs discovery,
    excluding the failed method, for any source whose health goes `DOWN`.
  - `live.py`: the one file wiring real network access for deployment;
    every other module is network-free and tested with fakes.
- `sources.catalog` seeded with 12 `TargetOrganization`s (EGX, Company IR,
  Reuters, Mubasher, Zawya, Enterprise, Asharq Business, CNBC Arabia, CBE,
  FRA, CAPMAS, Trading Economics), each linked to its existing `SourceSpec`
  catalog entry.
- `cli.py`: new `discover-sources` subcommand runs the engine (and
  continuity recovery) against the seed target catalog.
- `collectors/fetcher.py`: `HttpFetcher.robots_status()` — a three-state
  robots.txt check (allowed/disallowed/unreachable) distinct from the
  existing permissive-by-default `fetch_bytes` behavior.
- Verified directly (not assumed) that this development sandbox has no
  outbound network egress to arbitrary hosts (`curl`/`WebFetch` 403 on
  every target site attempted); a live `agx discover-sources` run
  correctly reports "no reachable domain" for all 12 named targets — the
  engine is complete and will perform real discovery the first time it
  runs somewhere with egress.
- 51 new Python tests (397 total, up from 346), all offline (fakes only);
  33 TypeScript tests unaffected; ruff clean.

## 0.8.0 — AGX Data Acquisition Platform
- `sources/`: `SourceSpec` gains three independent state axes —
  `lifecycle_state` (`LifecycleState`: Candidate/Quarantine/Evaluation/
  Trusted/Core), `health_status` (`HealthStatus`), `activation_status`
  (`ActivationStatus`) — plus `country`, `priority`, `reputation_score`.
  New `qualification.py` (evidence-gated promotion pipeline, one stage at a
  time, demoted on a DOWN health signal), `reputation.py` (`SourceMetrics`
  counters -> the charter's 9 reputation dimensions -> a composite score,
  finally wiring `SourceRegistry.record_measured_quality()`), `health.py`
  (`HealthMonitor`/`HealthAlert`: consecutive-failure/layout-change/schema-
  drift/staleness detection).
- `discovery/` (new package): `DiscoveryEngine` — RSS autodiscovery,
  PDF-repository scan, structured-dataset scan, sitemap scan, API-doc-link
  scan -> `SourceCandidate`. Pure function of already-fetched HTML/XML, no
  import of `SourceRegistry` — structurally cannot register or trust a
  source; `qualification.register_candidate` is the only bridge, always at
  Candidate/PLANNED with conservative priors.
- `collectors/archive.py` (new): `RawArchive`, a content-addressed,
  write-once binary blob store for PDF/Excel/image payloads that don't fit
  `RawDocument.content_text`; `RawDocument` gains `is_binary` and
  `build_binary_raw_document()`. `HttpFetcher` gains `fetch_bytes()`.
- `collectors/provenance_index.py` (new): `ProvenanceIndexRepository` — a
  per-value trace (source/collector/raw-document/hash/schema-version) for
  every materialized price bar and macro observation, closing the gap
  where only news items carried this forward. Wired automatically into
  `CollectionService`.
- `collectors/replay.py` + `archive_replay.py` (new): `ArchiveReplayCollector`
  (an ordinary `Collector` whose `fetch()` returns already-archived
  documents) + `HistoricalReplayEngine` — rebuild materialized data from
  the Raw Archive alone after a parser change, with no new fetch.
  `CollectionService.run()` is now idempotent about re-adding an
  already-stored `RawDocument`, and records `SourceMetrics`/`HealthMonitor`/
  registry health+reputation on every run (including parser exceptions,
  now caught and withheld rather than propagated).
- New generic collector-type frameworks: `PdfDocumentCollector` (pypdf-
  backed text extraction), `ExcelSeriesCollector` (openpyxl-backed,
  column-mapped macro series), `FilesystemCollector` (real, network-
  independent — ingests manually-placed files), `BrowserAutomationCollector`
  (honest `NotImplementedError` stub, no ToS-cleared target exists yet).
- New concrete collectors: `WorldBankCollector` (World Bank v2 API,
  IMPLEMENTED — Egypt macro indicators); `AlphaVantageCollector` and
  `FmpCollector` (code-complete and tested against each API's documented
  JSON shape, catalogued `NEEDS_KEY` — no fabricated/bypassed credentials).
- `contracts/source_spec.schema.json` regenerated; `api/src/types.ts` and
  `web/src/types.ts` updated to match the new `SourceSpec` fields.
- New dependencies: `pypdf`, `openpyxl` (both pure/near-pure-Python, no
  native extensions).
- 346 Python tests green (up from 273); TypeScript suite unchanged (33).

## 0.7.0 — Dual-provider dashboard architecture (static + API)
- `web/src/data/`: `DashboardDataProvider` interface with two
  implementations — `StaticJsonProvider` (reads JSON artifacts published
  alongside the static site) and `ApiProvider` (reads from a hosted
  `api/`). `web/src/data/factory.ts` selects one via `VITE_DATA_PROVIDER`
  (`web/.env.production` = static, `web/.env.development` = api); no
  component imports either implementation directly. `App` now takes an
  optional `provider` prop for testability.
- `research/src/agx_research/dashboard/`: `export_*()`/`write_dashboard_artifacts()`
  produce `knowledge.json`, `events.json`, `patterns.json`,
  `recommendations.json`, `market_state.json`, `runtime_metrics.json`,
  `system_status.json`, and `source_registry.json` — each a
  `model_dump(mode="json")` of an existing domain model, no duplicated
  schemas. `validate_dashboard_artifacts()` re-parses every file through
  its pydantic model before publishing, and hard-fails if `patterns.json`
  is ever non-empty (`HistoricalPatternsAgent` isn't implemented, so it
  must stay honestly empty). New CLI subcommands: `export-dashboard`,
  `validate-dashboard`.
- `contracts/`: `export_schemas.py` now emits schemas for `Event`,
  `Recommendation`, `MarketState`, `RunRecord`, `SourceSpec`, and the new
  `DashboardSystemStatus`, alongside `KnowledgeObject`; `api/src/types.ts`
  and `web/src/types.ts` extended to match.
- `api/`: new routes `/events`, `/patterns`, `/recommendations`,
  `/market-state`, `/runtime-metrics`, `/system-status`,
  `/source-registry` alongside the existing `/knowledge`. Events/runtime
  metrics flatten the same raw versioned-repository files `/knowledge`
  already does; the other five read the same generated snapshot files
  `StaticJsonProvider` reads, refreshed on a schedule in a real deployment
  (System 18 scheduling remains business-blocked).
- `cli.py`: events now persist to `data_dir/events.json` (previously
  in-memory only) via a shared `build_market_memory()` helper, so
  `export-dashboard` sees the same events any `run` produced.
- `.github/workflows/deploy-pages.yml`: now runs the real daily research
  pipeline against mock data (`agx run --date 2026-06-14`), generates and
  validates the dashboard artifacts into `web/public/data/`, then builds
  and publishes `web/`. Root-caused and fixed why the site was serving
  GitHub's default content: the repo's legacy branch-based Pages builder
  was still enabled alongside the Actions workflow and always won the
  race; `actions/configure-pages@v5` now fails the build loudly instead if
  that regresses.
- 17 new Python tests (273 total) and a new web test suite (19 tests,
  first `vitest`+`@testing-library/react`+`jsdom` setup for `web/`) plus 5
  new API tests (14 total) covering both providers, provider switching,
  App rendering with static artifacts, and "no `/api/*` calls happen in
  GitHub Pages mode."
- Docs synced: `MASTER_PROMPT.md` (new "Dashboard Data Architecture"
  section), `ARCHITECTURE.md`, `ROADMAP.md`, `TECHNICAL_DEBT.md`,
  `PHASE_STATUS.md`, `CLAUDE.md`.

## 0.6.1 — GitHub Pages deployment for the web dashboard
- `.github/workflows/deploy-pages.yml`: builds `web/` and publishes
  `web/dist` to GitHub Pages on push to `main` (paths-filtered to
  `web/**`), at `https://shadygad01.github.io/EGX-Genom/`.
- `web/vite.config.ts`: `base: "/EGX-Genom/"` for production builds only
  (dev server unaffected) so a GitHub Pages project site resolves assets
  correctly.
- Known limitation, documented in `docs/ARCHITECTURE.md`: GitHub Pages is
  static-only, so `api/`'s Fastify server isn't deployed alongside it —
  the dashboard renders but its knowledge fetch shows the existing "Error
  loading knowledge" state until `api/` is hosted somewhere reachable and
  `web/src/api.ts` is pointed at it.

## 0.6.0 — Production Data Acquisition Program (System 02 extension)
- `sources/`: `SourceSpec`/`SourceRegistry` — a 51-source declarative
  catalog spanning all 9 charter categories (Official, Company, Market
  Data, News, Arabic News, Macroeconomic, Global Markets, Alternative,
  Research), each with reliability/freshness priors, retry/rate-limit
  policy, license, conflict priority, and an honest status
  (IMPLEMENTED/PLANNED/NEEDS_KEY/TOS_REVIEW/DISABLED).
- `collectors/`: `RawDocument` provenance envelope (content-hash-derived
  id, append-only normalization/validation history); `HttpFetcher`
  enforcing robots.txt, per-source rate limits, and bounded exponential
  backoff in code, not just policy; `Collector` ABC that refuses to run
  against any non-IMPLEMENTED source; three real collectors — Stooq
  (EGX + global daily OHLCV), FRED (macro series), generic RSS/Atom
  (news, layout-tolerant); `collectors.quality.assess_quality()` computing
  the charter's 7 quality scores mechanically; `CollectionService`
  orchestrating fetch → parse → score → materialize-or-withhold → register
  (news candidates route through the existing `EventPlatform`, never a new
  write path).
- `data.mock_provider.LocalCsvDataProvider` — a clearer alias for
  `MockDataProvider` now that it also serves real collected data through
  the same CSV layout.
- CLI: new `collect` subcommand dispatching to the right collector by
  source id.
- `docs/DATA_ACQUISITION.md` — full design doc; `PHASE_STATUS`/`ROADMAP`/
  `TECHNICAL_DEBT` updated; 53 new tests (256 total), all offline against
  recorded-format fixtures (this environment has no outbound network
  egress; live fetching is validated only in deployment).

## 0.5.0 — Autonomous execution epoch: systems 04–18
- Market Memory: EGX trading calendar (fixed holidays as rules, movable as
  explicit placeholder table); canonical events wired into `MarketState`.
- Knowledge Graph: shortest-path and n-hop subgraph queries.
- Alpha Genome: multi-parent `merge()` alongside single-parent `mutate()`.
- Experiment Factory: claim statistic unified in `hypotheses/statistic.py`
  (pair→correlation, single→mean return); sensitivity analysis now real;
  only Monte Carlo remains a placeholder.
- Validation: `NaiveDirectionalBacktester` and
  `HistoricalWorstWindowStressTester` (first concrete gate implementations).
- Review Board: Economist (structural coherence) and PeerValidator
  (independent replication) reviewers real; findings carry proposed
  rationales for downstream judgment.
- Research OS: `DailyResearchPipeline` — the full 8-gate end-to-end chain
  with derived confidence, adversarial adjustment, genome/paper/graph
  output, and honest per-gate rejection.
- Scientist Framework: Macro, CorporateEvents, Liquidity,
  TechnicalStructure agents real (5 of 8); adversarial RandomCoincidence
  (seeded permutation test) and ParameterInstability real (6 of 9).
- Feature Discovery: momentum and volatility generators + definitions.
- Runtime Engine: deterministic date-range runner, per-day failure
  isolation, persistent run ledger, non-trading-day records.
- Prediction/Portfolio/Explainability/Learning v1: knowledge-weighted
  horizon models (no knowledge → no prediction), recommendation service,
  portfolio constructor with cash fallback, historical cases from real
  events, continuous-learning monitor with mechanical retirement.
- Infrastructure: integrity-checked backup/verify/restore, CLI
  (`run`/`status`/`backup`/`restore`), Dockerfile.
- Project management docs: ROADMAP, TECHNICAL_DEBT,
  ARCHITECTURE_DECISIONS, RISK_REGISTER, CHANGELOG; PHASE_STATUS rewritten.

## 0.4.0 — Event Platform production architecture (system 03)
- Fingerprint identity, taxonomy/ontology, entity resolution,
  dedup/conflict/lifecycle, `EventPlatform` sole write path, graph
  projection.

## 0.3.0 — MASTER_PROMPT charter adoption; Data Platform closure (02)
- Data quality validation, split/dividend adjustment (with a real caught
  bug: dividend factor from the last cum-dividend close), snapshot
  repository, fallback provider; PHASE_STATUS audit created.

## 0.2.0 — Epoch II: the scientific core
- Sessions/task graphs/artifacts, event layer, market memory, feature
  discovery, experiment factory, Alpha Genome, causal architecture,
  knowledge graph, paper generator, review board, adversarial scientist.

## 0.1.1 — Architectural audit and refactor
- Generic repositories, provenance chain, configurable gate pipeline,
  point-in-time snapshots, feature registry, contracts drift check.

## 0.1.0 — Foundation scaffold
- Python research engine skeleton, knowledge lifecycle, TS api/web
  viewers, CI.
