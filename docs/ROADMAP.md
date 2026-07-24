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

1. **EGX market data vendor selection** (the gating decision). Candidates
   to evaluate on cost/coverage/latency/licensing: EGX official feeds,
   Mubasher, Refinitiv/LSEG, Bloomberg. Engineering integration after the
   decision: one `DataProvider` implementation + `FallbackDataProvider`
   configuration + re-run of `data.quality` calibration. Estimated
   engineering: small — the seam exists.
2. **Deployment target** (cloud provider + payment), which unlocks:
   secrets management, managed scheduling of `RuntimeEngine`, monitoring/
   alerting, API authentication context, backup storage/retention.
3. **Authoritative EGX trading calendar + universe/sector membership
   feeds** (replace the placeholder tables).

## Data Acquisition Platform: next engineering-closeable steps

**See `docs/ACQUISITION_STRATEGY.md` first** — a capability-by-capability
legal acquisition strategy matrix (built after live GitHub Actions runs
evidenced that "homepage = data source" fails for hardened public sites
like EGX/CBE, but succeeds for World Bank-style documented APIs), now also
a real runtime engine (`acquisition_intelligence.capability`/
`capability_engine`, wired into `production/pipeline.py`'s LIVE mode --
see the doc's "Runtime Implementation" section). Its concrete next steps,
not yet done: verify IMF's and OECD's documented SDMX/JSON API contracts
and catalogue them directly (like World Bank), rather than as
homepage-discovery targets; explore FMP's financial-statement endpoints
for EGX coverage once a key exists; once a second `IMPLEMENTED` candidate
exists for a capability beyond Macroeconomic, review whether
`rank_capability_strategies()`'s declared composite weighting (TD-33)
actually orders them the way measured outcomes would.

Unlike the Production 1.0 blockers above, these need no business decision —
they're config/verification work against the now-complete platform
(registry, discovery, qualification, reputation, health, archive,
provenance, replay, acquisition intelligence — see `docs/DATA_ACQUISITION.md`):

- **Run `agx discover-sources` wherever this deploys with outbound network
  egress.** The Acquisition Intelligence Engine is complete and tested
  (`acquisition_intelligence/`); in this development sandbox it correctly
  reports "no reachable domain" for all 12 named PLANNED official/company/
  regional-news targets because the sandbox itself has no egress to
  arbitrary hosts (confirmed directly, not assumed). This single step —
  not manual endpoint research — is what completes the remaining item from
  the program's named 16-collector build order that isn't already either
  done (World Bank, AlphaVantage/FMP) or blocked on a business decision
  (Yahoo/TradingView ToS review); see `docs/DATA_ACQUISITION.md`'s "What's
  still blocked" section for the full breakdown.
- Every `SourceSpec` the engine auto-generates still needs an engineer to
  write and test the concrete collector before flipping `PLANNED` to
  `IMPLEMENTED` (by design — see `AD-16`/`AD-24`); the generic
  `RssNewsCollector`/`ExcelSeriesCollector`/`PdfDocumentCollector` already
  exist and cover most of what discovery is expected to find.
- Once a user supplies an AlphaVantage or FMP API key, flip that entry to
  `IMPLEMENTED` — the collector code and tests already exist.
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
- **Wire financial statements into research**: `FinancialStatementProvider`
  isn't yet composed into `MarketMemory`/`DatasetSnapshot` — deliberately
  deferred until `agents.financial_performance.FinancialPerformanceAgent`'s
  actual fundamental-factor logic is scoped (Scientist Framework work,
  System 08), rather than extending Market Memory for a consumer that
  doesn't exist yet.
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
- Schedule `agx run` itself (System 18, business-blocked in general, but
  the command is deployment-ready today) once any deployment target
  exists — this is the "runs unchanged under GitHub Actions and
  Cloudflare" the mission specified; `.github/workflows/deploy-pages.yml`
  already proves the GitHub Actions half.

## Dashboard architecture: next engineering-closeable steps

- Schedule `agx export-dashboard` to refresh a production `api/`'s
  `DASHBOARD_ARTIFACTS_DIR` periodically (System 18 scheduling is
  business-blocked in general, but this specific refresh needs only a cron
  job/timer once *any* deployment target exists — smaller than the
  System 18 blockers above).
- `patterns.json` stays `[]` — and `validate_dashboard_artifacts()` enforces
  that — until `agents.historical_patterns.HistoricalPatternsAgent` is
  implemented (still a data/methodology gap, see `docs/PHASE_STATUS.md`
  System 08).
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
- Remaining scientist agents as their feeds arrive: NewsIntelligence
  (NLP), FinancialPerformance (fundamentals), HistoricalPatterns
  (long-history analogs) — plus the HistoricalReviewer and the three
  remaining adversarial attacks (overfitting harness, regime labels,
  live-degradation comparison).
- Monte Carlo experiment once a market simulator design is chosen.
- Database-backed `Repository[T]` implementation when JSON stores hit
  scale limits; dedicated graph store behind the same interface.
- Full TS codegen for `contracts/` when the API surface grows.
