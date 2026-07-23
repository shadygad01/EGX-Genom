# Next Missions

In priority order. See `docs/ROADMAP.md` for the full detail behind each
item and `docs/PHASE_STATUS.md` for what's already closed.

## 1. Endpoint verification for the remaining PLANNED sources (engineering-closeable, no business decision needed)

Verify the real, current endpoint for each and flip its `SourceSpec.status`
to `IMPLEMENTED`; wire the existing generic collector (`RssNewsCollector`
for feeds, `ExcelSeriesCollector`/`PdfDocumentCollector` for bulletins) as
configuration, not new code:

- Official: EGX, CBE, FRA, MoF, CAPMAS, Egypt Open Data.
- Company: per-constituent Investor Relations pages (needs a PDF/XBRL
  extraction stage on top of `PdfDocumentCollector` — see below).
- News/Arabic News: Mubasher, Reuters, Zawya, Enterprise, Asharq Business,
  CNBC Arabia, Al Arabiya Business, MarketScreener, Investing.com News,
  Al Mal, Al Borsa, Masrawy Economy, Youm7 Economy, Sky News Arabia
  Economy, Asharq Economy.
- Macro: IMF, OECD, UN Data, Trading Economics.
- Global markets: Suez Canal Authority statistics.
- Alternative/Research: Wikipedia Page Views, GitHub Releases, patent
  databases, official hiring feeds, arXiv, SSRN, NBER.

## 2. Company IR extraction stage

`PdfDocumentCollector` handles fetch/archive/text-extraction generically;
turning extracted IR-report text into `MacroObservation`/`CorporateEvent`
candidates needs a source-specific (or at least report-template-specific)
`parse()` — the one piece of this mission genuinely deferred, since a
generic financial-statement-table extractor would either be a no-op or
guess a layout convention IR reports don't uniformly share.

## 3. Activate AlphaVantage/FMP once a user supplies a key

Both collectors are code-complete and tested. Flipping `status` to
`IMPLEMENTED` and passing the key into the constructor is the entire
remaining step.

## 4. Cross-source corroboration + latency measurement (TD-11 / TD-16)

Once a second `IMPLEMENTED` source overlaps existing coverage (e.g. a
second price feed alongside Stooq), wire real `consistency_score` instead
of `None`. Instrument `HttpFetcher` to time requests so `reputation.py`'s
`latency` dimension stops being permanently unmeasured.

## 5. Calibration pass (TD-17)

Once real run history exists, revisit `qualification.py`'s promotion
thresholds and `health.py`'s alert thresholds — both declared policy today,
same situation as the existing conflict-policy constants (TD-6).

## 6. Scheduled discovery runs

Wire a periodic `discovery.DiscoveryEngine` scan (against a seed list of
known IR/regulator/news homepages) into a scheduled job once any
deployment target exists (System 18) — the engine and the
candidate→registry bridge are ready now; only the "run this on a schedule"
part is deployment-shaped.

## 7. ToS reviews (business/legal decision, not engineering)

Yahoo Finance, TradingView, Investing.com, Google Trends, LinkedIn/company
social, public Telegram, Google Scholar, ResearchGate — each needs a human
legal judgment on automated-collection terms before any code changes.

## Beyond the Data Acquisition Platform

Per the charter's build order, no later system's work should start while
System 02 still has closeable (non-business-blocked) gaps — items 1–6
above are exactly that kind of gap, so they take priority over anything
new in systems 03–18. Longer-horizon, post-1.0 items (trained per-horizon
models, covariance-based portfolio optimization, remaining scientist
agents/adversarial attacks, a Monte Carlo experiment, a database-backed
`Repository[T]`) are tracked in `docs/ROADMAP.md`'s "Post-1.0" section and
are not immediate next missions.
