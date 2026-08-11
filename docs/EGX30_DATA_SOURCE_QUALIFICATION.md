# EGX30 Data Source Qualification

Mission 2 ("Data Unlock + Scientific Hardening"), Phase 1. Every source
below was **actually tested** from this development sandbox — a bare
`curl`/`WebFetch`/`git clone` attempt, not a marketing claim taken on
faith. "Usable" means a real retrieval succeeded and the retrieved
content was inspected; nothing here is qualified on reachability claims
alone.

## The decisive environment fact

This sandbox's outbound network policy is a strict allowlist. Every
general-internet host tested below — including `fred.stlouisfed.org`,
which this codebase's own `sources/catalog.py` already lists as
`IMPLEMENTED` and which a *prior* session's committed macro CSVs
(`research/data/macro/{BRENT_USD,EGP_USD}.csv`) prove was reachable from
*some* environment — returns `403`/"CONNECT tunnel failed" from *this*
session. `WebFetch` goes through the same proxy and is equally blocked
(confirmed against `en.wikipedia.org`, a domain with essentially no
reason to be specifically blocklisted, meaning this is a general
allowlist policy, not a finance-specific one).

Two exceptions, both re-confirmed today with real requests:

- `raw.githubusercontent.com` / `objects.githubusercontent.com` —
  genuinely open, **for any public repository**, no attachment needed
  (verified against `torvalds/linux`, a repo with no relationship to this
  session).
- Anonymous `git clone`/`fetch` of any public GitHub repository — served
  directly by this session's git proxy (confirmed via the `add_repo`
  tool's own response: "this session's git proxy serves anonymous git
  reads (clone/fetch) of public GitHub repositories directly").
- `api.github.com`/`codeload.github.com` are network-reachable but
  content-gated to repositories explicitly attached via `add_repo`.

This single fact is why every source below that lives on a vendor's own
website is `BLOCKED (environment)`, while a real dataset that happens to
be hosted inside a public GitHub repository is reachable. It is an
environment constraint, not a claim about what exists on the public
internet — a session with normal web egress would see a different table
for the vendor-hosted rows.

## Reachability test log (raw evidence)

| Host | Result | Method |
|---|---|---|
| `query1.finance.yahoo.com`, `query2.finance.yahoo.com` | `403` CONNECT tunnel failed | `curl` |
| `stooq.com` | `403` | `curl` + `WebFetch` |
| `egx.com.eg` | `403` | `curl` |
| `www.investing.com` | `403` | `curl` |
| `www.mubasher.info`, `english.mubasher.info` | `403` | `curl` |
| `africanmarkets.com`, `www.african-markets.com` | `403` | `curl` |
| `kaggle.com`, `www.kaggle.com` | `403` | `curl` |
| `data.mendeley.com` | `403` | `curl` |
| `huggingface.co`, `datasets-server.huggingface.co` | `403` | `curl` |
| `fred.stlouisfed.org` | `403` | `curl` |
| `api.worldbank.org`, `data.worldbank.org` | `403` | `curl` |
| `archive.org`, `web.archive.org` | `403` | `curl` |
| `egidegypt.com`, `egid.egyptse.com` | `403` | `curl` |
| `leviathan-uchb.onrender.com` (community EGX quote API) | `403` | `curl` |
| `en.wikipedia.org` | `EGRESS_BLOCKED` | `WebFetch` |
| `raw.githubusercontent.com` | `200`, real content returned | `curl` (torvalds/linux and a second unrelated public repo) |
| `objects.githubusercontent.com` | `404` (server reached, not proxy-blocked) | `curl` |
| `api.github.com` | `200` for the base host; `repos/*`/`search/*` return a structured "attach with add_repo" message for unattached repos | `curl` |
| `codeload.github.com` (repo tarball download) | Network-reachable; content gated the same way as `api.github.com` | `curl` |
| Anonymous `git clone` of a public repo | **Succeeds**, real content, no `add_repo` needed for read | `git clone --depth 1` |

`WebSearch` (a separate, server-side tool, not subject to this sandbox's
egress proxy) works throughout and was the actual discovery mechanism for
every candidate below.

## Source qualification table

| Source | Dataset | Years | Tickers | OHLC | Volume | Corporate Actions | Historical Universe | Free | Repeatable | Status | Evidence |
|---|---|---:|---:|---|---|---|---|---|---|---|---|
| `github.com/abdulrahman-mahmoud/egxstock-analysis` (`data/egx.sqlite3`, `raw_prices` table) | EGX daily OHLCV, per-ticker sector tag | 2022-01-02 → 2026-08-06 (~4.6 yrs) | 78 distinct (75 usable at a ≥250-observation floor; 3 excluded as newly-listed, <15 obs each) | Yes (raw, unadjusted) | Yes | No explicit event records — **reverse-engineered** from the source's own `Close`/`Adj Close` divergence (128 derived events across 75 tickers) | No (current-only; see below) | Yes (MIT license) | Yes (public repo, anonymous `git clone`) | **QUALIFIED — primary price source** | Cloned at commit `555fb77e290738f3ff97dd4db65791457ec1e90c`, real SQL queries run directly against the database (0 duplicate (Symbol,Date) pairs; 0 `High<Low`; 0 non-positive prices; 0 negative volume; 100% of 83,540 raw rows land on Sun-Thu after the +1-day Cairo-timezone correction, 0% before). Full detail: `docs/EGX30_DATA_QUALITY_REPORT.md`. |
| `github.com/abdulrahman-mahmoud/egxstock-analysis` (`company_snapshot`/`raw_prices.Sector` columns) | Sector classification | current, plus historical per-row (unchanged per ticker in this dataset) | 78 (271 in `company_snapshot`, broader than price coverage) | — | — | — | — | Yes | Yes | **QUALIFIED — closes the sector-coverage gap** `docs/PATTERN_DISCOVERY_DATA_AUDIT.md` flagged (10/30 EGX30 via the old placeholder) | Every one of the 78 priced tickers has exactly one consistent sector value across its full history (checked: 0 tickers with >1 distinct value). |
| Yahoo Finance (`query1/2.finance.yahoo.com`, this platform's own `egx_price_composite` collector) | EGX daily OHLCV, real-time deep history (`range=max`) | Potentially the deepest available | Any EGX ticker | Yes | Yes | Real (Yahoo's `events.dividends/splits`) | No | Yes | Yes, from an environment with egress | **BLOCKED (environment)** | `403` — see reachability log. Code is real and `IMPLEMENTED` (Mission 1); simply cannot run from this sandbox. |
| Stooq (`stooq.com`, this platform's own `StooqPriceCollector`) | EGX daily OHLCV | Varies | EGX-listed | Yes | Yes | No | No | Free for personal use | Robots.txt already confirmed (Mission 1) to disallow the CSV-download path even with egress | **BLOCKED (environment + ToS)** | `403` here; Mission 1 already found robots.txt disallows the mechanism regardless. |
| EGX official (`egx.com.eg`) | Official index/market-activity historical statistics, current constituents | Official archive, depth unknown | All EGX-listed | Unknown (not reached) | Unknown | Unknown | Current constituents confirmed available (already the source of `research/data/universe/EGX30.csv`/`EGX70.csv`'s single snapshot) | Yes (public site) | Yes, from an environment with egress | **BLOCKED (environment)** | `403`. This is the platform's own eventual target `SourceStatus.PLANNED` (`egx_official`) — unaffected qualification-wise by this mission. |
| Investing.com | EGX30 index + constituent historical data | Deep (site claims years) | EGX30 + broader | Yes (claimed) | Yes (claimed) | Unknown | Unknown | Free with signup for full history (claimed) | Unknown | **BLOCKED (environment)** | `403`. Never actually retrieved; qualification is reachability-only, not content-verified. |
| Kaggle (`Egyptian-Stock-Exchange-EGX30`, several dataset listings found via search) | EGX historical OHLCV | Unknown (not opened) | Unknown | Unknown | Unknown | Unknown | Unknown | Free (Kaggle account required) | Unknown | **BLOCKED (environment)** | `403` to `kaggle.com`; the Kaggle API/CDN was not independently reachable either (no bucket path known to test `storage.googleapis.com` against). |
| World Bank / FRED (macro, already `IMPLEMENTED`, already committed as real data in `research/data/macro/`) | FX, oil, CPI, GDP, interest rate | ~13 months daily (FRED) / ~10-13 annual points (World Bank) | n/a (macro) | n/a | n/a | n/a | n/a | Yes | Yes, from an environment with egress; **not** from this one | **ALREADY COLLECTED (prior session), BLOCKED for a fresh pull (this session)** | `403` to both `fred.stlouisfed.org` and `api.worldbank.org` today — the committed CSVs prove a *different* session had egress; this one doesn't. No new macro data acquired this mission. |
| Mubasher (`mubasher.info`) | Live quote snapshot (not deep history) | n/a | EGX-listed | Snapshot only | Snapshot only | No | No | Yes | Yes, from an environment with egress | **BLOCKED (environment)**, and not deep-history-capable regardless | `403`. Already a `DISABLED`/fallback-only leg of `egx_price_composite` in Mission 1's audit — low priority even if reachable. |
| `leviathan-uchb.onrender.com` (community EGX quote API, found via `github.com/TheAhmedRmdan/leviathan-docs`) | Live current price snapshot only (`{"stockPrice": 79.89, "date": ...}`) | n/a — no historical endpoint documented | EGX-listed | No | No | No | No | Free, unauthenticated | Unclear (small hobby API, no SLA) | **REJECTED — not historical** | `403` to the live host, and its own documented API shape (inspected via the repo's real `README.md` over `raw.githubusercontent.com`) only ever returns today's price, not history, so it would not qualify even with egress. |
| `github.com/HussienElSawy/EGX.com-Scanner` | Scraper *tool* (generates CSVs on run) | n/a | n/a | n/a | n/a | n/a | n/a | MIT-style, tool only | n/a | **REJECTED — no committed data** | Real `README.md` fetched via `raw.githubusercontent.com`; confirms `outputs/` is generated locally when the tool runs, not committed to the repo. No `.gitignore` was found either, but no data files exist at the repo's default branch tip. |
| GitHub search for a dedicated EGX30 index-level historical CSV, historical index-reconstitution announcement list, or a free structured EGX corporate-actions/financial-statements dataset | — | — | — | — | — | — | — | — | — | **NOT FOUND** | Multiple `WebSearch` queries (see this mission's own search history) returned only vendor-hosted pages (Investing.com, EGX official, TradingView, S&P/LSEG/Morningstar reconstitution announcements for *other* indices) — none reachable, and none EGX-specific for reconstitution history. Real, honestly-reported absence, not a stopping point papered over. |

## Category-by-category summary

1. **EGX historical OHLCV** — Qualified: the community SQLite dataset (75 usable tickers, ~4.6 years). Real EGX30/official-vendor sources exist but are environment-blocked.
2. **EGX30 historical constituents** — **Not found anywhere free/public and reachable.** EGX itself confirms semi-annual reviews (real, sourced from a live EnterpriseAM Egypt article found via `WebSearch`) but no historical reconstitution list was located. See Phase 3's honest handling of this gap.
3. **Corporate actions** — No dedicated real corporate-action dataset found; the community price dataset's own `Close`/`Adj Close` divergence is reverse-engineered into derived events instead (real, verified, but not independently confirmed as to economic nature — see `docs/EGX30_DATA_QUALITY_REPORT.md`).
4. **Sector classifications** — Qualified from the same community dataset; closes a real gap Mission 1 flagged.
5. **EGX30 index history** — Not found as a downloadable series; this platform (both before and after this mission) computes an equal-weighted basket proxy from constituent returns instead (`market_memory.regime`/`breadth`, `patterns.targets._market_forward_returns`) rather than fabricate or fetch an index series that isn't obtainable.
6. **EGX70/broader index history** — Same conclusion as #5; the community dataset's 78 tickers span both EGX30 and EGX70 names (38 of the real EGX30∪EGX70 union of 101 tickers).
7. **Macro data** — Already real and committed from a prior session (FRED/World Bank); not re-fetchable from this session, but nothing new needed since the existing CSVs remain valid, static, dated evidence.
8. **Company financial statements** — Still none found free/public and reachable; unchanged from Mission 1's finding, and a large, separate, already-tracked effort in this repository (`docs/FINANCIAL_COVERAGE_COMPLETION_MISSION_2026-08-04.md`) — out of this mission's scope to re-solve.
9. **Material corporate disclosures** — Not investigated further this mission (same environment blockers as #8 would apply to any IR/disclosure source); unchanged from Mission 1.

## What changed vs. Mission 1's conclusion

Mission 1 concluded no real, sufficiently deep EGX price data existed
anywhere in this repository or session-reachable. That conclusion is
**superseded for OHLCV and sector data** by the qualified community
dataset above — found via `WebSearch` (server-side, not egress-blocked)
and retrieved via anonymous `git clone` (also not egress-blocked), a
combination Mission 1 did not attempt. It remains **true and unchanged**
for historical universe membership, corporate-action ground truth, an
EGX30/EGX70 index-level series, financial statements, and material
disclosures — this mission looked, with real tests, and did not find
free/reachable sources for any of those five.
