# Next Missions

In priority order. See `docs/ROADMAP.md` for the full detail behind each
item and `docs/PHASE_STATUS.md` for what's already closed.

## 1. First live production collector (current mission — see `CURRENT_MISSION.md`)

Swap one mock-mode collector in `production/collector_plan.py` for a real
`HttpFetcher`-backed one against a verified live endpoint. World Bank is
the recommended first candidate: already `IMPLEMENTED`, tested, a stable
free no-key public API. This proves the production pipeline's mock/replay
seam (`AD-28`) actually swaps out cleanly for a live data source with zero
changes to `CollectionService`, `ProductionPipeline`, or the collector's
own `parse()`.

## 2. Corporate-actions collector (TD-24)

`CorporateEventsAgent` currently finds nothing when the production
pipeline's `MarketMemory` reads from `--data-dir`, since no collector
produces `CorporateEvent`s yet (unlike the static `research/data/mock/`
path, which has two hand-authored ones). A real collector — likely parsed
from Company IR PDF disclosures once that source is verified — closes
this; wire it the same way `collector_plan.py` wires price/macro/news.

## 3. Run the Acquisition Intelligence Engine somewhere with network egress

Still open from the prior mission: `agx discover-sources` is complete and
tested but has not yet run against the real internet (this sandbox has no
outbound egress to arbitrary hosts, confirmed directly). The moment it
runs with egress, it will resolve real domains and discover real
acquisition methods for EGX, Reuters, Mubasher, Zawya, Enterprise, Asharq
Business, CNBC Arabia, CBE, FRA, CAPMAS, and Trading Economics.

## 4. Implement production collectors against whatever the engine discovers

Once #3 produces real `AcquisitionResult`s, write and test the concrete
collector each one's `SourceSpec.collector` field suggests, then flip
`status` to `IMPLEMENTED` and wire it into `collector_plan.py` alongside
the collectors #1 and #2 added.

## 5. Company IR extraction stage

Per-constituent Investor Relations discovery is scoped
(`TargetOrganization.per_constituent=True`) but not yet iterated over the
EGX universe list, and needs the report-parsing stage `PdfDocumentCollector`
already flags as source-specific work.

## 6. Activate AlphaVantage/FMP once a user supplies a key

Both collectors are code-complete and tested. Flipping `status` to
`IMPLEMENTED` and passing the key into the constructor is the entire
remaining step.

## 7. Cross-source corroboration + latency measurement (TD-11 / TD-16)

Once a second `IMPLEMENTED` source overlaps existing coverage, wire real
`consistency_score` instead of `None`. Instrument `HttpFetcher` to time
requests so `reputation.py`'s `latency` dimension stops being permanently
unmeasured.

## 8. Calibration pass (TD-17, TD-20)

Once real run history and real ToS-page checks exist, revisit
`qualification.py`'s promotion thresholds, `health.py`'s alert thresholds,
and `legality.py`'s red/green keyword lists — all declared policy today.

## 9. Scheduled production pipeline runs

Wire a periodic `agx run` into a scheduled job once any deployment target
exists (System 18) — the command is deployment-ready today; only the "run
this on a schedule" wiring is deployment-shaped, not engineering. This is
the "runs unchanged under GitHub Actions and Cloudflare" the pipeline
mission specified; `.github/workflows/deploy-pages.yml` already proves the
GitHub Actions half.

## 10. ToS reviews (business/legal decision, not engineering)

Yahoo Finance, TradingView, Investing.com, Google Trends, LinkedIn/company
social, public Telegram, Google Scholar, ResearchGate — each needs a human
legal judgment on automated-collection terms before any code changes.

## Beyond the Data Acquisition Platform

Per the charter's build order, no later system's work should start while
System 02 still has closeable (non-business-blocked) gaps. Items 1–5 above
are exactly that kind of gap and take priority. Longer-horizon, post-1.0
items (trained per-horizon models, covariance-based portfolio optimization,
remaining scientist agents/adversarial attacks, a Monte Carlo experiment, a
database-backed `Repository[T]`) are tracked in `docs/ROADMAP.md`'s
"Post-1.0" section and are not immediate next missions.
