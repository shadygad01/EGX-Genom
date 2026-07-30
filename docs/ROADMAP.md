# Roadmap

**Frontend note:** the Production User Experience mission (see
`CURRENT_MISSION.md`) has completed a full rebuild of `web/` into a
routed, 9-section institutional research platform, consuming the
artifacts described below with zero frontend-side calculation. It changes
nothing on this roadmap — the backend/business-decision items below
remain exactly as scoped, paused rather than resumed during the frontend
phase.

Current engineering state: all 18 systems architecturally complete and
tested except the business-blocked remainder of 18 (see
`docs/PHASE_STATUS.md` for per-system detail). The platform runs
end-to-end daily research cycles on placeholder data. The Data Acquisition
Program (`sources/`+`collectors/`, see `docs/DATA_ACQUISITION.md`) has
since added a real (non-mock) collection path for free EGX/global/macro/
news data, feeding the same local-CSV layout the placeholder data uses
today. The web dashboard now runs on a dual-provider architecture
(`docs/ARCHITECTURE.md`'s "Dashboard data providers" section):
`StaticJsonProvider` for the GitHub Pages build (JSON artifacts generated
by the real pipeline, published via `.github/workflows/deploy-pages.yml`)
and `ApiProvider` for a hosted `api/`, both behind one interface so no
component needs to know which is active.

## Milestone: Production 1.0 (blocked on business decisions)

Required user/business inputs, in priority order:

1. ~~EGX market data vendor selection~~ — **decided (2026-07-27, see
   `docs/ARCHITECTURE_DECISIONS.md`'s AD-32): no paid/licensed vendor of
   any kind, permanently.** The `DataProvider` real-vendor seam stays
   unused; real EGX data (prices, macro, news, and per-company
   fundamentals alike) must come exclusively from the free-source
   Acquisition Program (`sources/`+`collectors/`+`acquisition_intelligence/`,
   see `docs/DATA_ACQUISITION.md`). Remaining engineering work under this
   constraint is tracked below under "Data Acquisition Platform" —
   principally widening `IMPLEMENTED` coverage and closing the per-company
   `company_ir` domain-resolution gap that gates real financial-statement
   data, now via two independent hint sources (`egx_official`'s own
   directory once reachable, and `discovery.wikidata_lookup` regardless of
   whether it is — AD-33) rather than depending solely on the exchange's
   own site.
2. **Deployment target** (cloud provider + payment), which unlocks:
   secrets management, managed scheduling of `RuntimeEngine`, monitoring/
   alerting, API authentication context, backup storage/retention.
3. **Authoritative EGX trading calendar + universe/sector membership
   feeds** (replace the placeholder tables).

## Closed: daily cross-run persistence (TD-40)

Was the highest-leverage engineering-closeable gap, not business-blocked:
the daily production pipeline (`deploy-pages.yml`'s `agx run --mode live`
step) used to run against an ephemeral `/tmp` data directory with no
restore-before/commit-after step, unlike `discovery.yml` — every calendar
day started from an empty `KnowledgeStore`/`AlphaGenome`/`EventRepository`/
run ledger, very likely the dominant reason the live dashboard rarely
surfaced a confident, cross-day-corroborated recommendation. **Now fixed**:
`deploy-pages.yml` restores `research/data/production/` from a
`production/state-latest` branch before running (`--data-dir
data/production`), auto-commits/force-pushes it back after a successful,
validated run (never PR-gated — operational state, not reviewed evidence),
and skips the rest of the job entirely on a same-day re-trigger (checked
against the real `RunRecordRepository`, since `RuntimeEngine` has no
built-in same-date dedup) so a double trigger can't duplicate a date's
hypotheses/knowledge. Accepted, disclosed tradeoff: real repo growth over
time (raw payload text accumulates) — watch it; see TD-40.

A complementary, already-shipped piece: `GdeltDocCollector` supports a
historical windowed backfill mode (absolute `startdatetime`/`enddatetime`,
`window_days`-sized slices around GDELT DOC 2.0's 250-articles-per-response
cap) and `.github/workflows/news-history-backfill.yml` runs it for real
(`workflow_dispatch`), landing old news in `research/data/news_history/`
via a reviewed PR — see TD-41.

## Closed: GDELT evidence-tier gate (TD-43)

Real 2026-07-29 evidence forced a bigger design question than "wire
GDELT's backfill into production": a live historical run's plain-OR query
returned 13,464 articles of which only ~3.8% even mentioned Egypt — GDELT
is a broad, low-precision global-news aggregator, not a source AGX should
ever let independently seed a `KnowledgeObject` or influence a
recommendation. Project owner direction: **GDELT is discovery-tier, not
primary-tier — every GDELT event must resolve to an independent PRIMARY
source (Enterprise, FRA, Al Borsa, Masrawy, company IR, official
announcements) before it counts as evidence.**

Implemented as `sources.spec.EvidenceTier` (`PRIMARY`/`DISCOVERY`) —
`collectors.service.CollectionService` now structurally routes a
DISCOVERY-tier source's news items to `news_discovery.csv` instead of
`news.csv`, and never registers them with the Event Platform directly.
`collectors.discovery_reconciliation.reconcile_discovery_news()` (wired
into `ProductionPipeline`'s Event Platform stage, runs every `agx run`)
is the only promotion path: a discovery candidate becomes a real
`news.csv` row only once a PRIMARY source independently reports the same
ticker within a tolerance window. GDELT's default query (daily-live and
backfill) was also tightened to require an Egypt term AND a finance term,
cutting the same false-positive class the query itself can address. The
already-collected historical batch was refiltered to 284 genuinely
Egypt-relevant headlines and re-pushed to its PR as `news_discovery.csv`
— see TD-41/TD-42/TD-43 for the full evidence trail, including a real
ticker-collision false-positive bug (TD-42) this reprocessing found.

"Wiring backfilled history into production" (the previous version of
this section) is superseded by this: the discovery pool is designed to be
folded into `research/data/production/news_discovery.csv` and continuously
re-checked by the daily reconciliation stage as PRIMARY-source coverage
grows, rather than merged into `news.csv` directly.

## Data Acquisition Platform: next engineering-closeable steps

**See `docs/ACQUISITION_STRATEGY.md` first** — a capability-by-capability
legal acquisition strategy matrix (built after live GitHub Actions runs
evidenced that "homepage = data source" fails for hardened public sites
like EGX/CBE, but succeeds for World Bank-style documented APIs), now also
a real runtime engine (`acquisition_intelligence.capability`/
`capability_engine`, wired into `production/pipeline.py`'s LIVE mode --
see the doc's "Runtime Implementation" section). Its concrete next steps,
not yet done: verify IMF's and OECD's documented SDMX/JSON API contracts
and catalogue them directly (like World Bank); once a second `IMPLEMENTED` candidate
exists for a capability beyond Macroeconomic, review whether
`rank_capability_strategies()`'s declared composite weighting (TD-33)
actually orders them the way measured outcomes would.

Unlike the Production 1.0 blockers above, these need no business decision —
they're config/verification work against the now-complete platform
(registry, discovery, qualification, reputation, health, archive,
provenance, replay, acquisition intelligence — see `docs/DATA_ACQUISITION.md`):

- ~~Run `agx discover-sources` wherever this deploys with outbound network
  egress~~ **Closed**: `.github/workflows/discovery.yml` now runs
  `agx discover-planned-report` weekly (plus manual `workflow_dispatch`)
  against every `PLANNED`/`CANDIDATE` source with a `TargetOrganization`,
  entirely on its own schedule and branch — it never blocks or slows
  `deploy-pages.yml`'s production deploy. Results (evidence, per-source
  recommendation, an incremental cache so an unchanged source isn't
  re-probed weekly) land only via a reviewed pull request against `main`
  from a dedicated `discovery/latest` branch — never a direct commit. See
  `docs/DATA_ACQUISITION.md`'s "Discovery workflow" section for the full
  design, and `docs/DATA_ACQUISITION.md`'s "What's still blocked" section
  for the per-source build-order breakdown this feeds.
- Every `SourceSpec` the engine auto-generates still needs an engineer to
  write and test the concrete collector before flipping `PLANNED` to
  `IMPLEMENTED` (by design — see `AD-16`/`AD-24`); the generic
  `RssNewsCollector`/`ExcelSeriesCollector`/`PdfDocumentCollector` already
  exist and cover most of what discovery is expected to find.
- Per the project owner's explicit decision, no `NEEDS_KEY` source will be
  catalogued going forward — FMP/AlphaVantage/Polygon/Tiingo were removed
  from the seed catalog and their collector code deleted for this reason
  (see `docs/DATA_ACQUISITION.md`'s "No API-key sources" note). Any future
  capability gap must be closed with a genuinely free, no-registration
  source, or left honestly uncovered.
- Cross-source corroboration measurement: once two IMPLEMENTED sources
  cover overlapping data (e.g. a second price source alongside Stooq),
  wire `consistency_score` in `collectors.quality.assess_quality()` instead
  of leaving it `None`.
- ~~Instrument `HttpFetcher` to time requests and feed real `latency_seconds`
  into `SourceMetricsRepository.record_run()`~~ **Closed (TD-16)**: done —
  `HttpFetcher.fetch_bytes` times each real request, `CollectionService`
  passes the average into `record_run`. Stays `None` in practice until a
  live collector actually runs (no fabricated placeholder in the interim).
- Calibration once real run history exists: `qualification.py`'s stage
  thresholds, `health.py`'s alert thresholds, and the Acquisition
  Intelligence Engine's own thresholds (TD-17, and its legality keyword
  lists, TD-20) are declared policy today, same situation as TD-6's
  conflict-policy constants.
- Wire a scheduled `agx discover-sources` run into a periodic job once any
  deployment target exists (System 18) — both the fresh-target discovery
  pass and `AcquisitionContinuityMonitor`'s DOWN-source recovery are ready;
  only the "run this on a schedule" wiring is deployment-shaped, not
  engineering (TD-23).

## Priority-Ordered Live Source Connection: next engineering-closeable steps

The current mission (see `CURRENT_MISSION.md`) re-prioritized live source
connection to strict business value: EGX official, then EGX30/EGX70 company
Investor Relations, then CBE/FRA/CAPMAS/Enterprise/Mubasher/Zawya/Reuters/
Trading Economics, then anything else the Acquisition Intelligence Engine
discovers on its own. `AcquisitionIntelligenceEngine.run_catalog()`,
`generate_company_ir_targets()`, and `discover_company_directory_links()`
already implement the full ordering and the EGX-directory-to-company-IR
hint chain end to end (see `docs/PHASE_STATUS.md`'s Production Execution
Phase section). What's next, in priority order:

- **Clear either blocker** (see `CURRENT_MISSION.md`'s "genuine constraint"
  section and `NEXT_MISSIONS.md` item 1): outbound network egress from a
  real deployment target, or a project-owner-supplied verified EGX30/EGX70
  constituent list. Neither is engineering-closeable from inside this
  sandbox.
- The moment either clears, `agx discover-sources` performs real discovery,
  ranking, `SourceSpec` generation, registration, and qualification kickoff
  for the entire catalog with zero further code changes.
- **First live production collector**: once a source in the catalog above
  resolves and qualifies, swap one of `collector_plan.py`'s mock-mode
  collectors for a real `HttpFetcher`-backed one against the verified live
  endpoint (`RssNewsCollector` for an IR/news RSS feed, `PdfDocumentCollector`
  for an IR disclosure PDF, etc. — see `NEXT_MISSIONS.md` item 2). World
  Bank remains a valid fallback first candidate (already `IMPLEMENTED`, a
  stable no-key public API) if its egress happens to clear first, but is no
  longer the priority per the project owner's explicit re-ordering.
- Calibration pass (TD-28, new this phase) on the company-directory-match
  token-overlap heuristic, once real EGX directory pages are actually
  fetched and matched against.

## Universe Engine + Corporate Disclosures + Financial Statements: next engineering-closeable steps

Closed this phase (see `docs/PHASE_STATUS.md`'s "Universe Engine +
Corporate Disclosures Phase" and "Financial Statement Collection"
sections for the full breakdown): `universe.IndexConstituent`/
`CollectedUniverseProvider`/`FallbackUniverseProvider`, `collectors.
index_constituents.IndexConstituentCollector`, `collectors.
corporate_event_classifier` (closing TD-24), and `financials.*` +
`collectors.financial_statements.FinancialStatementCollector` are all
built and tested. What's next:

- **Wire `IndexConstituentCollector`/`FinancialStatementCollector` live**
  once `egx_official`/`company_ir` are verified and flipped to
  `IMPLEMENTED` (blocked on network egress, `AD-24`).
- **Richer, PDF-based corporate disclosures and financial statements**:
  once a company's own IR/PDF source (priority 2/3, at real scale) is real
  and a concrete filing layout can be inspected, a source-verified
  `PdfDocumentCollector` subclass would give numeric corporate-event
  detail and full financial-statement line items a headline/structured-
  export path never can (TD-32) — never a generic PDF-numeric-extraction
  heuristic attempted ahead of a real layout.
- ~~**Wire financial statements into research**~~ **Closed** (Decision-Centric
  Redesign, 2026-07-30): `data.snapshot.DatasetSnapshot` gained
  `financial_statements`, populated via a new optional `financials_provider`
  parameter on `build_snapshot()`/`MarketMemory`, and
  `agents.financial_performance.FinancialPerformanceAgent` now produces
  real revenue-growth-trend and leverage-trend findings from it — see
  `docs/PHASE_STATUS.md`'s "Decision-Centric Redesign implementation"
  section and `AD-48`.
- Calibration pass (TD-29, TD-30, TD-31, new this phase) once real
  headlines and real exports exist to calibrate against.

## Production Execution Pipeline: next engineering-closeable steps

The first production pipeline (`agx run` -> `production.pipeline.
ProductionPipeline`) is complete, tested, and is the platform's single
production entrypoint. What's next, in priority order:

- ~~Wire a real corporate-actions collector (TD-24) so `CorporateEventsAgent`
  has something to find~~ **Closed**: `collectors.corporate_event_classifier`
  + `RssNewsCollector`'s `classify_corporate_events` flag now produce real
  (headline-only) corporate events in the mock pipeline — see the Universe
  Engine section above.
- Expand `collector_plan.py`'s mock/replay fixture coverage beyond
  COMI/MFPC once more tickers matter for research breadth.
- ~~Schedule `agx run` itself~~ **Closed for the GitHub Pages target**:
  `.github/workflows/deploy-pages.yml` now also fires on a daily
  `schedule:` cron (15:30 UTC, Sun-Thu, matching EGX's post-close window),
  not just on push — free on a public repo, no deployment target or paid
  scheduler needed. The dashboard now refreshes with real live data once a
  day even with zero commits. What's still open: a hosted `api/`'s own
  `DASHBOARD_ARTIFACTS_DIR` refresh (TD-14) needs a real deployment target
  to have anything to schedule against — this closes only the
  GitHub-Pages/`StaticJsonProvider` half.

## Dashboard architecture: next engineering-closeable steps

- Schedule `agx export-dashboard` to refresh a production `api/`'s
  `DASHBOARD_ARTIFACTS_DIR` periodically (System 18 scheduling is
  business-blocked in general, but this specific refresh needs only a cron
  job/timer once *any* deployment target exists — smaller than the
  System 18 blockers above).
- `patterns.json` stays `[]` — and `validate_dashboard_artifacts()`
  enforces that — until a dedicated `Pattern` pydantic model/contract
  exists for its dashboard-specific shape (TD-15). `HistoricalPatternsAgent`
  itself is implemented and its findings already flow through the normal
  pipeline like any other agent's (see `docs/PHASE_STATUS.md` System 08);
  this is only about a separate raw-pattern display artifact.
- Once a second `IMPLEMENTED` source overlaps an existing one, wire
  `consistency_score` (see the Data Acquisition Program item above) — this
  also improves `system_status.json`'s honesty once real corroboration
  data exists.

## Post-1.0 engineering roadmap (unblocked by real data accumulating)

- Trained per-horizon statistical models (replacing/augmenting the
  knowledge-weighted v1) once years of real history exist; the
  `HorizonModel` contract and model versioning are ready.
- Covariance-based portfolio optimization replacing capped proportional
  scoring; cost-aware portfolio-level backtesting harness.
- ~~Remaining scientist agent: FinancialPerformance~~ **Closed** — see
  above; all 8 of 8 Scientist Framework agents are now real. Remaining in
  this category: the HistoricalReviewer and the three remaining
  adversarial attacks (overfitting harness, regime labels,
  live-degradation comparison).
- ~~Wire `decision_service.DecisionService` into a queryable command~~
  **Closed** (TD-47): `agx decide --date ... [--positions positions.json]`
  reads a JSON portfolio file and prints position-aware six-way decisions,
  read-only and on-demand — never wired into `ProductionPipeline`'s
  autonomous stage list, per `AD-45`.
- Connect a real `SovereignRatingAction` collector once `moodys_ratings`/
  `sp_global_ratings`/`fitch_ratings` verify a real feed and go
  `IMPLEMENTED` (TD-48) — until then, `CountryRiskSeverity.CRISIS` is
  honestly unreachable by design, not a bug.
- Monte Carlo experiment once a market simulator design is chosen.
- Database-backed `Repository[T]` implementation when JSON stores hit
  scale limits; dedicated graph store behind the same interface.
- Full TS codegen for `contracts/` when the API surface grows.
