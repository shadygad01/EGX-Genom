# Financial Coverage Completion Mission

Started: 2026-08-04 (Africa/Cairo). Status: **IN PROGRESS**.

## Definition of done

Every one of the 101 EGX30+EGX70 tickers has either:

1. A verified financial dataset (real `ANNUAL`/`QUARTERLY` `FinancialStatementLineItem`
   rows, sourced from an `IMPLEMENTED` `SourceSpec`, traceable to a real fetch — never
   estimated, interpolated, or inferred, per `docs/TRUTH_PRESERVATION_POLICY.md`/AD-60), or
2. Documented evidence, in this file, of why no free and legal extractable financial
   source currently exists for it.

"Verified financial dataset" is measured the same way `financials.coverage
.build_financial_coverage_report()` already measures it: a ticker counts once its
latest reported period (`ANNUAL` or `QUARTERLY`) has at least one real line item.
A current-price/ratio snapshot (`period_type="SNAPSHOT"`) does not count — it is not
a financial statement.

This document is a living tracker, not a one-time report: it is updated every time new
evidence lands (a live production run, a live discovery sprint), never rewritten
speculatively ahead of that evidence.

## Baseline (verified 2026-08-03, production run `30844985214` on `main`)

**8/101 tickers = 7.92%** have a real financial-statement dataset today:

| Ticker | Source | Rows (ANNUAL/QUARTERLY) | Latest period |
|---|---|---:|---|
| ETEL | `telecom_egypt_ir` | 143 | 2026-03-31 |
| ARCC | `chief_egx_financials` | 126 | 2025-12-31 |
| COMI | `chief_egx_financials` | 108 | 2025-12-31 |
| CIEB | `chief_egx_financials` | 92 | 2024-12-31 |
| EXPA | `chief_egx_financials` | 92 | 2025-12-31 |
| RMDA | `rmda_ir` | 6 | 2026-03-31 |
| TMGH | `tmgh_ir` | 4 | 2026-03-31 |
| ORAS | `orascom_ir` | 3 | 2026-03-31 |

`egxpilot_fundamentals` reaches 100/101 tickers but only ever writes
`period_type="SNAPSHOT"` rows (current market P/E, EPS, revenue — trailing ratios, not
statement line items with a real reporting period). Confirmed by reading its collector
(`research/src/agx_research/collectors/egxpilot_fundamentals.py`): the API it calls has
no historical-statement endpoint, only a current snapshot and OHLCV price history. This
is not a bug and not a coverage lever — it is correctly excluded.

## Sources ruled out for the whole market (apply to every currently-uncovered ticker equally)

Established by `docs/ACQUISITION_STRATEGY.md` (live-evidenced, not assumed) and this
mission's own audit — these are not per-ticker gaps, they are structural blocks that
apply market-wide until a business/legal action changes them:

| Source | Status | Why it can't close any gap right now |
|---|---|---|
| `egx_official` (egx.com.eg bulk disclosure/financials) | `DISABLED` | TCP connection actively reset; network-level anti-bot, reconfirmed every session. Not an engineering-closable gap. |
| `egid_financial_filings` (official issuer-filings API, up to 6 years per issuer) | `TOS_REVIEW` / `BLOCKED` | Live audit found the backend accepts any ISIN with a company-scoped JWT, but automating that would rely on a tenant-authorization gap, not a documented bulk-access grant. Explicitly gated on EGID confirming a market-wide credential — a business/legal action, not code. **This is the single highest-potential lever in the whole mission if cleared** (claims "up to six years of issuer financial-statement attachments" per company, i.e. potentially near-universal coverage) — flagged for the project owner, not something engineering can unblock alone. |
| Aggregator display pages (Investing.com, TradingView, MarketScreener, Mubasher, Zawya) | Blocked | robots.txt disallow and/or explicit ToS prohibition on automated collection, confirmed by fetching the actual ToS text, not assumed. |
| Financial aggregator APIs (AlphaVantage, FMP, Twelve Data, EODHD) | Business-blocked | `NEEDS_KEY` — a paid/registration credential is a business decision reserved for the project owner per this program's existing "never fabricate or bypass a credential" rule, and the project owner has already decided (see `docs/ACQUISITION_STRATEGY.md`'s "no-API-key sources decision") to rely exclusively on genuinely free, no-registration sources. |

None of the above are "documented no free source exists" closures for a specific
ticker under this mission's Definition of Done — they are the reason *broad* sources
can't help, which is why this mission's real lever is **per-company** sources
(`company_ir`, `chief_egx_financials`-style discovery).

## Per-company discovery: in progress

`company_ir` (per-constituent IR pages) is `PLANNED` — code-complete
(`collectors/company_earnings_table.py`'s `CompanyEarningsTablePdfCollector`, already
proven live for RMDA/TMGH; `collectors/financial_statements.py`'s
`FinancialStatementCollector` for CSV/XLSX exports) but genuinely unverified per
company until a real fetch confirms a real endpoint — per this program's absolute rule
that "every endpoint must be verified before a `SourceSpec` becomes `IMPLEMENTED`,"
inventing one here would be exactly the kind of fabrication AD-60 forbids.

`discovery.web_search_hints` already carries live-web-search-gathered (not
training-data-recalled) domain hints for **26/31 EGX30 tickers** (TD-38); 5 EGX30
tickers (`EGCH`, `HELI`, `MCQE`, `OIH`, `PHDC`) have no confident hint yet; EGX70 is
unattempted. `.github/workflows/discover-sources.yml` — a manual, read-only,
`workflow_dispatch`-only sprint that runs the full Acquisition Intelligence Engine
catalog (every org target + every EGX30/EGX70 `company_ir` target) against real network
egress, and never writes to the repo (promoting a verified result stays a separate,
reviewed, human commit) — was triggered for this mission:

- Run: `https://github.com/shadygad01/EGX-Genom/actions/runs/30879320221`
- Triggered: 2026-08-04 05:00 UTC, full catalog (no `target` filter)
- Status as of this writing: **in progress** (can take well over an hour per its own
  documentation, due to per-source rate limiting across ~100 targets)

This document will be updated with real results once that run completes — verified
candidates promoted to `IMPLEMENTED` `SourceSpec`s (each a separate, reviewed commit
per source, matching the existing precedent for `telecom_egypt_ir`/`orascom_ir`/
`tmgh_ir`/`rmda_ir`), and any target that comes back genuinely dead-ended documented
below as a real "no free source" closure — never guessed ahead of that evidence.

## Full 101-ticker status

Legend: **COVERED** = real ANNUAL/QUARTERLY dataset exists today. **PENDING** = no
dataset yet, and the live discovery sprint above has not yet reported on this ticker's
`company_ir` candidate — not yet eligible to be called "no free source exists."
**NO-HINT** = also has no domain hint at all yet (TD-38), so even the pending sprint
has nothing to test for it without a domain first.

### EGX30 (31 tickers)

| Ticker | Company | Status |
|---|---|---|
| ABUK | Abou Kir Fertilizers | PENDING |
| ADIB | Abu Dhabi Islamic Bank-Egypt | PENDING |
| AMOC | Alexandria Mineral Oils Company | PENDING |
| ARCC | Arabian Cement Company | **COVERED** (`chief_egx_financials`) |
| BTFH | Beltone Holding | PENDING |
| CCAP | QALAA For Financial Investments | PENDING |
| COMI | Commercial International Bank-Egypt | **COVERED** (`chief_egx_financials`) |
| EAST | Eastern Company | PENDING |
| EFID | Edita Food Industries S.A.E | PENDING |
| EFIH | E-finance For Digital and Financial Investments | PENDING |
| EGAL | Egypt Aluminum | PENDING |
| EGCH | Egyptian Chemical Industries (Kima) | NO-HINT |
| EMFD | Emaar Misr for Development | PENDING |
| ETEL | Telecom Egypt | **COVERED** (`telecom_egypt_ir`) |
| FWRY | Fawry For Banking Technology And Electronic Payment | PENDING |
| GBCO | GB Corp | PENDING |
| HELI | Heliopolis Housing | NO-HINT |
| HRHO | EFG Holding | PENDING |
| ISPH | Ibnsina Pharma | PENDING |
| JUFO | Juhayna Food Industries | PENDING |
| MCQE | Misr Cement (Qena) | NO-HINT |
| OIH | Orascom Investment Holding | NO-HINT |
| ORAS | Orascom Construction PLC | **COVERED** (`orascom_ir`) |
| ORHD | Orascom Development Egypt | PENDING |
| ORWE | Oriental Weavers | PENDING |
| PHDC | Palm Hills Development Company | NO-HINT |
| RAYA | Raya Holding For Financial Investments | PENDING |
| RMDA | Tenth Of Ramadan Pharmaceutical Industries&Diagnostic-Rameda | **COVERED** (`rmda_ir`) |
| TMGH | T M G Holding | **COVERED** (`tmgh_ir`) |
| VLMR | Valmore Holding | PENDING |
| VLMRA | Valmore Holding-EGP | PENDING |

### EGX70 (70 tickers)

All EGX70 tickers are **PENDING** (no domain-hint snapshot exists yet for EGX70 at
all — TD-38 covers EGX30 only), except:

- **CIEB** (Credit Agricole Egypt) — **COVERED** (`chief_egx_financials`)
- **EXPA** (Export Development Bank of Egypt) — **COVERED** (`chief_egx_financials`)
- **AIDC** (Arabia for Investment and Development) — the sole ticker with **zero**
  source data of any kind (not even a `SNAPSHOT` row) — `egxpilot_fundamentals`'s own
  notes explicitly record "the all-stocks endpoint matched 100/101 AGX securities...
  AIDC was absent." Highest-priority individual target once the discovery sprint's
  `company_ir` results land.

Remaining 67 PENDING EGX70 tickers (naming preserved from `EGX70.csv`): ACTF, AFDI,
AFMC, AIHC, ALCN, AMER, AMIA, ARAB, ASCM, ASPI, ATLC, ATQA, BIOC, CNFN, COSG, CSAG,
DAPH, DSCW, ECAP, EGTS, EHDR, ELSH, ENGC, ETRS, GPIM, HDBK, ICFC, IDRE, IEEC, IFAP,
ISMA, ISMQ, KABO, KRDI, LCSW, MASR, MCRO, MEPA, MFPC, MOED, MPCI, MPCO, MPRC, MTIE,
NCCW, NIPH, OBRI, OCDI, OFH, PHAR, POUL, PRCL, RACC, SCEM, SDTI, SIPC, SKPC, SVCE,
SWDY, TALM, TANM, TAQA, UEGC, UNIP, VALU, ZEOT, ZMID.

## Naming-pattern observations (unverified, not a coverage claim)

A few tickers share a name fragment suggesting a possible group relationship —
**observation only, not a verified `PARENT_COMPANY` claim** (that `ClaimAttribute` enum
member, `discovery/resolution_memory.py`, is currently defined but has zero populated
claims anywhere in this codebase):

- "Orascom": ORAS (covered), ORHD, OIH — three distinct listed entities.
- "Raya": RAYA, RACC.
- "Arabia": AIDC (zero coverage), AIHC.
- Valmore: VLMR/VLMRA are two share classes of the *same* issuer, not a parent/subsidiary pair.

None of these are usable as a coverage shortcut on their own — each is a separately
listed issuer that reports its own financial statements; a shared name is a discovery
hint at best (worth a search-domain-hint pass), never a substitute for that ticker's
own verified data.

## Next update

Triggered by: `discover-sources.yml` run `30879320221` completing. Will record, per
target attempted: verified/promotable candidate, or the specific real failure reason
(network block, robots.txt disallow, ToS restriction, no discoverable feed) as the
Definition of Done's "documented evidence" closure for that ticker.
