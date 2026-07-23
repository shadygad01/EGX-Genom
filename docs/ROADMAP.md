# Roadmap

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

## Data Acquisition Program: next engineering-closeable steps

Unlike the Production 1.0 blockers above, these need no business decision —
they're config/verification work against the existing `Collector`
framework:

- Verify real endpoint URLs and wire `SourceSpec`s for the `PLANNED`
  official sources (EGX, FRA, CBE, MoF, CAPMAS, Egypt Open Data) and the
  `PLANNED` English/Arabic news RSS feeds — each just needs its actual
  feed/endpoint confirmed and a `SourceSpec` flipped to `IMPLEMENTED`; the
  generic `RssNewsCollector`/`FredCsvCollector` already serve them.
- Add a source-specific collector only where no existing generic collector
  applies (e.g. company IR PDF/XBRL filings, Suez Canal statistics).
- Cross-source corroboration measurement: once two IMPLEMENTED sources
  cover overlapping data (e.g. a second price source alongside Stooq),
  wire `consistency_score` in `collectors.quality.assess_quality()` instead
  of leaving it `None`, and start feeding `SourceRegistry.record_measured_quality()`
  from real run history instead of leaving `data_quality_score` unset.

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
