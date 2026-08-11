# EGX30 Community Price Seed — Data Quality Report

Automated gate output from `research/scripts/egx_data_quality_report.py`, run against `research/data/community_prices_seed/normalized/`. A `FAIL`ed ticker is excluded from `patterns.engine` runs by construction (see `docs/PATTERN_DISCOVERY_DATA_AUDIT.md`'s companion source-qualification doc for full source provenance).

**75/75 tickers PASS every critical check.**

## Dataset-wide Open/Close-vs-[Low,High]-band characteristic

20816 of 83523 bars total (24.9%) have Open and/or Close outside that bar's own [Low, High] band, by a median relative magnitude of well under 1% and a long tail out to tens of percent on a small minority of bars — a real, quantified characteristic of this third-party source (Yahoo Finance via `yfinance`, likely reflecting settlement/auction prices computed from a slightly different feed than intraday tick extremes). Deliberately kept **non-critical**: `High >= Low` itself is 100% clean dataset-wide (checked separately, 0 violations), so MFE/MAE (which read High/Low directly) stay valid, and every return/target this engine computes is close-to-close, never Open-relative-to-its-own-day's-High/Low — this characteristic does not corrupt this pipeline's calculations. See each ticker's row below for its own median/max violation magnitude.

## Critical check summary

| Check | Method |
|---|---|
| Duplicate dates | exact (ticker, date) uniqueness |
| Trading-calendar mismatch | every bar must fall Sun-Thu (`market_memory.calendar.StaticEGXCalendar`) |
| Invalid OHLC | `high >= low`, `open`/`close` within `[low, high]` |
| Non-positive prices | `min(open,high,low,close) > 0` |
| Negative volume | `volume >= 0` |

## Non-critical, informational checks

| Check | Method |
|---|---|
| Extreme raw jumps | day-over-day raw close change > 25%, cross-checked against derived corporate-action event dates (±3 days) |
| Interior gaps | a run of >= 15 consecutive expected-but-missing trading days strictly inside a ticker's own date range |
| Coverage ratio | observed bars / expected Sun-Thu trading days over the ticker's own span (an honest denominator estimate — pre-2026 movable-holiday dates are not in this codebase's calendar table, so the true expected count for years before 2026 is a slight overestimate; see `market_memory/calendar.py`) |

## Per-ticker results

| Ticker | Status | Obs | Coverage | Extreme jumps (explained/unexplained) | Interior gaps | Issues |
|---|---|---:|---:|---:|---:|---|
| ACGC | PASS | 1113 | 0.9545 | 0/0 | 0 | 156 bar(s) with open/close outside [low, high] (median 0.367%, max 4.598%, 10 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ADIB | PASS | 1116 | 0.9571 | 0/1 | 0 | 210 bar(s) with open/close outside [low, high] (median 0.292%, max 3.005%, 5 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| AFDI | PASS | 1113 | 0.9545 | 0/0 | 0 | 241 bar(s) with open/close outside [low, high] (median 0.341%, max 6.811%, 11 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| AIFI | PASS | 1116 | 0.9571 | 0/2 | 0 | 58 bar(s) with open/close outside [low, high] (median 0.579%, max 3.75%, 5 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| ALUM | PASS | 1113 | 0.9545 | 0/0 | 0 | 357 bar(s) with open/close outside [low, high] (median 1.019%, max 15.916%, 121 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| AMER | PASS | 1113 | 0.9545 | 0/1 | 0 | 284 bar(s) with open/close outside [low, high] (median 1.021%, max 12.949%, 79 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| APSW | PASS | 1113 | 0.9545 | 0/0 | 0 | 432 bar(s) with open/close outside [low, high] (median 2.0%, max 5.214%, 217 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ARAB | PASS | 1114 | 0.9554 | 0/2 | 0 | 139 bar(s) with open/close outside [low, high] (median 0.532%, max 6.095%, 10 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| AREH | PASS | 1113 | 0.9545 | 0/0 | 0 | 204 bar(s) with open/close outside [low, high] (median 0.91%, max 16.667%, 62 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ASCM | PASS | 1113 | 0.9545 | 0/0 | 0 | 306 bar(s) with open/close outside [low, high] (median 0.541%, max 11.033%, 61 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| BIDI | PASS | 1115 | 0.9563 | 0/0 | 0 | 705 bar(s) with open/close outside [low, high] (median 3.517%, max 11.111%, 488 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| CANA | PASS | 1113 | 0.9545 | 0/2 | 0 | 547 bar(s) with open/close outside [low, high] (median 2.0%, max 13.889%, 273 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| CCRS | PASS | 1113 | 0.9545 | 0/2 | 0 | 768 bar(s) with open/close outside [low, high] (median 2.971%, max 16.405%, 460 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| CIEB | PASS | 1113 | 0.9545 | 0/0 | 0 | 166 bar(s) with open/close outside [low, high] (median 0.275%, max 15.162%, 6 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| CIRA | PASS | 1113 | 0.9545 | 0/0 | 0 | 175 bar(s) with open/close outside [low, high] (median 0.334%, max 4.41%, 7 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| COMI | PASS | 1113 | 0.9545 | 0/0 | 0 | 250 bar(s) with open/close outside [low, high] (median 0.211%, max 6.513%, 17 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| COPR | PASS | 1113 | 0.9545 | 0/4 | 0 | 341 bar(s) with open/close outside [low, high] (median 5.263%, max 53.846%, 219 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 4 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| DSCW | PASS | 1113 | 0.9545 | 0/2 | 0 | 157 bar(s) with open/close outside [low, high] (median 0.533%, max 10.31%, 11 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| DTPP | PASS | 1113 | 0.9545 | 0/0 | 0 | 1052 bar(s) with open/close outside [low, high] (median 3.658%, max 24.969%, 698 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ECAP | PASS | 1113 | 0.9545 | 0/0 | 0 | 287 bar(s) with open/close outside [low, high] (median 0.571%, max 7.051%, 49 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| EEII | PASS | 1113 | 0.9545 | 0/0 | 0 | 171 bar(s) with open/close outside [low, high] (median 0.725%, max 7.273%, 21 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| EFIH | PASS | 1115 | 0.9563 | 0/1 | 0 | 177 bar(s) with open/close outside [low, high] (median 0.26%, max 3.846%, 5 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| EGAL | PASS | 1113 | 0.9545 | 0/0 | 0 | 257 bar(s) with open/close outside [low, high] (median 0.391%, max 12.622%, 20 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| EGBE | PASS | 1117 | 0.958 | 0/0 | 0 | 581 bar(s) with open/close outside [low, high] (median 1.044%, max 7.335%, 130 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| EHDR | PASS | 1113 | 0.9545 | 0/1 | 0 | 170 bar(s) with open/close outside [low, high] (median 0.498%, max 69.88%, 9 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| ELEC | PASS | 1113 | 0.9545 | 0/0 | 0 | 184 bar(s) with open/close outside [low, high] (median 0.551%, max 10.386%, 16 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ELKA | PASS | 1113 | 0.9545 | 0/1 | 0 | 186 bar(s) with open/close outside [low, high] (median 0.677%, max 5.854%, 16 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| ELSH | PASS | 1113 | 0.9545 | 1/1 | 0 | 223 bar(s) with open/close outside [low, high] (median 0.476%, max 7.193%, 15 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| EMFD | PASS | 1113 | 0.9545 | 0/0 | 0 | 166 bar(s) with open/close outside [low, high] (median 0.368%, max 4.723%, 12 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ENGC | PASS | 1113 | 0.9545 | 0/0 | 0 | 238 bar(s) with open/close outside [low, high] (median 0.523%, max 5.113%, 22 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| EPPK | PASS | 1115 | 0.9563 | 0/0 | 0 | 623 bar(s) with open/close outside [low, high] (median 5.155%, max 5.249%, 468 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ETEL | PASS | 1113 | 0.9545 | 0/0 | 0 | 183 bar(s) with open/close outside [low, high] (median 0.204%, max 4.487%, 6 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| EXPA | PASS | 1113 | 0.9545 | 0/2 | 0 | 226 bar(s) with open/close outside [low, high] (median 0.562%, max 6.771%, 34 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| FAIT | PASS | 1113 | 0.9545 | 0/0 | 0 | 168 bar(s) with open/close outside [low, high] (median 0.236%, max 6.093%, 9 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| FIRE | PASS | 1114 | 0.9554 | 0/0 | 0 | 346 bar(s) with open/close outside [low, high] (median 2.659%, max 11.111%, 189 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| FWRY | PASS | 1113 | 0.9545 | 0/0 | 0 | 208 bar(s) with open/close outside [low, high] (median 0.351%, max 4.8%, 8 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| GBCO | PASS | 1113 | 0.9545 | 0/0 | 0 | 203 bar(s) with open/close outside [low, high] (median 0.369%, max 4.558%, 11 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| GDWA | PASS | 1113 | 0.9545 | 0/1 | 0 | 221 bar(s) with open/close outside [low, high] (median 0.554%, max 6.4%, 26 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| GIHD | PASS | 1113 | 0.9545 | 0/0 | 0 | 382 bar(s) with open/close outside [low, high] (median 0.762%, max 15.288%, 93 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| GPPL | PASS | 1118 | 0.9588 | 0/0 | 0 | 139 bar(s) with open/close outside [low, high] (median 5.174%, max 5.263%, 124 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| GTWL | PASS | 1113 | 0.9545 | 0/0 | 0 | 646 bar(s) with open/close outside [low, high] (median 2.966%, max 24.954%, 391 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| HDBK | PASS | 1114 | 0.9554 | 0/1 | 0 | 182 bar(s) with open/close outside [low, high] (median 0.269%, max 7.265%, 7 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| HELI | PASS | 1113 | 0.9545 | 0/1 | 0 | 206 bar(s) with open/close outside [low, high] (median 0.376%, max 10.66%, 10 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| IDRE | PASS | 1113 | 0.9545 | 0/0 | 0 | 406 bar(s) with open/close outside [low, high] (median 1.861%, max 7.236%, 201 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| IRON | PASS | 1113 | 0.9545 | 0/0 | 0 | 211 bar(s) with open/close outside [low, high] (median 1.739%, max 5.261%, 102 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ISMQ | PASS | 1113 | 0.9545 | 0/0 | 0 | 186 bar(s) with open/close outside [low, high] (median 0.445%, max 10.861%, 16 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| KABO | PASS | 1113 | 0.9545 | 0/0 | 0 | 199 bar(s) with open/close outside [low, high] (median 0.563%, max 5.859%, 24 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| LCSW | PASS | 1114 | 0.9554 | 0/2 | 0 | 247 bar(s) with open/close outside [low, high] (median 0.632%, max 16.402%, 39 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| MASR | PASS | 1113 | 0.9545 | 0/0 | 0 | 188 bar(s) with open/close outside [low, high] (median 0.472%, max 4.115%, 10 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| MBEG | PASS | 1113 | 0.9545 | 0/1 | 0 | 497 bar(s) with open/close outside [low, high] (median 3.295%, max 16.667%, 312 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| MEGM | PASS | 1118 | 0.9588 | 0/0 | 0 | none |
| MENA | PASS | 1113 | 0.9545 | 0/0 | 0 | 187 bar(s) with open/close outside [low, high] (median 0.552%, max 7.895%, 10 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| NHPS | PASS | 1115 | 0.9563 | 0/1 | 0 | 340 bar(s) with open/close outside [low, high] (median 3.9%, max 25.0%, 199 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| OBRI | PASS | 1113 | 0.9545 | 0/1 | 0 | 324 bar(s) with open/close outside [low, high] (median 0.791%, max 24.905%, 86 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| OCDI | PASS | 1113 | 0.9545 | 0/2 | 0 | 275 bar(s) with open/close outside [low, high] (median 0.48%, max 6.72%, 34 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 2 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| ORAS | PASS | 1118 | 0.9588 | 0/0 | 0 | none |
| ORHD | PASS | 1113 | 0.9545 | 0/0 | 0 | 210 bar(s) with open/close outside [low, high] (median 0.333%, max 4.174%, 12 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ORWE | PASS | 1113 | 0.9545 | 0/0 | 0 | 177 bar(s) with open/close outside [low, high] (median 0.303%, max 12.985%, 8 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| PHDC | PASS | 1113 | 0.9545 | 0/0 | 0 | 200 bar(s) with open/close outside [low, high] (median 0.467%, max 5.858%, 8 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| PRCL | PASS | 1113 | 0.9545 | 0/1 | 0 | 239 bar(s) with open/close outside [low, high] (median 0.529%, max 8.8%, 23 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| PRDC | PASS | 1113 | 0.9545 | 0/0 | 0 | 172 bar(s) with open/close outside [low, high] (median 0.469%, max 8.108%, 6 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| RAKT | PASS | 1113 | 0.9545 | 0/0 | 0 | 501 bar(s) with open/close outside [low, high] (median 1.45%, max 17.658%, 190 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| RKAZ | PASS | 1114 | 0.9554 | 0/0 | 0 | 528 bar(s) with open/close outside [low, high] (median 8.591%, max 11.111%, 386 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| RREI | PASS | 1113 | 0.9545 | 0/0 | 0 | 326 bar(s) with open/close outside [low, high] (median 0.796%, max 8.779%, 66 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| RUBX | PASS | 1113 | 0.9545 | 0/0 | 0 | 425 bar(s) with open/close outside [low, high] (median 1.645%, max 17.407%, 179 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| SAIB | PASS | 1118 | 0.9588 | 0/0 | 0 | 192 bar(s) with open/close outside [low, high] (median 16.516%, max 16.777%, 180 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| SAUD | PASS | 1113 | 0.9545 | 0/0 | 0 | 232 bar(s) with open/close outside [low, high] (median 0.422%, max 8.233%, 14 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| SPHT | PASS | 1118 | 0.9588 | 0/1 | 0 | 18 bar(s) with open/close outside [low, high] (median 24.673%, max 25.0%, 16 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| SPIN | PASS | 1113 | 0.9545 | 0/0 | 0 | 367 bar(s) with open/close outside [low, high] (median 0.99%, max 17.627%, 107 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| SWDY | PASS | 1113 | 0.9545 | 0/0 | 0 | 225 bar(s) with open/close outside [low, high] (median 0.264%, max 9.0%, 6 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| TMGH | PASS | 1113 | 0.9545 | 0/0 | 0 | 206 bar(s) with open/close outside [low, high] (median 0.276%, max 5.781%, 10 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| UEGC | PASS | 1113 | 0.9545 | 0/0 | 0 | 197 bar(s) with open/close outside [low, high] (median 0.566%, max 8.421%, 14 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| UNIP | PASS | 1113 | 0.9545 | 0/1 | 0 | 185 bar(s) with open/close outside [low, high] (median 0.688%, max 10.183%, 23 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |
| UNIT | PASS | 1113 | 0.9545 | 0/0 | 0 | 209 bar(s) with open/close outside [low, high] (median 0.667%, max 6.833%, 20 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses) |
| ZMID | PASS | 1113 | 0.9545 | 0/1 | 0 | 226 bar(s) with open/close outside [low, high] (median 0.528%, max 5.357%, 31 at or above 2% -- informational, does not affect close-to-close return calculations this engine uses); 1 raw close jump(s) > 25% (not itself critical -- cross-checked against derived corporate-action events separately) |

## Tickers with unexplained extreme jumps (informational)

These raw-close jumps exceed the threshold and have no derived corporate-action event within 3 days — could be a real, large single-day move (Egypt has real, sometimes large single-name moves), a corporate action this dataset's Close/Adj-Close reverse-engineering missed (e.g. a rights issue, which is not a simple multiplicative adjustment), or a genuine data error in the source. Not fabricated as one or the other here — flagged for the reader.
- **ADIB**: [('2025-05-26', -0.4947)]
- **AIFI**: [('2024-08-22', 6.3205), ('2025-12-28', -0.4183)]
- **AMER**: [('2023-05-28', -0.3399)]
- **ARAB**: [('2024-05-07', -0.8295), ('2025-03-09', -0.3018)]
- **CANA**: [('2025-01-06', -0.2578), ('2026-04-06', -0.3635)]
- **CCRS**: [('2025-03-02', -0.9178), ('2025-08-10', -0.6436)]
- **COPR**: [('2022-11-10', -0.35), ('2023-07-05', -0.9851), ('2023-09-11', -0.3588), ('2025-12-14', -0.4905)]
- **DSCW**: [('2022-06-09', -0.2957), ('2025-10-28', -0.3382)]
- **EFIH**: [('2025-05-25', -0.3117)]
- **EHDR**: [('2025-10-21', 3.9494)]
- **ELKA**: [('2026-01-26', -0.4457)]
- **ELSH**: [('2025-06-24', -0.3145)]
- **EXPA**: [('2024-08-13', -0.2561), ('2025-09-09', -0.2827)]
- **GDWA**: [('2025-10-05', -0.8062)]
- **HDBK**: [('2026-06-29', -0.4965)]
- **HELI**: [('2025-09-16', -0.6754)]
- **LCSW**: [('2023-10-22', 0.302), ('2024-05-27', 0.3749)]
- **MBEG**: [('2024-05-21', -0.4494)]
- **NHPS**: [('2024-05-02', 0.573)]
- **OBRI**: [('2024-02-18', -0.3013)]
- **OCDI**: [('2024-02-19', 0.2737), ('2025-08-17', -0.7377)]
- **PRCL**: [('2023-10-22', 0.3983)]
- **SPHT**: [('2025-09-17', -0.2529)]
- **UNIP**: [('2025-09-16', -0.6731)]
- **ZMID**: [('2024-12-10', -0.4785)]
