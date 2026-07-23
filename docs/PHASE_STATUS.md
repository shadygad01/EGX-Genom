# Phase Status — MASTER_PROMPT.md's 18 Systems

The living audit the charter requires. Updated whenever a system's status
changes. Status: **DONE** (Definition of Done met, with any remaining gaps
being external/business-blocked and named) / **PARTIAL** / **NOT STARTED**.

Cross-cutting note on what DONE means here: the *architecture and
engineering* are production-shaped and fully tested; the platform still
runs on placeholder market data. Every conclusion the system produces is
only as real as its data feed, and the single largest open item for a true
Production 1.0 is the licensed EGX data vendor — a business decision
(cost/coverage/contract) explicitly reserved for the user. See
`docs/ROADMAP.md`.

| # | System | Status | Evidence / remaining gaps |
|---|--------|--------|---------------------------|
| 01 | Foundation | **DONE** | `domain/`, `storage/`, `config.py`; reused unmodified by every later store; CI green. |
| 02 | Data Platform | **DONE** | Provider/fallback interfaces, snapshots(+repo), quality checks, split/dividend adjustment, plus the Data Acquisition Program (`sources/`+`collectors/`): a 51-source registry cataloguing every named free source across 9 categories, with real collectors for Stooq (EGX+global daily OHLCV), FRED (macro series), and generic RSS/Atom (news) — each enforcing robots.txt/rate limits/retries, wrapping every fetch in a provenance-carrying `RawDocument`, mechanically scoring the charter's 7 quality dimensions, and withholding (never silently degrading) batches below the confidence floor. Collected data materializes into the same CSV layout `LocalCsvDataProvider` reads — no new provider needed. Blocked-external: licensed EGX vendor for guaranteed-accurate real-time/official data (business decision) remains the gap this doesn't close; sources needing a user-supplied API key (`NEEDS_KEY`) or ToS clarification (`TOS_REVIEW`) are catalogued but deliberately not collected. |
| 03 | Event Platform | **DONE** | Fingerprint identity, taxonomy/ontology, entity resolution, dedup/conflict/lifecycle, `EventPlatform` sole write path, graph projection. Blocked-external: political/technical feeds, NLP entity linking. |
| 04 | Market Memory | **DONE** | `MarketState` (snapshot+universe+sectors+events+session), `TradingCalendar` (fixed holidays as rules; movable as explicit placeholder table). Blocked-external: authoritative movable-holiday dates. |
| 05 | Knowledge Graph | **DONE** | Versioned nodes/edges, provenance-derived builder, shortest-path + n-hop subgraph queries. Deferred by choice: dedicated graph DB (swap behind `Repository[T]` when scale demands). |
| 06 | Alpha Genome | **DONE** | Immutable genes, `mutate()` (single-parent), `merge()` (multi-parent synthesis), lineage walk, status machine; never overwrites. |
| 07 | Research OS | **DONE** | TaskGraph/Artifacts/Sessions plus `DailyResearchPipeline` — the full 8-gate walk wired to real validators, board, causal gate, adversarial scientist, genome, papers, graph. End-to-end tested incl. rejection honesty and determinism. |
| 08 | Scientist Framework | **DONE** (5 of 8 agents real) | MarketStructure, Macro, CorporateEvents, Liquidity, TechnicalStructure real; News/FinancialPerformance/HistoricalPatterns are honest stubs, all data-blocked (NLP, fundamentals feed, long history). Adversarial: 6 of 9 attacks real; 3 data/harness-blocked, reported `attempted=False`. |
| 09 | Feature Discovery | **DONE** | Three autonomous generators (pairwise correlation, momentum, volatility) over three registered feature definitions; candidates versioned+evidenced. |
| 10 | Experiment Factory | **DONE** | Statistic dispatch by asset arity; CV/bootstrap/walk-forward/OOS/sensitivity real (scipy-backed); stress adapter; Monte Carlo an explicit placeholder (needs a simulator — research decision). |
| 11 | Validation Framework | **DONE** | `SignificanceThresholdValidator`, `NaiveDirectionalBacktester` (costs explicitly out of scope, stated), `HistoricalWorstWindowStressTester` (scenario located in real data, not simulated). Deferred: cost-aware portfolio-level backtesting (with 15's future optimizer). |
| 12 | Review Board | **DONE** (4 of 5 reviewers real) | Statistician, Risk, Economist (structural coherence, not economic truth — stated), PeerValidator (independent replication). Historical reviewer data-blocked. Board wired into the pipeline before `promote()`. |
| 13 | Runtime Engine | **DONE** | `RuntimeEngine.run_range`: deterministic, per-day failure isolation, non-trading days recorded not skipped silently, persistent run ledger. OS-level scheduling = deployment config (18). |
| 14 | Prediction Intelligence | **DONE** (v1) | `KnowledgeWeightedHorizonModel`: predictions derived exclusively from promoted knowledge; no knowledge → no prediction. Trained statistical models deferred until years of real data exist (data-blocked, would otherwise be fabricated science). |
| 15 | Portfolio Intelligence | **DONE** (v1) | `PortfolioConstructor`: risk-adjusted confidence-discounted scoring, capped proportional weights, cash fallback, full explanation. Deferred: covariance-based optimization (needs real data depth). |
| 16 | Explainability Engine | **DONE** | Six-question `Explanation` with structured `evidence_refs` everywhere; `similar_historical_cases` populated from real recorded events via the Event Platform. |
| 17 | Continuous Learning | **DONE** (v1) | `ContinuousLearningMonitor`: realized performance recorded on knowledge+genes from real later-window data; mechanical sign-disagreement retirement policy with audited reasons. |
| 18 | Production Infrastructure | **PARTIAL** | Engineering-closeable parts done: integrity-checked backup/verify/restore, CLI (`run`/`status`/`backup`/`restore`), Dockerfile, CI. Business-blocked: cloud provider + payment, secrets management service, managed scheduling, API authentication context, monitoring/alerting stack. Named in `docs/ROADMAP.md`. |

## What Production 1.0 still needs (all business-blocked)

1. **Licensed EGX market data vendor** — the single gating decision.
2. Cloud/deployment target + secrets management + scheduler (18).
3. Authoritative EGX holiday calendar + universe/sector feeds (04/02).
4. Optional data feeds unlocking the remaining stubs: news NLP source,
   fundamentals feed, long-history archive (08/12 stragglers).

Everything engineering-closeable without those inputs is closed and tested
(273 Python tests + 33 TypeScript tests green).

## Dashboard dual-provider architecture (post-Data-Acquisition-Program)

The web dashboard (`api`/`web`, presentation layer) now runs on a
`DashboardDataProvider` abstraction — `StaticJsonProvider` (GitHub Pages:
JSON artifacts generated by the real research pipeline) and `ApiProvider`
(a hosted `api/`), both serving the exact same eight resources
(knowledge/events/patterns/recommendations/market_state/runtime_metrics/
system_status/source_registry) from the exact same pydantic-derived
contracts. See `docs/ARCHITECTURE.md`'s "Dashboard data providers"
section for the full design. This doesn't correspond to a new charter
system — it's a presentation-layer capability enabling the already-DONE
research engine's real output to reach a static deployment target with no
backend, which the charter's System 18 (Production Infrastructure) never
required in the first place.

## Data Acquisition Program (post-Epoch-II, within System 02's scope)

Per the standing charter, the next objective after all 18 systems reached
DONE/PARTIAL was not more AI — it was building the largest legally
accessible free research dataset for EGX, since no research conclusion can
outrun its data. This closed the *engineering* half of that goal:

- `docs/DATA_ACQUISITION.md` — full design (source registry schema,
  collector architecture, quality scoring, provenance, legal-compliance
  enforcement in code, not just policy).
- 51 sources catalogued across all 9 named categories (Official, Company,
  Market Data, News, Arabic News, Macroeconomic, Global Markets,
  Alternative, Research); honestly split IMPLEMENTED (4) / PLANNED (35) /
  NEEDS_KEY (4) / TOS_REVIEW (8).
- 3 real collectors (Stooq, FRED, generic RSS/Atom) fully tested against
  recorded-format fixtures — no live network calls in the test suite (this
  sandbox has no outbound egress; live fetching is a deployment-time
  concern only).
- Remaining catalogued-but-uncollected sources are blocked on exactly one
  of: endpoint/config verification (PLANNED — engineering-closeable over
  time, not a business decision), a user-registered API key (NEEDS_KEY —
  business decision: which paid/free-tier key to obtain), or ToS ambiguity
  around automated collection/redistribution (TOS_REVIEW — business/legal
  decision). None of these are silently skipped; each is named in the
  registry with its blocking reason.
