# Next Missions

In priority order (business value, per the project owner's explicit
ordering — not engineering convenience). See `docs/ROADMAP.md` for full
detail and `docs/PHASE_STATUS.md` for what's already closed.

## What runs automatically the moment either blocker below clears

No further engineering is required for this — `agx discover-sources`
already processes the complete priority-ordered catalog end to end
(resolve → discover → verify legality/stability/historical-availability →
rank → select → auto-generate `SourceSpec` → register → begin
qualification) for:

1. EGX official
4. CBE
5. FRA
6. CAPMAS
7. Enterprise
8. Mubasher
9. Zawya
10. Reuters
11. Trading Economics
12. Anything else the engine finds on its own

Priorities 2/3 (EGX30/EGX70 company Investor Relations) run automatically
too, for whichever companies exist in the universe at the time
(`generate_company_ir_targets`) — currently the 10-company EGX30
placeholder, expanding with zero code changes once a real list exists.

## 1. Clear the blocker: network egress or a verified company list

Two independent unblocks, either one lets real connection work resume:

- **Run somewhere with outbound network egress** (a deployment, or a
  differently-configured sandbox). The moment this happens,
  `agx discover-sources` performs real, verified discovery for the entire
  catalog above with no code changes.
- **Project owner supplies a verified EGX30/EGX70 constituent list**
  (tickers + names) and/or per-company IR domains. This is explicitly a
  business decision, not something engineering should fabricate from
  training-data recall (see `CURRENT_MISSION.md`'s honesty note). Either
  input slots directly into `generate_company_ir_targets(companies, ...)`
  and/or each `TargetOrganization.domain_hints`.

## 2. Once a source resolves: write and test its concrete collector

Every `SourceSpec` `agx discover-sources` registers stays `PLANNED` by
design (`AD-24`) until an engineer writes and tests the concrete collector
its `collector` field suggests (`RssNewsCollector` for RSS,
`ExcelSeriesCollector`/`PdfDocumentCollector` for structured/PDF sources).
Wire it into `production/collector_plan.py` (extending its existing
mock/replay seam, `AD-28`) and flip `status` to `IMPLEMENTED`.

## 3. Historical backfill — no new logic needed, already automatic

Per the mission's own instruction ("never build separate historical
logic"): every collector already in this platform (`StooqPriceCollector`,
`FredCsvCollector`, `WorldBankCollector`, `RssNewsCollector`) fetches a
source's full available series by construction, not an incremental
window — backfill is what a first real collection run against any of
these sources already does, through the identical production pipeline
(`HistoricalReplayEngine` handles reprocessing archived data under a
parser fix; no separate "backfill mode" exists or is needed). Once
priorities 1–11's collectors are real, their first run *is* the backfill.

## 4. World Bank / IMF / FRED live activation — deprioritized, not abandoned

The prior mission's plan (make World Bank the first live collector) is
still valid engineering, just no longer the first priority per the
project owner's explicit re-ordering: these are enrichment sources. Revisit
after priorities 1–11 have real collectors, or opportunistically if World
Bank's egress happens to clear first (same blocker, same unblock).

## 5. Corporate-actions collector (TD-24, still open)

`CorporateEventsAgent` finds nothing from `--data-dir` today because no
collector produces `CorporateEvent`s. Once a company's own IR/PDF source
(priority 2/3) is real, this is likely its natural byproduct — an IR
disclosure PDF collector should extract corporate actions (splits,
dividends, earnings dates), not just narrative news.

## 6. Cross-source corroboration + latency measurement (TD-11 / TD-16)

Once two `IMPLEMENTED` sources overlap coverage (e.g. two independent EGX
price sources), wire real `consistency_score`. Instrument `HttpFetcher` to
time requests so `reputation.py`'s `latency` dimension stops being
permanently unmeasured.

## 7. Calibration pass (TD-17, TD-20, TD-28 — new this phase)

Once real run history and real ToS-page checks exist, revisit
`qualification.py`'s promotion thresholds, `health.py`'s alert thresholds,
`legality.py`'s red/green keyword lists, and the company-directory-match
token-overlap heuristic (TD-28) — all declared policy today.

## 8. Scheduled production pipeline + discovery runs

Wire `agx run` and `agx discover-sources` into a periodic job once any
deployment target exists (System 18) — both are deployment-ready today;
only the "run this on a schedule" wiring is deployment-shaped.

## 9. ToS reviews (business/legal decision, not engineering)

Yahoo Finance, TradingView, Investing.com, Google Trends, LinkedIn/company
social, public Telegram, Google Scholar, ResearchGate — each needs a human
legal judgment on automated-collection terms before any code changes.

## Beyond this

Per the charter's build order, no later system's work should start while
System 02 still has closeable (non-business-blocked) gaps. Items 1–5 above
are exactly that kind of gap and take priority. Longer-horizon, post-1.0
items (trained per-horizon models, covariance-based portfolio optimization,
remaining scientist agents/adversarial attacks, a Monte Carlo experiment, a
database-backed `Repository[T]`) are tracked in `docs/ROADMAP.md`'s
"Post-1.0" section and are not immediate next missions.
