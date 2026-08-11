# Pattern Discovery — Data Audit

Produced by the EGX30 Autonomous Pattern Discovery Engine mission
(2026-08-11), step 2 of its mandated implementation order ("do not proceed
to implementation until this audit is complete"). This is a factual
inventory of every dataset that actually exists in this repository or is
reachable from it today — not a design document. It answers one question
per dataset: **can this be used, safely, to discover and validate a
market-outcome relationship without look-ahead bias?**

Companion to `docs/DATA_ACQUISITION.md` (the general source-acquisition
program) and `docs/TRUTH_PRESERVATION_POLICY.md` (`AD-60`, the zero-
fabrication rules this audit's conclusions must respect). Nothing below
invents coverage that doesn't exist; several rows conclude `usable_for_backtest:
NO` and that is the correct, expected outcome of an honest audit — see the
mission's own acceptance criterion 16 ("the system can legitimately return
ZERO validated patterns").

## Method

For every CSV actually committed under `research/data/` (real, collected
data) and `research/data/mock/` (synthetic placeholder data,
`data.mock_provider.MockDataProvider`'s fixture set), this audit records:
row/observation counts by direct inspection (`wc -l`, `head`, `tail`), the
originating collector/source per `sources/catalog.py`, and whether the
platform's existing point-in-time machinery
(`data.point_in_time.is_knowable`, `universe.collected.CollectedUniverseProvider`)
already protects it or leaves a gap.

**A decisive environment finding**: this session's outbound network policy
denies all requests to Yahoo Finance, StockAnalysis, and Mubasher (a live
`curl` to `query1.finance.yahoo.com` returned `403` — "gateway answered 403
to CONNECT (policy denial or upstream failure)", confirmed via
`$HTTPS_PROXY/__agentproxy/status`'s `recentRelayFailures`). The
`egx_price_composite` collector (`collectors/egx_prices.py`) is real,
`IMPLEMENTED`, and — per its Yahoo leg's `range=max` query — *could* pull
deep multi-year daily history once run somewhere with vendor network
access, but **cannot be run from this session**. This audit reports the
data that actually exists in the repository today, not a hypothetical
post-collection state.

## Dataset inventory

| dataset | source | frequency | historical coverage | availability timestamp | revisions | missingness | usable_for_backtest | limitations |
|---|---|---|---|---|---|---|---|---|
| EGX price OHLCV (mock) | `research/data/mock/prices/{COMI,MFPC}.csv` — synthetic fixture, `MockDataProvider` | daily | **10 trading days**, 2026-06-01→2026-06-14, **2 of 30** EGX30 tickers | synthetic; no real publication lag to model (same-day, by construction) | none (static fixture, flagged stale — `docs/TECHNICAL_DEBT.md` item on mock prices "last date 2026-06-14 vs. later pipeline runs") | 28/30 EGX30 constituents entirely absent | **NO** | Not real market data and far too short for any statistic requiring dozens of independent observations (a single 5-day forward-return target already consumes half the series). Only fit for exercising pipeline mechanics/tests, never for a discovery claim. |
| EGX price OHLCV (real, collector) | `egx_price_composite` (Yahoo `range=max` + StockAnalysis + Mubasher fallback), `sources/catalog.py` `IMPLEMENTED` | daily (EOD) | **unknown/uncollected** — collector has never been run in this repository; no `<data_dir>/prices/*.csv` output is committed anywhere | Yahoo/StockAnalysis publish EOD bars with no documented "became public at" timestamp; the collector's own comment treats a bar older than 3 days as stale, i.e. assumes next-day-ish availability, but this is an operational heuristic, not a vendor-cited SLA | Yahoo's `events.dividends/splits` arrays reflect **today's** view of history, not the view as of any past date — a split announced after the fact could silently backfill; this is why `data.adjustments.compute_adjusted_closes` deliberately works from raw (unadjusted) `PriceBar.close` plus an explicit, dated `CorporateEvent` list rather than trusting a vendor's own "adjusted close" column, which already protects against this specific risk | n/a — no data collected yet | **NOT YET — requires a real collection run outside this session's network policy** | The mechanism for real depth exists and is real code, not a stub, but until it's actually run (from an environment with vendor network access) there is zero real price history in this repository. Once run, treat Yahoo/StockAnalysis EOD bars as knowable `trade_date + 1` calendar day at the earliest (conservative), never same-day. |
| Macro: Brent crude USD | `research/data/macro/BRENT_USD.csv`, FRED (`fred`, `IMPLEMENTED`) | daily | 278 obs, 2025-07-02 → 2026-08-06 (~13 months) | `data.point_in_time.ASSUMED_PUBLICATION_LAG_DAYS["fred"] = 0` (no assumed delay; FRED commodity/FX series are same/next-day) | Spot-price series; FRED does not revise past printed values for this series type | none observed in the sampled range | **YES** | Already gated by `is_knowable()` inside `build_snapshot()` when `macro_series_sources={"BRENT_USD": "fred"}` is supplied — safe as-is. ~13 months is workable for macro-level regime features, not for a full multi-year regime study. |
| Macro: EGP/USD | `research/data/macro/EGP_USD.csv`, FRED | daily | 286 obs, 2025-07-01 → 2026-08-06 (~13 months) | same as Brent — 0-day assumed lag | Spot FX fixing; not revised | none observed | **YES** | Same posture as Brent. |
| Macro: Egypt CPI inflation | `research/data/macro/egypt_cpi_inflation.csv`, World Bank (`worldbank`, `IMPLEMENTED`) | **annual** | 13 obs, 2014-12-31 → 2025-12-31 | `ASSUMED_PUBLICATION_LAG_DAYS["worldbank"] = 30` — a declared conservative **floor**, not a measured lag; this codebase's own live-verified evidence found a real World Bank observation collectible ~165 days after period-end (`docs/PHASE_STATUS.md`) | **World Bank national-accounts figures are routinely revised in later releases.** This dataset stores only the latest collected value per period, not a first-release vintage — there is no way, today, to tell a discovery process "use only what was known at the time," because only one (possibly since-revised) number exists per year. | none in range, but only 1 obs/year — cannot support any within-year daily-panel join without forward-filling a single stale value for ~365 days | **CAUTION — LOOK-AHEAD-SAFE ORDERING ONLY, REVISION-UNSAFE VALUE** | Ordering (don't use before `known_as_of()`) is protected; the *value itself* may silently be a revised figure the market never actually saw at that historical date. This is exactly the "revised-data leakage" risk the mission calls out by name. Any feature built from this series must be documented as carrying this specific, unresolved caveat, never silently treated as clean. |
| Macro: Egypt GDP growth | `research/data/macro/egypt_gdp_growth.csv`, World Bank | annual | 11 obs, 2016-12-31 → 2025-12-31 | same 30-day floor as CPI | same revision risk as CPI (World Bank GDP growth is a canonical example of a heavily-revised series) | 1 obs/year | **CAUTION — same as CPI** | Same caveat as CPI; additionally too sparse (11 points) to itself be split into discovery/validation samples. |
| Macro: Egypt interest rate | `research/data/macro/egypt_interest_rate.csv`, World Bank | annual | 11 obs, 2015-12-31 → 2024-12-31 | same 30-day floor | same revision risk | 1 obs/year | **CAUTION — same as CPI** | Same as above. Note this is a real lending/deposit-rate proxy, not CBE's actual overnight/policy rate (no CBE policy-rate collector is `IMPLEMENTED` — `cbe` is `DISABLED` in `sources/catalog.py`). |
| Universe membership (EGX30) | `research/data/universe/EGX30.csv`, `egx_universe_seed` | **single snapshot** | 31 rows (30 constituents + header), `as_of_date=2026-07-26` only | `CollectedUniverseProvider.constituents(as_of)` correctly returns "the latest snapshot at or before `as_of`" — no *future* snapshot ever leaks backward | n/a — one dated snapshot, not a revised series | **No historical reconstitution history at all**: every `as_of` before 2026-07-26 receives the same 2026-07-26 constituent list, because it's the only snapshot that exists | **NO for any historical `as_of`** | This is real, genuine **universe/survivorship-bias leakage** if used to define "the EGX30" on any past date: real index reconstitutions add/drop constituents periodically, and this file cannot distinguish "was in the index on 2025-01-15" from "is in the index today." Safe only for `as_of >= 2026-07-26` (effectively "today," not historical backtesting). Mission item 10 ("different EGX30 constituents where historical membership is available") is honestly **not available** — flagged rather than faked. |
| Universe membership (EGX70) | `research/data/universe/EGX70.csv`, `egx_universe_seed` | single snapshot | 71 rows, `as_of_date=2026-07-26` only | same as EGX30 | n/a | same gap as EGX30 | **NO for any historical `as_of`** | Same reasoning as EGX30. |
| News | `research/data/news_history/news_discovery.csv`, GDELT (`gdelt`, `IMPLEMENTED`) | irregular/event-driven | 285 rows, sampled dates cluster around 2024-08 | `published_at` date exists; GDELT aggregates from source publication with same-day-ish latency, but no per-article confirmed-public timestamp is stored | Articles are immutable once collected (no re-fetch/edit tracking) | **Severe**: `tickers` column is empty for the large majority of sampled rows (spot-checked: general Egypt/world news, not EGX-company-specific) — see mock's own 3-row `news.csv` for the intended shape (ticker-tagged) vs. this file's actual mostly-untagged reality | **LIMITED** | Usable only for the minority of rows that do carry a real ticker tag, and even those need manual/heuristic relevance verification before being trusted as a feature input. Not usable today as a systematic per-ticker feature source without a dedicated tagging/relevance pass — out of scope for this mission to build (a separate NLP/entity-linking effort). |
| Corporate events (mock) | `research/data/mock/corporate_events.csv` | irregular | 2 events (COMI EARNINGS, MFPC DIVIDEND), synthetic | synthetic | none | only 2 tickers, 2 events total | **NO** | Same synthetic-fixture caveat as mock prices; already exercised by `test_adjustments.py`. |
| Financial statements | none committed | — | **0 rows anywhere in the repository** — `financials/collected.py`'s expected `<data_dir>/financial_statements/<TICKER>.csv` layout has no committed instance under `research/data/` | n/a | n/a | 100% | **NO — does not exist** | `DatasetSnapshot.financial_statements` and `agents.financial_performance.FinancialPerformanceAgent` are real code paths, but nothing populates them in this repository today. Fundamental-transform features (§3 of the mission spec) cannot be generated from real data; the Feature Factory implements them but they will legitimately produce zero fundamental features against current data. |
| Sector classification | none committed (only the 10-ticker `universe.sector.EGX_SECTOR_PLACEHOLDER` hardcoded fallback) | — | 10 hand-picked tickers, not sourced from any dated collection | n/a — hardcoded, not a dataset | n/a | 20/30 EGX30 tickers have no sector at all | **PARTIAL** | Sector-relative/participation features (mission §3 "cross-sectional") can only be computed for the 10 placeholder-covered tickers; the rest silently drop out of any sector-conditioned candidate, which the engine must report as reduced sample size, not paper over. |

## Verdict this audit reaches, honestly

The platform's **point-in-time safeguards that already exist are real and
correctly used** for what data it has (`DatasetSnapshot`'s hard `as_of`
cutoff, `data.point_in_time.is_knowable` for macro publication lag,
`data.adjustments`'s raw-close + explicit-event adjustment convention,
`CollectedUniverseProvider`'s latest-at-or-before snapshot lookup). What's
missing is not point-in-time *logic* — it's **depth**: real, multi-year,
broad-coverage EGX price history does not exist anywhere in this
repository, and the one collector that could produce it cannot reach the
network from this session.

Concretely, this means:

- The canonical research dataset, Feature Factory, and Target Factory can
  and will be built to be **correct** against whatever depth is available
  — but run today, they have at most 10 daily observations across 2
  tickers of real price granularity (mock) plus ~13 months of 2 macro
  series. That is not enough to responsibly generate, let alone validate,
  a single candidate pattern requiring (per this mission's own minimum
  sample requirements) dozens of independent, non-overlapping
  observations.
- **Universe membership before 2026-07-26 cannot be reconstructed
  point-in-time** — any historical backtest implicitly uses today's
  constituent list, a real survivorship-bias exposure this audit refuses
  to paper over.
- **World Bank annual macro series carry unresolved revision risk** — safe
  ordering, unverified value-vintage.
- **Financial statements and systematic ticker-tagged news do not exist**
  as usable inputs today.

Per the mission's explicit acceptance criteria, the correct response to
this is not to invent depth that doesn't exist, but to **build the engine
so it is honest about insufficient data** — every stage below refuses to
manufacture a candidate, statistic, or validated pattern past what its
`min_sample_size`/`min_oos_sample_size` floor allows, and reports exactly
why when it can't proceed. See `docs/PATTERN_DISCOVERY_REPORT.md` for the
actual run against this data and its (expected: zero) validated-pattern
count.
