# Next Missions

In priority order. See `docs/ROADMAP.md` for the full detail behind each
item and `docs/PHASE_STATUS.md` for what's already closed.

## 1. Run the Acquisition Intelligence Engine somewhere with network egress

This is the literal unblock for almost everything below it. `agx
discover-sources` is complete and tested; it has not yet run against the
real internet because this development sandbox is confirmed to have no
outbound egress to arbitrary hosts. The moment it runs in an environment
with egress (a deployment, a differently-configured sandbox), it will:

- Resolve real domains for EGX, Reuters, Mubasher, Zawya, Enterprise,
  Asharq Business, CNBC Arabia, CBE, FRA, CAPMAS, and Trading Economics.
- Discover, verify, and rank real acquisition methods for each.
- Register auto-generated `SourceSpec`s (still `PLANNED`) and begin
  qualification.

## 2. Implement production collectors against whatever the engine discovers

Once step 1 produces real `AcquisitionResult`s, for each with
`registered=True`: write and test the concrete collector its
`SourceSpec.collector` field suggests (often `RssNewsCollector` as
configuration; `ExcelSeriesCollector`/`PdfDocumentCollector` need a
subclass with source-specific parsing), then flip `status` to
`IMPLEMENTED`. This is the "small adapter" the whole platform was built to
make trivial — the discovery, legality, stability, and historical-
availability work will already be done.

## 3. Company IR extraction stage

Per-constituent Investor Relations discovery is scoped as
`per_constituent=True` in the target catalog but not yet iterated over the
EGX universe list (the engine currently runs against single named
organizations). Wiring one `AcquisitionIntelligenceEngine.run_for_target`
call per universe member, plus the report-parsing stage `PdfDocumentCollector`
already flags as needing source-specific work, closes this.

## 4. Activate AlphaVantage/FMP once a user supplies a key

Unchanged from the prior phase: both collectors are code-complete and
tested. Flipping `status` to `IMPLEMENTED` and passing the key into the
constructor is the entire remaining step.

## 5. Cross-source corroboration + latency measurement (TD-11 / TD-16)

Once a second `IMPLEMENTED` source overlaps existing coverage, wire real
`consistency_score` instead of `None`. Instrument `HttpFetcher` to time
requests so `reputation.py`'s `latency` dimension stops being permanently
unmeasured.

## 6. Calibration pass (TD-17, TD-20)

Once real run history and real ToS-page checks exist, revisit
`qualification.py`'s promotion thresholds, `health.py`'s alert thresholds,
and `legality.py`'s red/green keyword lists — all declared policy today.

## 7. Scheduled acquisition intelligence runs (TD-23)

Wire a periodic `agx discover-sources` run (both fresh-target discovery
and `AcquisitionContinuityMonitor` recovery) into a scheduled job once any
deployment target exists (System 18) — both are ready; only the "run this
on a schedule" wiring is deployment-shaped.

## 8. ToS reviews (business/legal decision, not engineering)

Yahoo Finance, TradingView, Investing.com, Google Trends, LinkedIn/company
social, public Telegram, Google Scholar, ResearchGate — each needs a human
legal judgment on automated-collection terms before any code changes.

## Beyond the Data Acquisition Platform

Per the charter's build order, no later system's work should start while
System 02 still has closeable (non-business-blocked) gaps. Items 1–3 above
are exactly that kind of gap and take priority. Longer-horizon, post-1.0
items (trained per-horizon models, covariance-based portfolio optimization,
remaining scientist agents/adversarial attacks, a Monte Carlo experiment, a
database-backed `Repository[T]`) are tracked in `docs/ROADMAP.md`'s
"Post-1.0" section and are not immediate next missions.
