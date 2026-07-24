# Current Mission

**Superseded three times since the "no egress" finding below.** That finding was
specific to *this coding sandbox*; the production deployment target
(GitHub Actions, `.github/workflows/deploy-pages.yml`) has real outbound
egress and has since run the pipeline live multiple times, producing
first-party evidence that changed the picture substantially. The original
"blocked at the mission's own stop condition" framing is preserved below
for its own historical accuracy but is **no longer the current state**.

## Latest mission: first real Egyptian market data flowing live (this phase)

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
