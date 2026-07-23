# Production Data Acquisition Program

Data collection is a core product of AGX: the goal is the largest
continuously growing structured research database for the Egyptian Stock
Exchange, built exclusively from legally accessible free sources, where no
source is authoritative by itself — truth emerges through corroboration
(the Event Platform's existing fingerprint/corroboration/conflict
machinery is the arbiter; this program feeds it).

## Architecture

```
sources/    SourceSpec (full charter field set) + SourceRegistry + seed catalog
collectors/ RawDocument (provenance envelope) + Collector ABC + FetchPolicy
            + concrete collectors + quality scoring + CollectionService
            + materialization into the local CSV data layout
```

- **Adapters only.** No source-specific logic exists outside a collector.
  Collectors produce canonical candidates (`PriceBar`, `MacroObservation`,
  `NewsItem`, candidate `Event`s); identity, dedup, corroboration,
  conflict resolution, lifecycle, and graph projection stay exclusively in
  the Event Platform.
- **Provenance envelope.** Every fetched payload becomes a `RawDocument`
  carrying: source id, collector name+version, fetch timestamp, original
  URL, sha256 content hash, schema version, license, and append-only
  normalization/validation history. Parsed values reference their raw
  document id, so any downstream value walks back to the exact bytes
  collected.
- **Quality is mechanical.** `quality.py` computes the seven charter
  scores (coverage, freshness, reliability, consistency, completeness,
  validation, confidence) from measurable inputs; `consistency` is
  honestly `None` until a second source covers the same values —
  never invented. The composite confidence is a documented formula over
  the measured components.
- **Materialization.** Validated price/macro/news batches are written into
  the local CSV layout `MockDataProvider` already reads (aliased
  `LocalCsvDataProvider` — it was always just a local-CSV provider; the
  "mock" framing described its *content*, not its mechanism). Collected
  real data therefore flows into snapshots, the pipeline, and everything
  downstream with zero further integration.

## Source catalog policy (honesty rules)

Every source named by the program is catalogued in the seed registry with
an explicit status:

- **IMPLEMENTED** — a real collector exists, tested against recorded-format
  fixtures; runs live wherever network egress exists.
- **PLANNED** — catalogued with known access details; collector not yet
  written (most are one configuration of an existing generic collector,
  e.g. an RSS feed URL).
- **NEEDS_KEY** — free tier requires a user-registered API key
  (AlphaVantage, FMP, Polygon, Tiingo). Keys are credentials: a business/
  user action, never fabricated or bypassed.
- **TOS_REVIEW** — access exists but redistribution/automation terms are
  ambiguous (Yahoo Finance unofficial API, Investing.com, TradingView,
  Google Trends automation, LinkedIn). Not collected until the review
  clears — "respect Terms of Service" is a hard rule, so ambiguity blocks.
- **Declared priors, not measurements.** `reliability_score` etc. in seed
  entries are documented starting priors (official regulator > exchange >
  aggregator > social), replaced by measured values as collection history
  accumulates. `data_quality_score` starts `None` — it is only ever
  measured.

## Implemented collectors (v1)

| Collector | Source(s) | Why first |
|---|---|---|
| `StooqPriceCollector` | Stooq daily CSV (`stooq.com/q/d/l/?s=...&i=d`) | Free, no auth, explicit CSV download endpoint, permissive personal-use terms; covers EGX symbols (`.eg` suffix convention) and global benchmarks (indices, commodities, FX). |
| `FredCsvCollector` | FRED `fredgraph.csv?id=SERIES` | Free, no auth for CSV export, US-government open data; covers oil, dollar index, treasury yields, and other global-macro series the vision requires. |
| `RssNewsCollector` | Any RSS/Atom feed | One generic, layout-tolerant collector covers every news source that publishes a feed (most named Arabic/English outlets); per-source configuration lives in the registry entry, not in code. |

All three parse recorded-format fixtures in tests (clearly labeled
synthetic fixtures in the real wire format — never presented as collected
market data). Live fetching uses stdlib urllib with proxy support,
per-source rate limiting, bounded retries with backoff, timeout, and a
robots.txt check for HTML-ish fetches; it is exercised in deployment, not
in unit tests.

## Legal compliance (enforced, not aspirational)

- `FetchPolicy.respect_robots` blocks fetches disallowed by robots.txt.
- No collector authenticates, bypasses paywalls, or touches restricted
  data; NEEDS_KEY sources idle until the user supplies their own key.
- Every `SourceSpec` records `license` and `terms_of_use_url`; TOS_REVIEW
  status blocks collection outright.
- Rate limits are per-source configuration honored by the fetcher.

## Deployment note

This development environment has no outbound network egress, so live
collection was validated at the parser/protocol level against fixtures;
first live runs happen wherever the runtime is deployed with egress
(a System-18 deployment decision).
