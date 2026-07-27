# Current Mission

## Current mission: TD-34 — `ticker_data_gap_report.json` web/API wiring

Immediate follow-up, per the project owner's "continue all remaining
legal/free directions" instruction: the last purely-engineering item on
`NEXT_MISSIONS.md`'s punch list.

**Closed** — see `docs/PHASE_STATUS.md`'s "TD-34" section: wired
following `financial_statements.json`'s exact existing pattern (API
route/provider method, both web providers, TS types); UI reuses
Opportunity Center's existing click-to-select pattern for a new "Data
Coverage" detail card on the Decision Readiness table, rather than a new
page. Verified in a real headless browser against real mock-mode `agx
run` output served through a production build — clicking a row correctly
populates the 5-layer breakdown. `npm run lint`/`build`/`test` clean for
both `api` and `web`.

**All five items from the project owner's "continue all remaining
legal/free directions" instruction are now closed**: NewsIntelligenceAgent,
entity resolution for news-to-ticker matching, macro frequency alignment
+ no-look-ahead discipline, the Monte Carlo stress simulator, and this
TD-34 wiring. See `NEXT_MISSIONS.md` for what's genuinely next.

---

## Prior mission: Monte Carlo stress simulator

Immediate follow-up, per the project owner's "continue all remaining
legal/free directions" instruction: `NEXT_MISSIONS.md`'s Monte Carlo
item — the one Experiment Factory gap named as a pure design decision,
not a data blocker.

**Closed** — see `docs/PHASE_STATUS.md`'s matching section: new
`validation.stress_test.MonteCarloBlockBootstrapStressTester` (block
bootstrap over real observed returns, matching the existing stress
tester's "locate/derive from real data, never simulate" philosophy);
`MonteCarloExperiment` is now a real adapter over it instead of raising;
`DailyResearchPipeline`'s STRESS_TEST gate now requires both testers to
pass. Verified an identical mock run still produces the same 5
hypotheses as before. 616 backend tests pass (8 new); `ruff check`
clean.

---

## Prior mission: macro frequency alignment + no-look-ahead discipline

Immediate follow-up, per the project owner's "continue all remaining
legal/free directions" instruction: `NEXT_MISSIONS.md` item 2.

**Closed** — see `docs/PHASE_STATUS.md`'s matching section for full
detail: `agents/macro.py` now forward-fills a macro series' step changes
onto every trading day instead of requiring exact date equality (closing
the frequency-mismatch half); `data/point_in_time.py` + `data.snapshot.
build_snapshot()`'s new `macro_series_sources` param drop any
observation not yet knowable given a declared, conservative per-source
publication-lag floor (new debt TD-37), wired into `ProductionPipeline`
for LIVE mode. Caught and fixed a real near-miss before merging: an
initial 365-day World Bank/UN SDG lag assumption contradicted this
codebase's own live-verified evidence (a real ~165-day-old collected
observation) — scaled back to a 30-day floor, verified against the
regression test that caught it. 608 backend tests pass (8 new); `ruff
check` clean.

---

## Prior mission: entity resolution for news-to-ticker matching

Immediate follow-up, per the project owner's "continue all remaining
legal/free directions" instruction: `NEXT_MISSIONS.md` item 1,
strengthening `NewsIntelligenceAgent`'s (and every RSS/GDELT-sourced
event's) own ticker attribution.

**Closed** — see `docs/PHASE_STATUS.md`'s "Entity resolution for
news-to-ticker matching" section for full detail: replaced
`RssNewsCollector`/`GdeltDocCollector`'s substring ticker match with real
word/token + company-name matching (`universe/entity_resolution.py`,
reusing `discovery.engine.significant_tokens()`), and threaded real
company names already present in this codebase
(`research/data/universe/EGX30.csv`/`EGX70.csv`) through the production
pipeline into both collectors. Deliberately no Arabic aliases (TD-36) —
no verified source exists, and this codebase does not fabricate one. 600
backend tests pass (8 new); `ruff check` clean.

---

## Prior mission: NewsIntelligenceAgent — turn already-connected real news into a real signal

The project owner asked why Opportunity Center recommendations still
aren't "real research," and, once the honest answer (99 of 101 tickers
have zero real price history; every remaining free/legal acquisition
avenue is either ToS/robots.txt-blocked, network-blocked, or gated on a
named business decision — see `docs/ACQUISITION_STRATEGY.md`) was given,
explicitly refused to have the ToS/robots.txt-compliance rule removed from
the codebase (a correct call: that rule is a legal/ethical line, not a
configurable preference) and instead asked to pursue every remaining
*legal, free* direction, prioritizing real results.

Per the standing acquisition-architecture freeze (`NEXT_MISSIONS.md`), no
new `TargetOrganization`/collector/source-discovery work was in scope
without a new named business input clearing a standing blocker — but the
freeze explicitly names non-acquisition work (turning already-connected
real evidence into research signal) as exactly what should happen instead.
`NewsIntelligenceAgent` (`NEXT_MISSIONS.md` item 2) was the named,
genuinely-unblocked next item: `enterprise_press`/`fra_egypt` have been
producing real dated `NewsItem` records every live run since the
"Egyptian Live Data Sprint" phase, and nothing turned that into a research
finding.

**Closed** — see `docs/PHASE_STATUS.md`'s "NewsIntelligenceAgent" section
for full detail: implemented as a real headline-keyword sentiment
classifier (`agents/news_sentiment.py`, new debt TD-35) feeding a
mechanical event-study-lite agent (`agents/news_intelligence.py`,
mirroring `CorporateEventsAgent`'s exact structure), wired into
`production.pipeline.ProductionPipeline`. Found and fixed one genuine,
previously-latent bug along the way: `collectors.service._append_news`
never deduped by natural key (unlike every sibling materialization
writer), silently duplicating news rows on repeated collection of the
same feed — caught by the existing mock/replay-determinism test the
moment a real agent started consuming `news.csv`. 592 backend tests pass
(24 new); `ruff check` clean.

**Not done this phase, named as genuinely next** (all legal/free, no
acquisition-architecture work): entity resolution for news-to-ticker
matching (`NEXT_MISSIONS.md` item 1, "Immediately next" section — directly
strengthens `NewsIntelligenceAgent`'s own ticker attribution); macro
frequency alignment + no-look-ahead discipline (item 2); the Monte Carlo
stress simulator (the one Experiment Factory gap that's a design decision,
not a data blocker); `ticker_data_gap_report.json` web/API wiring (TD-34).
See `NEXT_MISSIONS.md` for the full prioritized list.

---

## Prior mission: target the closeable half of "not_targeted", explain the rest honestly

The project owner looked at the live `/sources` page after the first real
Discovery run and asked, pointedly, why `PLANNED` sources still aren't
"working", with an explicit "100%" goal.

**The honest answer, grounded in the real run's own evidence** (34 sources
probed with real network egress, `discovery_metrics.json`): of 34 in-scope
sources, 1 verified reachable, 5 were legality-blocked (a real candidate
existed but robots.txt/ToS disallowed it), 7 had no reachable domain, 1 had
no discoverable candidates, and 20 were `not_targeted` (no
`TargetOrganization` entry existed at all — the engine had nothing to
resolve). "100%" is not an available outcome for the legality-blocked
five — bypassing robots.txt/ToS is a hard rule this codebase (and this
assistant) will not cross, full stop, regardless of the goal stated. But
20 of the 34 were a genuinely closeable gap, not a hard blocker.

**Closed**: added `TargetOrganization` entries (`acquisition_intelligence/
target.py`) for 14 of those 20 — every one with a single, unambiguous,
publicly-known organization domain (IMF, OECD, Egypt's Ministry of
Finance, Egypt's Open Data portal, the Suez Canal Authority,
Investing.com, TradingView, Google Trends, the Wikimedia Foundation,
arXiv, SSRN, NBER, Google Scholar, ResearchGate) — the same category of
public knowledge already used for every existing target (Reuters is
reuters.com), independently re-verified for reachability before anything
is trusted, never asserted. Verified locally (this sandbox has no egress,
so all 28 now-targeted sources honestly report `no_reachable_domain` —
the point is that they're attempted at all now, not skipped as
`not_targeted`). 568 backend tests pass; `ruff check` clean.

**Left alone, on purpose, not silently**: the remaining 6
(`github_releases`, `company_social_official`, `public_telegram`,
`patents`, `hiring_signals`, `company_ir`'s own per-constituent marker)
each name more than one candidate organization or are inherently
per-company/per-channel — picking one would be exactly the fabrication
this program's own rules forbid. These stay `not_targeted` until the
project owner names which specific organization/channel/office to target,
or until per-company generation (like `company_ir`'s own
`generate_company_ir_targets`) is extended to cover them.

**What "100%" will still never mean**: even a source that gets
`verified_reachable` next run still isn't `IMPLEMENTED` automatically —
per `AD-16`/`AD-24`, a maintainer must still confirm the real content
parses correctly before that flip, exactly the gate every prior promotion
(Enterprise, Al Borsa, Masrawy, FRA, Sky News Arabia) went through. This
is a deliberate safety rule, not a remaining task to automate away.

---

## Current mission: surface already-computed data the dashboard was hiding

The project owner looked at the live Mission Control (`/mission-control`)
and Source Intelligence (`/sources`) pages and reported "these pages have
unexploited capabilities" — asked for a plain-language summary first
(not asserting technical field names as the primary explanation), then to
fix it once the summary made sense.

Verified by reading the actual React components against the backend
artifacts feeding them (not guessing): `collector_status.json` computes
per-record-type counts and a composite reputation score per source per
run that the UI collapsed into one "Yield" number and never rendered at
all, respectively; `compute_reputation()`'s 9 charter dimensions were
only 6-of-9 rendered in Source Intelligence's meters (missing
`correction_rate`/`duplicate_rate`/`historical_usefulness` and the
composite); and the weekly Discovery workflow built in the mission below
had zero frontend wiring — its own artifacts existed on disk (once a PR
merges) with no `DashboardDataProvider` method, API route, or UI section
to reach them.

**Closed**:
- Mission Control's Collectors table: new Breakdown/Withheld/Reputation
  columns from fields `collector_status.json` already carried.
- Source Intelligence: 3 missing reputation dimensions + composite score
  added to the meters block.
- Discovery workflow wired end to end: `web/src/types.ts`
  (`DiscoveryOutcome`/`EndpointCandidate`/`DiscoveryMetrics`),
  `DashboardDataProvider`/`StaticJsonProvider`/`ApiProvider`
  (`getDiscoveryReport`/`getDiscoveryMetrics`/`getEndpointCandidates`),
  `api/src/artifactsStore.ts`/`api/src/routes/dashboard.ts` (3 new
  routes), a new "Weekly Discovery" section on Mission Control, and a
  "Discovery Evidence" block on Source Intelligence's detail panel.
  `deploy-pages.yml` copies `research/data/discovery/*.json` into the
  dashboard data directory when present (plain file copy, no
  reprocessing — see the mission below for why those files are already
  final-shaped). Renders an honest empty state until the first Discovery
  PR actually merges.
- `npm install` was needed first (fresh session, `node_modules` never
  installed) — `npm run build`/`test` clean for both `api` and `web`
  afterward.

---

## Current mission: weekly Discovery workflow — verify PLANNED sources continuously

The project owner pushed back on "37 sources stay PLANNED pending network
egress" as an unfinished-sounding answer: this dev sandbox has no egress,
but the GitHub Actions production deployment does, and nothing was
actually scheduled to use it for discovery. Asked, in effect, "what are
you waiting for — finish it."

Presented the concrete design choice (a new, separate scheduled workflow
vs. adding the step back into the fast production deploy vs. just
documenting the plan) via `AskUserQuestion`; the project owner chose a
dedicated, weekly, separate workflow with durable (git-committed)
evidence, gave a full detailed specification (scope: only `PLANNED`/
`CANDIDATE` sources; real verification with evidence per conclusion;
three named JSON artifacts; incremental — don't re-test what's still
fresh; promote through the existing qualification pipeline; PR only,
never a direct commit to `main`).

**Closed**:
- `acquisition_intelligence/discovery_report.py` (new): `plan_discovery_targets`
  scopes the catalog to in-scope sources honestly (excludes per-constituent
  markers and provider legs already wired via `integrated_via`, and reports
  a `PLANNED` source with no `TargetOrganization` as `not_targeted` rather
  than fabricating one); `run_discovery_report` runs the *existing*,
  unmodified `AcquisitionIntelligenceEngine.run_for_target` (which already
  calls the qualification pipeline internally — no new promotion mechanism
  needed) with a TTL + input-fingerprint incremental cache
  (`DiscoveryHistoryRepository`); `build_discovery_metrics` aggregates
  counts. 9 new tests (`test_discovery_report.py`), all fake-backed (no
  network), including cache-hit, TTL-expiry, and fingerprint-drift cases.
- New CLI subcommand `discover-planned-report` (`--out`, `--history`,
  `--ttl-days`, `--force`) wiring the above into three JSON artifacts.
- New `.github/workflows/discovery.yml`: its own trigger (weekly cron +
  `workflow_dispatch`), never touches or blocks `deploy-pages.yml`. Commits
  evidence only to a dedicated `discovery/latest` branch and opens/updates
  one standing PR against `main` — never a direct commit, never an
  automatic `SourceSpec.status` flip (that stays a reviewed, manual step
  per `AD-16`/`AD-24`, same as every prior source promotion in this
  codebase). Restores the prior run's history from `discovery/latest`
  before running, so re-verification genuinely only happens on TTL expiry,
  input drift, or an explicit `--force`.
- `research/data/discovery/README.md` documents the three artifacts;
  `research/scripts/build_discovery_pr_summary.py` renders the PR body
  from the committed JSON (never a second source of truth).
- Smoke-tested the CLI subcommand directly in this sandbox: an honest
  first run reports `no_reachable_domain` for all 14 in-scope, targeted
  sources (no egress here, exactly as documented) and `not_targeted` for
  the 20 catalogued sources without a `TargetOrganization` yet (~82s); a
  second run within the TTL served every result from cache with zero new
  probes (~0.002s) — the incremental behavior verified working, not just
  unit-tested.
- Updated `docs/DATA_ACQUISITION.md` (new "Discovery workflow" section),
  `docs/ROADMAP.md` (closed the "run discover-sources" item), and
  `docs/TECHNICAL_DEBT.md` (TD-23 partially closed — the scheduling half
  is done; wiring `AcquisitionContinuityMonitor`'s DOWN-recovery into the
  same schedule is still open, out of this mission's explicit PLANNED-only
  scope).
- 568 backend tests pass; `ruff check` clean.

**Named, not done** (deliberately out of this mission's scope): adding
`TargetOrganization` entries for the 20 untargeted `PLANNED` sources (a
real per-organization research decision, not this mission's ask); wiring
`AcquisitionContinuityMonitor` into the same schedule (TD-23's remaining
half); this session cannot verify the live GitHub Actions run itself (no
egress here) — the first real scheduled run, or a manual
`workflow_dispatch`, is the first live proof.

---

## Current mission: no-API-key-sources decision — remove `NEEDS_KEY` entirely

Immediate follow-up to the mission below: the project owner made an
explicit, permanent policy call — the platform is scoped exclusively to
genuinely free sources, so any source whose only route needs a
user-registered API key serves no goal ("لا انتظار" — no waiting on a
key that will never come, and if the only solution for a capability is a
keyed API, delete it rather than leave it catalogued and idle).

**Closed**: removed all four `NEEDS_KEY` seed catalog entries (`fmp`,
`alphavantage`, `polygon`, `tiingo`) from `sources/catalog.py`, deleted
`AlphaVantageCollector`/`FmpCollector` (`collectors/alphavantage.py`,
`collectors/fmp.py`) and their tests, and dropped their ids from
`acquisition_intelligence/capability.py`'s `CAPABILITY_STRATEGIES` pools
for `Capability.PRICE_DATA`/`Capability.FINANCIAL_STATEMENTS`. Updated
`test_capability_engine.py`'s synthetic fallback tests to use a still-
catalogued candidate id instead of the removed `fmp` placeholder (the
tests exercise the ranking/fallback engine generically, not FMP itself).
Registry is now 51 sources (14 IMPLEMENTED / 37 PLANNED / 0 NEEDS_KEY /
0 TOS_REVIEW). Updated `docs/DATA_ACQUISITION.md` ("No API-key sources"
section, replacing the old NEEDS_KEY policy description),
`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/TECHNICAL_DEBT.md`
(TD-21's repayment trigger no longer suggests a keyed resolver), and
`docs/ACQUISITION_STRATEGY.md` (an inline "Update" note over the
now-historical FMP/AlphaVantage analysis, preserving the original
analysis for accuracy rather than rewriting it). `SourceStatus.NEEDS_KEY`
stays in the enum as a structural classification — nothing currently
uses it, and any future source proposal needing a credential should be
rejected the same way, not silently re-added.

`NEXT_MISSIONS.md`'s "Paid/`NEEDS_KEY` sources" item is now closed
outright rather than deferred (see its updated entry).

---

## Current mission: provider-leg health measurement accuracy (System 02 accuracy review)

The project owner reviewed the platform's own source dashboards (as
generated by a prior Codex/Claude session) and reported the picture back
in detail: it's correct given current data, but reveals that dozens of
catalogued sources are still `PLANNED` without a verified endpoint, paid
sources have no key yet, no scheduled recurring discovery/collection
exists, and — specifically — `Unknown` health on some sources integrated
via composite integration is misleading because the measurement never
reaches the sub-source. Asked for the gaps to be closed.

**Outcome**: the first three are already-documented, correctly-named
business/infrastructure blockers, not code gaps — a `PLANNED` source
needs a verified real endpoint (this dev sandbox has no arbitrary
outbound egress, though the GitHub Actions production deployment does),
`NEEDS_KEY` needs the user's own credential, and periodic scheduling
needs System 18's managed-scheduling decision (TD-23's own named
repayment trigger) — re-attempting any of them here would mean guessing
a URL or fabricating a key, which this codebase's own rules forbid. The
fourth complaint was real and closeable: `CollectionService` only ever
recorded `SourceMetrics`/`HealthStatus` against a composite collector's
own id, never against the specific provider leg (`yahoo_finance`/
`stockanalysis`/`mubasher` inside `EgxCompositePriceCollector`) a
document was actually attributable to, so those legs' own
`health_status`/`data_quality_score` in `source_registry.json` stayed
`unknown`/`null` forever regardless of how much real traffic they
served. Closed with `CollectionService._record_provider_outcome`,
recording each provider leg's own metrics/health from the same
per-document quality assessment already computed for it; also removed a
prior session's display-layer workaround (`export_collector_status`
borrowing the parent composite's `health_status` for a provider row)
now that the provider's own measured value is correct. See
`docs/PHASE_STATUS.md`'s "Provider-Leg Health Measurement Accuracy"
section for full detail. 567 backend tests pass (1 new); `ruff check`
clean. Not a re-opening of the acquisition-architecture freeze below —
no new `TargetOrganization`, collector, or source added.

---

## Current mission: Ticker Data Gap Report (supersedes the acquisition freeze below for this one item)

The project owner supplied a new, detailed completion plan (in Arabic)
prioritizing whichever data source removes a decision blocker directly,
starting with an explicit per-ticker gap report ("know exactly what
prevents each of the 101 tickers from Swing/Investment readiness") before
anything else in the plan. This is **not** a re-opening of the acquisition
architecture freeze below (no new `TargetOrganization`, collector, or
source-discovery engineering happened) — it is the same "generate,
validate, rank, and explain" mandate the freeze itself called for, applied
to data-gap visibility specifically.

**Outcome**: most of the plan's own items turned out already
engineering-complete on inspection — `meta.readiness.assess_decision_readiness`
already computes the exact MICRO/SWING/INVESTMENT gates the plan asks for
(item 6); the Financial Statement Collector (item 3) and EGX-disclosure
classifier (item 2) already exist end to end, blocked only on the same
two named business inputs every phase since has named (a verified real
`company_ir` endpoint; this sandbox's lack of network egress); the
101-ticker EGX30+EGX70 universe (item 1's prerequisite) was already
connected. The one real, closeable gap: nothing decomposed
`decision_readiness.json` into the plan's five named layers
(Financials/Disclosures/News/Macro/Knowledge) with a completeness
percentage, and nothing published it as a reviewable artifact. Closed
this phase — see `docs/PHASE_STATUS.md`'s "Ticker Data Gap Report"
section for full detail, including the honest mock-mode evidence (99 of
101 tickers `blocked`, 2 `degraded`, 0 Swing-ready, 0 Investment-ready —
the correct starting point the plan itself describes) and a published
Artifact rendering it.

**Not done this phase, named as next** (see `NEXT_MISSIONS.md`): web/API
wiring for the new artifact (TD-34); the plan's item 4 (Arabic/English
company-alias entity resolution for news-to-ticker matching) and item 5
(macro series frequency alignment + point-in-time publication-date
discipline, avoiding look-ahead on financial/macro releases) — both real,
scoped engineering tasks, deliberately not started in the same sitting as
the gap-report work.

---

**Superseded six times since the "no egress" finding below.** That finding was
specific to *this coding sandbox*; the production deployment target
(GitHub Actions, `.github/workflows/deploy-pages.yml`) has real outbound
egress and has since run the pipeline live multiple times, producing
first-party evidence that changed the picture substantially. The original
"blocked at the mission's own stop condition" framing is preserved below
for its own historical accuracy but is **no longer the current state**.

## Current mission: acquisition architecture frozen — engineering effort shifts to explainable investment intelligence

The project owner's explicit instruction this phase: complete the
highest-value legally obtainable Egyptian data coverage, then **freeze
the acquisition architecture** — no further `TargetOrganization` entries,
collectors, or source-discovery engineering without a new named business
input clearing a standing blocker. Every subsequent sprint must increase
AGX's ability to **generate, validate, rank, and explain** investment
decisions, not merely collect more data.

**Closing verification before the freeze, not just a declaration**: (1) a
real self-correction — `skynews_arabia_economy` had been promoted to
`IMPLEMENTED` last phase on reachability/legal-clearance alone, without
confirming an actual successful collection (unlike `enterprise_press`/
`fra_egypt`); directly exercising its collector this sprint returned
`HTTP 404` on its only known feed URL, so it's reverted to `PLANNED` with
the finding recorded. (2) IMF's real current public API (the DataMapper,
distinct from the deprecated SDMX endpoint the prior phase found
unresolvable) returns `403 Forbidden` on every real indicator probed — a
WAF block, evidenced rather than assumed. Full detail:
`docs/ACQUISITION_STRATEGY.md`'s "Final Data Acquisition Sprint" section.

**Verdict: no further real source remains to connect right now.** Every
named candidate is either connected-and-verified (World Bank, Enterprise,
FRA), evidence-blocked (EGX official, CBE, IMF, Stooq, Yahoo Finance,
Investing.com, TradingView, Mubasher, Zawya, and every other named news
outlet), or gated on a business decision this program won't make
unilaterally (a NEEDS_KEY vendor's key, a verified EGX30/EGX70 constituent
list, a licensed EGX vendor). **The freeze is therefore in effect as of
this commit.** See `NEXT_MISSIONS.md` for what the next sprint actually
builds.

## Prior mission: price-data feasibility, evaluated with live evidence

Explicit question: can AGX build statistically valid investment research
using only legally obtainable free Egyptian market price data? If not,
prove it with evidence after evaluating every realistic free source; if
so, implement the minimum viable capability.

**Answer: no autonomously-implementable free strategy currently exists —
demonstrated, not assumed.** Every option engineering can act on
unilaterally is now evidenced-blocked by a live fetch this phase: Stooq's
robots.txt disallows its CSV-download mechanism entirely (confirmed
blanket, not EGX-scoped — an equivalent US-ticker path and even robots.txt
itself are disallowed identically); Yahoo Finance's actual Terms of
Service, fetched and quoted directly, explicitly prohibits "automated
means... robots, spiders, scrapers, data mining tools" (superseding the
prior "ambiguous" framing with a definitive answer); Investing.com
returned 403 Forbidden outright; TradingView's real policies page shows
explicit data-ownership/redistribution restrictions; Mubasher's and
Zawya's own homepages (508 and 154 links scanned) have zero
download/historical/export/csv/market-data links — nothing to discover,
not a legality question; EGX official remains network-level blocked,
reconfirmed. The one non-wall option (a NEEDS_KEY aggregator's free tier)
is explicitly a business decision reserved for the project owner, not
something engineering can supply on its own. Full evidence table:
`docs/ACQUISITION_STRATEGY.md`'s "Price Data Feasibility Mission" section.

**Nothing was implemented, and that is the correct outcome**: writing a
collector against any ToS/robots.txt-blocked source would violate this
program's own hard rules; Mubasher/Zawya have no structured endpoint to
write one against at all. `Price Data`/`Market Breadth` stay honestly
`UNAVAILABLE` — no number was fabricated to fill the gap. This confirms,
with today's direct evidence rather than inherited assumption, the same
blocker `docs/ROADMAP.md`/`MISSION_CONTROL.md` already named: a licensed
EGX market data vendor remains a business decision, not an engineering gap.

## Prior mission: coverage expansion (same phase's earlier half)

Explicit job: audit every registered source's real operational state,
then expand production coverage using only verified, legal, maintainable
strategies, reusing the existing architecture.

**Two new live sources**, verified with the same rigor as Enterprise:
`fra_egypt` (Egypt's own Financial Regulatory Authority,
`fra.gov.eg/feed/` — the first official Egyptian government source this
platform has connected; 10 real disclosure items, 10 events,
`data_quality_score=0.95`) and `skynews_arabia_economy`
(`skynewsarabia.com/rss.xml`, legally cleared, feed independently
confirmed live, not yet exercised by a live collection cycle since
`enterprise_press` ranks higher for the same capabilities). Both found by
the same RSS-autodiscovery heuristic that found Enterprise's feed — no new
architecture.

**Two real, previously-latent bugs found and fixed by actually running
expanded discovery live**, not by inspection: (1) nine catalogued-but-
never-attempted outlets had no `TargetOrganization` entry at all, so
`agx discover-sources` had nothing to run against them — closed by adding
one per outlet with its own public brand domain as a hint; (2) the
production pipeline's own discovery stage separately had its *own*
hardcoded 5-id allowlist left over from an earlier mission, so even a
target with a `TargetOrganization` entry was never automatically attempted
by a real `agx run --mode live` — only reachable via a manual CLI call.
Fresh discovery now runs every non-per-constituent seeded target every
live run. Running that expanded discovery immediately surfaced a third
real bug: `cnbc_arabia`'s real sitemap.xml contains a non-compliant
relative `<loc>` entry that `discover_sitemap_urls()` had never resolved
against its own URL (unlike every other discovery function), crashing the
whole discovery stage with a `ValueError` its own exception handling
didn't catch. Fixed with `urljoin()` plus a defensive `HttpFetcher`
widening. Full detail: `docs/ACQUISITION_STRATEGY.md`'s
"Coverage-Expansion Mission" section.

518→522 backend tests pass (4 new regression tests for the sitemap/fetcher
bugs); `ruff check` clean; deployed live via GitHub Actions and verified
serving from `main`.

## Prior mission: first real Egyptian market data flowing live

The prior mission (below) built the capability-driven runtime engine but
had never produced real EGX-specific data — World Bank (macro) was the
only thing actually collecting. This mission's explicit job was to stop
improving the platform and instead obtain real Egyptian data through at
least one verified, legal, maintainable strategy — "the mission is no
longer to improve AGX, the mission is to make AGX operational for the
Egyptian market."

**Outcome: mission succeeded.** `enterprise_press` is now `IMPLEMENTED`
and `lifecycle_state=TRUSTED`, collecting real news via
`https://enterpriseam.com/egypt/feed/` — discovered live by the existing
Acquisition Intelligence Engine's standard RSS-autodiscovery heuristic (a
real `<link rel="alternate" type="application/rss+xml">` tag on
enterprise.press's own homepage, never guessed), legally cleared (robots.txt
allows, `RSS_FEED` access method, no ToS red flags), and verified end to
end in a live GitHub Actions run: **6 real news items parsed, 6 real
events registered in the Event Platform**, `data_quality_score=0.97`,
`health_status=healthy`. `corporate_disclosures`, `corporate_actions`, and
`news` capabilities all now report `succeeded=True` via this one source in
`acquisition_decisions.json`. This is the first genuinely EGX-specific
live source this platform has ever collected from (World Bank's Egypt CPI
data is macro, not EGX-market-specific).

**Three real, previously-undetected bugs were found and fixed getting
here** — all directly blocking verification, not general platform
polish:
1. `HttpFetcher` crashed outright (`UnicodeEncodeError`) on a URL
   containing raw non-percent-encoded non-ASCII characters — surfaced by
   Zawya's real sitemap-index listing Arabic-slugged article URLs.
2. `HttpFetcher`'s robots.txt fetch had no timeout at all (stdlib
   `RobotFileParser.read()`'s own `urlopen()` call) — a host that accepts
   the TCP connection but never responds hung the entire pipeline
   indefinitely (one run was cancelled after 90+ minutes).
3. The sitemap-fallback discovery path (added last phase) had no cap on
   candidate count — a real sitemap-index's per-section sitemap can list
   thousands of URLs, each individually probed before ranking; this alone
   caused a second, ~70-minute hang even after fixing (1). Both nested-
   sitemap-following and total-candidate count are now bounded.
4. (A fourth, non-hang bug) `AcquisitionIntelligenceEngine.run_for_target()`
   unconditionally re-registered every named priority target on every
   pipeline run, including ones already `IMPLEMENTED` — silently
   regressing `enterprise_press` back to `PLANNED` in the very next run
   after it was first verified, since `generate_source_spec()` always
   mints a fresh `PLANNED` spec. Now skipped for any target that's already
   `IMPLEMENTED` and not `DOWN` (a `DOWN` `IMPLEMENTED` source still gets
   rediscovered, preserving `AcquisitionContinuityMonitor`'s recovery path).

Full evidence, the acquisition-decisions breakdown, and per-bug detail:
`docs/ACQUISITION_STRATEGY.md`'s "First Live Egyptian Source" section.
518 backend tests pass (8 new this phase); `ruff check` clean.

**Still not flowing** (honest gap, not attempted this phase): every other
named Egyptian source (EGX official, CBE, Mubasher, Zawya) remains blocked
by the same evidenced, genuine defensive measures documented in the prior
two missions (network-level reset, WAF rejection, robots.txt disallow, or
— Zawya specifically — a sitemap that's real and parseable but whose
entries are all HTML article pages, not a legally-clearable structured
feed). No knowledge/genome growth happened this specific run either — the
run date landed on a non-trading day, so the research pipeline correctly
produced zero hypotheses; the real events are registered and will feed the
next trading-day run.

## Prior mission: capability-driven acquisition engine

The prior mission (below) produced `docs/ACQUISITION_STRATEGY.md` as
analysis; this mission's explicit job was to turn it into executable
runtime logic — "stop thinking in terms of websites, think only in terms
of required data."

**Outcome:** `acquisition_intelligence.capability.Capability` (13 values:
the 12 named data requirements plus Research Papers) with
`CAPABILITY_STRATEGIES` mapping each to its declared, ranked pool of
catalogued `SourceSpec` ids — a capability, not a website, is now the
platform's primary acquisition object. `acquisition_intelligence.
capability_engine.rank_capability_strategies()` ranks every candidate from
registry state + measured reputation; `CapabilityDecisionEngine` executes
the best collectable one and automatically falls through to the next on
failure or zero yield (Macroeconomic runs every ready strategy, since
World Bank and FRED cover complementary, not redundant, series). Wired
into `production/pipeline.py`'s LIVE-mode Collector Selection/Execution —
reusing the exact same `CollectionService`/`SourceRegistry`/reputation
engine every mode already used, no new architecture — with every decision
persisted as a new `acquisition_decisions.json` Mission Control artifact
and rendered in the web dashboard, replacing a former "not yet available"
placeholder. A live-fixture run reproduces every existing collection
assertion unchanged for the sources already solved (stooq/fred/worldbank)
while every other capability now honestly reports its full ranked
fallback chain instead of being silently absent. 510 backend tests pass
(34 new); `ruff check`/`web`+`api` typecheck/build all clean. See
`docs/ACQUISITION_STRATEGY.md`'s "Runtime Implementation" and "Collector
Classification" sections, and `docs/PHASE_STATUS.md`'s matching entry, for
full detail. Deliberately not done: no new collector for IMF/OECD (their
exact endpoint shape is still unverified — the correct next step per the
strategy analysis, not implemented blind here either).

## Prior mission: solve the acquisition *strategy* problem

Live runs surfaced a pattern the "connect one more homepage" approach
wasn't going to fix: four of five named Egyptian sources are blocked by a
genuine, evidenced defensive measure (EGX: TCP connection actively reset;
CBE: explicit WAF rejection page; Enterprise/Mubasher: robots.txt
disallow), and the fifth (Zawya) is reachable with real content but has no
RSS/PDF/dataset/API link the existing homepage-scan heuristics could find.
Meanwhile World Bank — never approached via homepage discovery, catalogued
directly against its documented API — collected 66 real Egypt CPI
observations live. This mission's job was to determine whether the
*acquisition strategy itself* (not the platform) was wrong before writing
another collector.

**Outcome:** produced a full capability-by-capability legal acquisition
strategy matrix — see **`docs/ACQUISITION_STRATEGY.md`** — covering all 12
named data requirements (price, corporate disclosures/actions, financial
statements, IR, news, macro, breadth, calendar, index constituents, sector
membership, economic releases), ranking every legal strategy per
capability and comparing it against what's actually catalogued today. Key
finding: "homepage = data source" is the correct strategy only for
per-company Investor Relations (no legal aggregator substitute exists);
everywhere else, a documented API/feed/bulk-download contract should be
sought and catalogued directly (the World Bank precedent), with homepage
discovery as the fallback, not the default. IMF/OECD are flagged as
mismodeled (treated as homepage-discovery targets despite having
documented SDMX/JSON APIs at the same confidence tier as World Bank) —
recorded as the next step, not implemented blind, since their exact
endpoint shape hasn't been verified this session.

**Minimum engineering change implemented** (Step 7 of that document):
`AcquisitionIntelligenceEngine.run_for_target()` now falls back to the
sitemaps.org protocol (robots.txt's `Sitemap:` directive, then
`/sitemap.xml`, following a sitemap-index one level) when the homepage's
own markup has nothing discoverable — directly closing the Zawya-class gap
and `docs/TECHNICAL_DEBT.md` TD-18's sitemap-index half. `discover_sitemap_urls()`
also now classifies entries by file extension instead of blanket
`HTML_SCRAPE`. Both changes are fully unit-tested with fakes (research/tests/
test_discovery.py, test_acquisition_engine.py); no network call was added
that bypasses robots.txt, ToS, or any anti-bot measure, and no endpoint was
fabricated or guessed.

## Prior mission: Egyptian Live Data Sprint (immediately preceding phase)

Replaced the mock-only production pipeline with a real `--mode live`
default, fixed a genuine health-engine bug (a collector that downloaded
data but produced zero parsed/knowledge/event records was previously
reported HEALTHY — now correctly `DEGRADED`/`FAILED` with an explicit
reason, connection/parse/yield/knowledge/event metrics surfaced in
Mission Control), and fixed a second bug where a fetch-level exception
bypassed health/metrics bookkeeping entirely. Live runs via GitHub
Actions (which does have egress, unlike this coding sandbox) confirmed:
World Bank collects real data; Stooq/FRED are reachable but blocked by
a Cloudflare-style JS challenge / non-responsive respectively; the five
named Egyptian sources fail with the concrete, source-side reasons this
phase's `docs/ACQUISITION_STRATEGY.md` documents in full. This is the
first mission where "the platform has genuinely run live," superseding
the pure no-egress framing below.

---

## Historical: original "no egress in this coding sandbox" finding

**Superseded by a new mission from the project owner: activate AGX with
real live data**, connecting the first live production sources in the
named priority order (Tier 1: EGX official, EGX30/EGX70 company Investor
Relations, CBE; Tier 2: Enterprise, Mubasher, Zawya, Asharq Business;
Tier 3: CAPMAS, Trading Economics, World Bank, IMF, FRED; Tier 4:
whatever the Acquisition Intelligence Engine discovers on its own).

**Outcome of this phase, verified directly (not assumed):** every named
Tier 1-4 host is unreachable from *this coding session specifically*
(the sandbox this assistant runs in, not the GitHub Actions deployment
target — see the two phases above for what running with real egress
actually found). `curl` to
`www.egx.com.eg`, `www.cbe.org.eg`, `www.mubasher.info`, `www.zawya.com`,
`www.tradingeconomics.com`, `fred.stlouisfed.org`, `stooq.com`,
`api.worldbank.org`, `data.worldbank.org`, `www.imf.org`,
`www.capmas.gov.eg`, `www.enterprise.press`, and `asharqbusiness.com` all
fail identically: `CONNECT tunnel failed, response 403`. The proxy's own
status endpoint (`$HTTPS_PROXY/__agentproxy/status`) logs each as
`connect_rejected` — `"gateway answered 403 to CONNECT (policy denial or
upstream failure)"` — an explicit organization egress-policy denial, not a
transient failure, and not specific to any one source (it blocks
`fred.stlouisfed.org`/`stooq.com`/`api.worldbank.org` too, sources this
codebase's own registry already lists as `IMPLEMENTED`). `WebFetch`
independently returns HTTP 403 for the same hosts. Running the platform's
own `agx discover-sources` end to end against the full 21-target priority
catalog reproduces the same result for every target,
`no-op -- No reachable domain found from public brand hints or
name-derived guesses` — the `HeuristicDomainResolver` correctly refusing
to trust an unprobed domain, not a bug. This is the fifth independent
confirmation of the same environmental block across missions (see
`MISSION_CONTROL.md`), now with proxy-level evidence in addition to the
prior curl/WebFetch checks.

Per this mission's own stated stop conditions ("a genuine external
dependency blocks implementation"), no live collection could be started
this phase. The instructions governing this session also explicitly
forbid working around a proxy policy denial (`/root/.ccr/README.md`:
"do not retry or route around it — report the blocked host"), so no
attempt was made to bypass it. Every engineering-closeable prerequisite
for the moment egress exists — `SourceRegistry`, `CollectionService`,
the qualification/reputation/health pipeline, and the
`AcquisitionIntelligenceEngine` that resolves/verifies/ranks/registers a
source with no hand-picked URL — was already built and tested in prior
missions and required no changes here. See `docs/TECHNICAL_DEBT.md`: every
remaining named debt item is gated on either a real fetch happening at
least once (to verify a wire format) or a business decision (EGX70 list,
vendor selection) — there is no debt item closeable from inside this
sandbox.

**This session's actual conclusion:** live-data activation cannot proceed
further until this runs in an environment with real outbound egress (a
deployment decision, System 18) or the project owner supplies the
business inputs `MISSION_CONTROL.md` names (a verified EGX30/EGX70
constituent list; a licensed EGX vendor selection). Nothing was
fabricated in place of a real connection. **Since superseded**: the
GitHub Actions deployment target does have egress, and the two mission
phases above describe what actually happened once it ran there.

---

## Prior mission (paused, unchanged by this phase)

**Build the complete AGX Production User Experience — a world-class
Research Intelligence Platform, not a stock website, dashboard, or CRUD
app.**

The project owner has declared the backend architecture, the research
engine, and the production pipeline complete: no more backend redesign
work. Full engineering ownership has been handed to the frontend — the
visual/UX bar is a combination of Bloomberg Terminal, Koyfin, TradingView,
Notion, and institutional sell-side research. The interface must explain
not only *what* AGX recommends, but *why*, *how* it reached that
conclusion, and *what evidence* supports or contradicts every thesis.

**Hard constraint, unchanged from the backend mission's own discipline:**
the frontend consumes artifacts only. No calculation happens in `web/` —
every number a page shows must already exist in a dashboard artifact
`research/src/agx_research/dashboard/export.py` or
`production/artifacts.py` produces. A UI need with no backing artifact
gets either (a) a new thin backend export (a `model_dump(mode="json")`
over an already-tested model, same pattern as every prior artifact) or
(b) an honest "not yet available" gap in the UI — never a fabricated
number.

## Status: all 9 sections built

The application is nine sections, all now implemented and routed:
AI Briefing (landing page), Opportunity Center, Company Research
Workspace, Market Intelligence, Research Center, Knowledge Graph,
Mission Control, Source Intelligence, System Administration.

## What this phase engineered

**Frontend Audit.** Read the entire repository, every architecture and
Mission Control document, the existing `web/` implementation (a single
hardcoded knowledge table, `App.tsx`), the production pipeline, and every
JSON artifact AGX produces, before writing any code.

**Backend: six new dashboard artifacts.** `genes.json`, `papers.json`,
`hypotheses.json`, `knowledge_graph.json`, `financial_statements.json`,
`source_metrics.json` — thin `model_dump(mode="json")` exports, no new
calculations. Fixed a real pre-existing bug: `ProductionPipeline` computed
knowledge-graph edges every run but never persisted them (no path was
passed to the `KnowledgeGraph` constructor) — fixed by pointing it at
`<data-dir>/graph_nodes.json`/`graph_edges.json`, matching how the
hypothesis/paper repositories and the genome are already wired. Closed a
pre-existing `api/`/`StaticJsonProvider` parity gap for 6 earlier "bonus"
artifacts (`investment_cases`, `collector_status`, `runtime_status`,
`dashboard_metrics`, `mission_status`, `execution_report`) that were only
ever wired into the static provider.

**Design system + routed application shell.** Institutional dark-theme-
first design tokens (`web/src/styles/tokens.css`), a shared primitive
library (`Card`, `Badge`, `StatTile`, `Meter`, `DataTable`, `Section`,
`EmptyState`/`LoadingState`/`ErrorState`), a persistent `Sidebar`/`TopBar`
`AppShell`, and `react-router-dom` routes for all 9 sections. A
`useArtifact` hook is the one seam every page uses to pull data through
`DashboardDataProvider` with consistent loading/error handling.

**AI Briefing** — the landing page and "signature experience": System
Health, Changes Since Yesterday (from `ExecutionReport`'s before/after
counts), Market Summary, Top Opportunities, Biggest Risks, Most Important
News, Upcoming Catalysts, Knowledge Changes, Scientific Discoveries, and
Portfolio.

**Opportunity Center** — every recommendation ranked by confidence,
master/detail: ranked table + full `Explanation` (research/risk summary,
supporting/contradicting evidence, historical similar cases, upcoming
catalysts) for the selected row.

**Company Research Workspace** (`/company/:ticker`) — per-ticker deep
page: investment thesis, upcoming catalysts, knowledge timeline, research
papers and gene lineage (cross-referenced via knowledge object ids),
financial statements, corporate actions, news timeline. Market Regime &
Macro Exposure is an honest gap (no artifact exists upstream yet).

**Market Intelligence** — universe/sector composition, macro dashboard,
market-wide upcoming/recent corporate actions. Market Breadth & Liquidity
and Market Regime & Historical Comparison are honest gaps — the frontend
must not compute returns from raw price bars itself
(`data.adjustments`'s own rule).

**Research Center** — the 8-gate hypothesis pipeline (master/detail:
ranked list + full stage history), covering "Experiments," "Validation
Queue," "Active Research," and "Discovery History" as views over the same
underlying data; Knowledge Objects; Scientific Papers. Review Board is an
honest gap (no repository persists past `BoardDecision`s yet).

**Knowledge Graph** — interactive, searchable, pan/zoomable rendering of
`getKnowledgeGraph()`'s nodes and edges, using a small dependency-free
force-directed layout (`lib/forceLayout.ts`) rather than adding a
graph-rendering library for one page.

**Mission Control** — mission status, pipeline health (stage-by-stage),
knowledge/genome status, collectors, source health rollup, current
blockers, execution history. Discovery Engine detail is an honest gap (no
dashboard export yet for `acquisition_intelligence`).

**Source Intelligence** — every registered source, master/detail: health,
lifecycle, activation, reputation dimensions (availability, coverage,
freshness, latency, accuracy, schema stability) as meters, joined across
the source registry, source metrics, and the most recent collector run.

**System Administration** — runtime/versions, configuration, replay
capability, artifact inventory, per-stage performance (slowest first),
execution history with error/session detail. Logs is an honest gap (no
artifact carries raw log lines yet).

Every page above was verified in a headless browser (both light and dark
theme where relevant) against either real artifacts from a mock-mode
`agx run` or a synthetic fixture where the mock pipeline currently
produces no data (e.g. zero promoted knowledge/recommendations) — never
against untested markup.

## What's next

The quality pass: responsive layout, accessibility, performance,
cross-page consistency re-verified now that all 9 sections exist (see
`NEXT_MISSIONS.md`). No further page is queued unless the quality pass or
the project owner surfaces a genuine gap.

## What did NOT change

Per the mission's explicit instruction, no backend redesign happened
beyond the sanctioned artifact-export extension point: `hypotheses/`,
`validation/`, `agents/`, `orchestration/`, `production/pipeline.py`'s
internal stage logic, `KnowledgeStore.promote()`'s signature, and every
other backend invariant `CLAUDE.md` documents are unchanged. The one
backend fix (wiring a persist path into `KnowledgeGraph`'s existing
constructor parameter) is additive composition, not a redesign.
