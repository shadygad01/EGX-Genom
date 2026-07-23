# Completion Report — Financial Statement Collection

## Mission

The project owner handed over full engineering ownership: no more
isolated tasks, continue autonomously through the entire remaining
backlog until a genuine blocker is hit, in this refined business-priority
order: (1) EGX official, (2) Universe Engine, (3) Investor Relations
discovery, (4) Corporate disclosures, (5) Financial statement collection,
(6) Historical backfill, (7) Live incremental synchronization, (8–15) CBE/
FRA/CAPMAS/Enterprise/Mubasher/Zawya/Reuters/Trading Economics, (16)
anything else discovered automatically. This report covers priority 5,
delivered directly after priorities 2–4 (see this repository's git
history / earlier `CHANGELOG.md` entries for that report).

## Delivered

| Module | Delivers |
|---|---|
| `financials/schema.py` | `FinancialStatementLineItem` — `{ticker, period_end_date, period_type, statement_type, line_item, value, currency}`; `STANDARD_LINE_ITEMS`, a small IFRS/GAAP-style vocabulary, reused where possible but never hard-enforced. |
| `financials/provider.py`, `financials/collected.py` | `FinancialStatementProvider` (new, small ABC — mirrors `universe.UniverseProvider` rather than growing `data.provider.DataProvider`'s method set) + `CollectedFinancialStatementProvider` (reads collected data, empty when nothing collected). |
| `collectors/base.py`, `collectors/service.py`, `collectors/quality.py` | `CollectionBatch` gained `financial_statement_line_items`; `CollectionService` materializes to `financial_statements/<TICKER>.csv` (merged by `period_end_date,statement_type,line_item`), provenance-traced, matching the existing writer pattern exactly. |
| `collectors/financial_statements.py` | `FinancialStatementCollector` — generic header-matching CSV parser for a structured financial-statement export; built and tested, not yet wireable (endpoint unverified). |

## The gap this closed

`agents.financial_performance.FinancialPerformanceAgent` has been an
honest `NotImplementedError` stub since System 08 was built (see
`docs/PHASE_STATUS.md`'s System 08 entry: "News/FinancialPerformance/
HistoricalPatterns are honest stubs, all data-blocked... fundamentals
feed"), explicitly documented as needing "a financial statement data
source and a defined fundamental factor set." This phase built the data
source — the acquisition-side infrastructure a real financial-statement
feed needs to reach the platform at all. The agent's own fundamental-
factor logic (relating margins/ROE/leverage/earnings growth to forward
returns) remains separate, later Scientist Framework work, deliberately
not attempted here — this milestone was scoped to priority 5 (data
acquisition), not System 08 (research agent implementation).

## Verification

- 475 Python tests (up from 462), 13 new. Covers: `FinancialStatementCollector`'s
  column detection (order-independent across all five required columns,
  optional sixth currency column, warns rather than guesses on
  ambiguous/malformed/missing-column input, never silently drops an
  unparseable row); `CollectedFinancialStatementProvider`'s date-range
  filtering, `statement_type` filtering, sorted output, empty-when-
  nothing-collected and empty-when-out-of-range behavior, default currency
  handling; `CollectionService`'s materialization and idempotent
  re-ingestion of the new record type with correct provenance keys.
- `ruff check` clean; `contracts/` unchanged (`FinancialStatementLineItem`
  isn't API-facing).

## What did not change, deliberately

- No change to `data.provider.DataProvider`'s abstract method set —
  `FinancialStatementProvider` is a new, small, dedicated interface
  instead, matching the precedent `universe.UniverseProvider`/
  `SectorProvider` already set (one clean interface per concern, not
  growing a completed, tested interface every implementation depends on).
- No generic PDF-based financial-statement extractor. `sources.catalog`'s
  own `company_ir` notes expect PDF/XBRL disclosures to be the more common
  real case, but a generic numeric-extraction heuristic over arbitrary
  filing layouts risks silently reading the *wrong* line item's value —
  materially worse than a missing column, and the exact reason
  `collectors.pdf.PdfDocumentCollector.parse()` already stays abstract for
  every other PDF source (new debt, TD-32; new risk, R-21).
- No wiring of `FinancialStatementProvider` into `MarketMemory`/
  `DatasetSnapshot`. `FinancialPerformanceAgent`'s implementation would be
  the natural trigger for that additive change (matching how
  `UniverseProvider`/`SectorProvider` are already composed into
  `MarketMemory`'s constructor) — doing it now, ahead of a defined
  consumer, would extend a completed system (Market Memory) speculatively.
- `company_ir`'s `SourceSpec` stays `PLANNED` — not flipped to
  `IMPLEMENTED` to make the new collector "usable," since that would
  misrepresent verification that hasn't happened.

## Genuine blockers — unchanged, named again for this phase

1. **No outbound network egress** from this sandbox (confirmed directly
   and repeatedly across four missions now) — blocks verifying
   `company_ir`'s/`egx_official`'s real endpoints, which blocks
   `FinancialStatementCollector`/`IndexConstituentCollector` ever running
   live, which blocks priorities 1, 2/3/4/5 at real scale, and 8–16.
2. **No verified, complete EGX30/EGX70 constituent list** exists in this
   codebase — a business decision reserved for the project owner;
   fabricating one from training-data recall would violate the platform's
   anti-fabrication principle.

Everything engineering could complete without either input has been
completed across priorities 2–7 of this mission (Universe Engine,
Investor Relations discovery confirmed already scaled, Corporate
Disclosures, Financial Statement Collection, Historical Backfill and Live
Incremental Sync confirmed already satisfied). See `NEXT_MISSIONS.md` for
what remains genuinely engineering-closeable in the meantime (richer
PDF-based extraction once a real layout exists, cross-source
corroboration once a second overlapping source exists, calibration passes
once real data exists) and what runs automatically the moment either named
blocker clears.
