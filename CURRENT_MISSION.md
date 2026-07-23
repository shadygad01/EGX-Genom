# Current Mission

**Build AGX toward collecting, processing, learning from, and presenting
real Egyptian market data — Engineering Ownership Phase.**

The project owner has handed over full engineering ownership: no more
isolated tasks, no waiting for approval between milestones. Architecture,
the Data Acquisition Platform, the runtime pipeline, and Mission Control
are all declared complete — the work now is closing every remaining
engineering-closeable gap toward real data, in this exact business
priority order:

1. Official Egyptian Exchange integration
2. Universe Engine
3. Investor Relations discovery
4. Corporate disclosures
5. Financial statement collection
6. Historical backfill
7. Live incremental synchronization
8. Central Bank of Egypt
9. FRA
10. CAPMAS
11. Enterprise
12. Mubasher
13. Zawya
14. Reuters
15. Trading Economics
16. Every additional legally accessible free public source discovered automatically

## What this phase engineered

**Universe Engine (priority 2).** `universe.UniverseProvider` had only
`StaticUniverseProvider`, a fixed placeholder — no path existed for a real
collected constituent list to reach it. Closed:

- **`IndexConstituent`** (`universe/constituent.py`): `{index, ticker,
  company_name, as_of_date}` — carrying a date per row, not a single
  overwritten snapshot, so membership queries stay point-in-time-correct
  (no look-ahead bias, the same guarantee every other query in this
  platform gives).
- **`CollectionBatch.index_constituents`** (+ `corporate_events`, built at
  the same time since both are new record types the same materialization
  path needed) — `CollectionService` now writes `universe/<INDEX>.csv`,
  merged by `(ticker, as_of_date)`, with full provenance tracing.
- **`CollectedUniverseProvider`** (`universe/collected.py`): reads that
  CSV, returning the latest snapshot at-or-before the query date, or `{}`
  if nothing's been collected yet — never fabricated. **`FallbackUniverseProvider`**
  composes it with `StaticUniverseProvider`, mirroring `FallbackDataProvider`
  exactly. Wired into `production.pipeline`'s `_stage_market_memory` and
  `cli.py`'s `discover-sources`, so a real collected universe is preferred
  the instant one exists, with zero further code changes.
- **`IndexConstituentCollector`** (`collectors/index_constituents.py`):
  the collection half — a generic, header-matching CSV parser (finds
  ticker/name columns by header text, not a fixed column order). Fully
  built and tested, exactly like the AlphaVantage/FMP collectors sitting
  at `NEEDS_KEY` — it cannot be wired into the live pipeline until
  `egx_official`'s real endpoint is verified and its status flips from
  `PLANNED` to `IMPLEMENTED` (`AD-24`), since inventing a specific parser
  for an unverified page would be guessing a wire format, not parsing a
  real one (TD-30).

**Corporate disclosures (priority 4), closing TD-24.** `CorporateEvent`
had a schema and a `DataProvider` read path, but nothing produced one.
Closed with `collectors.corporate_event_classifier`: a declared headline
keyword heuristic (dividend/split/merger/buyback/earnings/etc., same
posture as the legality and company-directory heuristics, TD-29) that
`RssNewsCollector`'s new `classify_corporate_events` flag applies per
entry, populating `batch.corporate_events` alongside the always-produced
`NewsItem` — one disclosure, two views, not two collectors. Wired into
`collector_plan.py`'s `rss_generic` mock/replay collector. **Verified
live**: a mock-mode production pipeline run now writes real
`COMI/EARNINGS` and `MFPC/DIVIDEND` rows to `corporate_events.csv` from
the existing mock RSS headlines — no fabrication, a real (if narrow)
capability. Headline-only by design (RSS/ToS terms): classified events
carry no numeric detail (split ratio, dividend amount), so they stay
correctly informational-only until a fuller-text source (an IR disclosure
PDF) exists.

**Investor Relations discovery (priority 3)** — no new engineering this
phase; it was fully built two missions ago (`generate_company_ir_targets`,
`discover_company_directory_links`, `run_catalog`) and now automatically
scales the moment the Universe Engine's collector (or a user-supplied
list) supplies a real constituent set, per its original design.

## Priorities 1, 6, 7: why no new code this phase

- **Priority 1 (EGX official)**: blocked on the same two named constraints
  below — its `SourceSpec` (`egx_official`) is fully seeded and its
  `TargetOrganization` fully wired into `run_catalog`; only real endpoint
  verification (network access) can move it past `PLANNED`.
- **Priority 6 (historical backfill)**: already automatic by design, no
  separate logic exists or is needed — every collector (including the new
  `IndexConstituentCollector`) fetches a source's full available series by
  construction; a first real run *is* the backfill.
- **Priority 7 (live incremental sync)**: already satisfied by design too
  — every materialization writer (price bars, macro observations,
  corporate events, index constituents) merges by natural key and
  overwrites idempotently; a subsequent run naturally only changes what's
  actually new, with no separate "incremental mode" required.

## The one real constraint, stated plainly (unchanged across four missions)

This sandbox has no outbound network egress to arbitrary hosts — confirmed
directly and repeatedly. Two consequences:

1. **Priority 1 (EGX official) and everything gated on it (2/3 at real
   scale, 8–16) cannot connect live** — every mechanism is built, tested,
   and wired; only real endpoint verification is missing.
2. **No real, complete EGX30/EGX70 constituent list exists in this
   codebase** — a business decision reserved for the project owner (see
   `docs/DATA_ACQUISITION.md`); fabricating one from training-data recall
   would violate the platform's anti-fabrication principle.

Everything engineering could complete without either input has been
completed. See `NEXT_MISSIONS.md` for what runs automatically the moment
either clears, and what's next regardless: **Financial Statement
Collection (priority 5)**, which needs no live source to design the
canonical schema, collector shape, and provider read path — the same
generic-infrastructure-now pattern this phase used for the Universe
Engine and corporate events.
