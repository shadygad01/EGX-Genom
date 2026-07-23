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

**Financial Statement Collection (priority 5).**
`agents.financial_performance.FinancialPerformanceAgent` has been an
honest `NotImplementedError` stub since System 08 was built, explicitly
documented as needing "a financial statement data source and a defined
fundamental factor set" (`docs/PHASE_STATUS.md` System 08) — confirming
this priority closes a real, already-named architectural gap, not
speculative scope. Closed the acquisition half (the agent's own
fundamental-factor logic remains separate, later Scientist Framework
work):

- **`financials/` (new package)**: `FinancialStatementLineItem` —
  `{ticker, period_end_date, period_type, statement_type, line_item,
  value, currency}`, `STANDARD_LINE_ITEMS` (a small, well-known IFRS/GAAP
  vocabulary — revenue, net_income, total_assets, etc. — reused where
  possible but never hard-validated, so an uncommon real line item is
  preserved, not dropped). `FinancialStatementProvider` (ABC, mirroring
  `universe.UniverseProvider`'s "small dedicated interface" shape rather
  than growing `data.provider.DataProvider`'s existing method set) +
  `CollectedFinancialStatementProvider` (reads the collected CSV, empty
  when nothing's collected — never fabricated).
- **`CollectionBatch.financial_statement_line_items`** — `CollectionService`
  now writes `financial_statements/<TICKER>.csv`, merged by
  `(period_end_date, statement_type, line_item)`, with full provenance
  tracing, extending the same writer pattern used for every other record
  type.
- **`FinancialStatementCollector`** (`collectors/financial_statements.py`):
  a generic, header-matching CSV parser for a *structured* financial-
  statement export (income statement/balance sheet/cash flow, long
  format). Built and tested, not yet wireable live — `company_ir`'s
  `SourceSpec` stays `PLANNED` until its real endpoint is verified
  (`AD-24`), same honest boundary as every other unconnected collector.
- **Deliberately not built**: a generic PDF-based financial-statement
  extractor. `sources.catalog`'s own `company_ir` notes expect PDF/XBRL
  disclosures to be the more common real case, but a generic numeric
  extraction heuristic over arbitrary filing layouts risks silently
  reading the *wrong* line item's value — a materially worse failure mode
  than a missing column, and exactly why `collectors.pdf.
  PdfDocumentCollector.parse()` already stays abstract for the same
  reason. That extraction is left for a concrete, source-verified
  subclass once a real filing layout exists to build and test against
  (TD-32).

## Earlier this phase: Universe Engine + Corporate Disclosures

**Universe Engine (priority 2)** closed `universe.UniverseProvider`'s
missing collected-data path: `IndexConstituent` (point-in-time-correct
membership), `CollectedUniverseProvider`/`FallbackUniverseProvider` (wired
into `production.pipeline` and `cli.py discover-sources`), and
`IndexConstituentCollector` (built, tested, not yet wireable — same
`egx_official`-verification boundary as above).

**Corporate disclosures (priority 4), closing TD-24**: a declared headline
keyword classifier (`collectors.corporate_event_classifier`) now produces
real `CorporateEvent`s from `RssNewsCollector`'s existing content —
verified live via a mock-mode production pipeline run writing real
`COMI/EARNINGS` and `MFPC/DIVIDEND` rows.

**Investor Relations discovery (priority 3)** needed no new engineering —
already fully built two missions ago, scaling automatically once a real
universe exists.

See `COMPLETION_REPORT.md` for the full delivery report of both phases.

## Priorities 1, 6, 7: why no new code this phase either

- **Priority 1 (EGX official)**: blocked on the same two named constraints
  below.
- **Priority 6 (historical backfill) / 7 (live incremental sync)**:
  already automatic by design — every collector (including
  `FinancialStatementCollector`) fetches a source's full available series
  by construction, and every materialization writer (including the new
  financial-statement one) merges idempotently by natural key.

## The one real constraint, stated plainly (unchanged across four missions)

This sandbox has no outbound network egress to arbitrary hosts — confirmed
directly and repeatedly. Two consequences:

1. **Priority 1 (EGX official) and everything gated on it (2/3 at real
   scale, 4/5 at real scale, 8–16) cannot connect live** — every mechanism
   is built, tested, and wired; only real endpoint verification is
   missing.
2. **No real, complete EGX30/EGX70 constituent list exists in this
   codebase** — a business decision reserved for the project owner (see
   `docs/DATA_ACQUISITION.md`); fabricating one from training-data recall
   would violate the platform's anti-fabrication principle.

Everything engineering could complete without either input has been
completed across all three sub-phases of this mission (Universe Engine,
Corporate Disclosures, Financial Statement Collection). See
`NEXT_MISSIONS.md` for what runs automatically the moment either blocker
clears, and for the next genuinely unblocked items in the meantime.
