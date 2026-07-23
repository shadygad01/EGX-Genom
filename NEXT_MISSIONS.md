# Next Missions

In priority order (business value, per the project owner's explicit
ordering — not engineering convenience). See `docs/ROADMAP.md` for full
detail and `docs/PHASE_STATUS.md` for what's already closed.

## 1. Financial Statement Collection (priority 5) — next up, no blocker

The next engineering-closeable milestone, needing no live source to design:
a canonical schema for structured financial-statement line items (income
statement, balance sheet, cash flow), a generic collector shape (mirroring
`IndexConstituentCollector`'s header-matching, format-tolerant posture —
never guessing a specific vendor's real layout before one is verified),
and a `DataProvider`-consistent read path. Same "generic infrastructure
now, wire-format-pending-verification" pattern this phase used for the
Universe Engine and corporate events.

## 2. Clear the blocker: network egress or a verified company list

Two independent unblocks, either one lets real connection work resume for
priority 1 (EGX official) and everything gated on it:

- **Run somewhere with outbound network egress** (a deployment, or a
  differently-configured sandbox). The moment this happens,
  `agx discover-sources` performs real, verified discovery for the entire
  catalog below with no code changes, and `IndexConstituentCollector` can
  be pointed at `egx_official`'s real endpoint once verified.
- **Project owner supplies a verified EGX30/EGX70 constituent list**
  (tickers + names) and/or per-company IR domains. This is explicitly a
  business decision, not something engineering should fabricate from
  training-data recall (see `CURRENT_MISSION.md`'s honesty note). Either
  input slots directly into `generate_company_ir_targets(companies, ...)`
  and/or `universe.StaticUniverseProvider`'s constructor.

## What runs automatically the moment either clears

No further engineering is required for this — `agx discover-sources`
already processes the complete priority-ordered catalog end to end
(resolve → discover → verify legality/stability/historical-availability →
rank → select → auto-generate `SourceSpec` → register → begin
qualification) for:

- EGX official (priority 1)
- CBE, FRA, CAPMAS, Enterprise, Mubasher, Zawya, Reuters, Trading
  Economics (priorities 8–15)
- Anything else the engine finds on its own (priority 16)

Priorities 2/3 (EGX30/EGX70 company Investor Relations) scale automatically
too, for whichever companies exist in the universe at the time
(`generate_company_ir_targets`) — currently the 10-company EGX30
placeholder, expanding with zero code changes once the Universe Engine's
`IndexConstituentCollector` (or a user-supplied list) provides a real one.

## 3. Once a source resolves: write and test its concrete collector

Every `SourceSpec` `agx discover-sources` registers stays `PLANNED` by
design (`AD-24`) until an engineer writes and tests the concrete collector
its `collector` field suggests (`RssNewsCollector` for RSS,
`ExcelSeriesCollector`/`PdfDocumentCollector` for structured/PDF sources,
`IndexConstituentCollector` for `egx_official`'s constituent list once its
real endpoint is verified). Wire it into `production/collector_plan.py`
(extending its existing mock/replay seam, `AD-28`) and flip `status` to
`IMPLEMENTED`.

## 4. Historical backfill / 5. Live incremental sync — already automatic

Priorities 6/7 in the mission's list needed no new engineering this phase
and need none going forward: every collector (`StooqPriceCollector`,
`FredCsvCollector`, `WorldBankCollector`, `RssNewsCollector`,
`IndexConstituentCollector`) fetches a source's full available series by
construction, and every materialization writer merges by natural key and
overwrites idempotently — a first real run *is* the backfill, and every
subsequent run *is* the incremental sync, through the identical production
pipeline. No separate "backfill mode" or "incremental mode" exists or is
needed.

## 6. World Bank / IMF / FRED live activation — deprioritized, not abandoned

Still valid engineering, just not the first priority per the project
owner's ordering: these are enrichment sources. Revisit after priorities
1–15 have real collectors, or opportunistically if World Bank's egress
happens to clear first (same blocker, same unblock).

## 7. Richer corporate disclosures beyond the headline classifier

TD-24 is closed (`corporate_event_classifier` + `RssNewsCollector`'s
`classify_corporate_events` flag produce real, if headline-only,
`CorporateEvent`s today). Once a company's own IR/PDF source (priority 2/3
at real scale) is real, a disclosure-PDF extraction stage would give
numeric detail (split ratios, dividend amounts) a headline never can —
follows `PdfDocumentCollector`'s existing abstract-`parse()` pattern.

## 8. Cross-source corroboration (TD-11)

Once two `IMPLEMENTED` sources overlap coverage (e.g. two independent EGX
price sources), wire real `consistency_score` in `collectors.quality.
assess_quality()`.

## 9. Calibration pass (TD-17, TD-20, TD-28, TD-29, TD-30 — new this phase)

Once real run history, real ToS-page checks, and real fetched pages exist,
revisit `qualification.py`'s promotion thresholds, `health.py`'s alert
thresholds, `legality.py`'s red/green keyword lists, the company-directory-
match token-overlap heuristic (TD-28), the corporate-event headline
classifier's keyword list (TD-29), and `IndexConstituentCollector`'s
column-header matching (TD-30) — all declared policy today.

## 10. Scheduled production pipeline + discovery runs

Wire `agx run` and `agx discover-sources` into a periodic job once any
deployment target exists (System 18) — both are deployment-ready today;
only the "run this on a schedule" wiring is deployment-shaped.

## 11. ToS reviews (business/legal decision, not engineering)

Yahoo Finance, TradingView, Investing.com, Google Trends, LinkedIn/company
social, public Telegram, Google Scholar, ResearchGate — each needs a human
legal judgment on automated-collection terms before any code changes.

## Beyond this

Per the charter's build order, no later system's work should start while
System 02 still has closeable (non-business-blocked) gaps. Items 1 and 3
above are exactly that kind of gap and take priority. Longer-horizon,
post-1.0 items (trained per-horizon models, covariance-based portfolio
optimization, remaining scientist agents/adversarial attacks, a Monte
Carlo experiment, a database-backed `Repository[T]`) are tracked in
`docs/ROADMAP.md`'s "Post-1.0" section and are not immediate next missions.
