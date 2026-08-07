# EGX Collector Memory Profiling Report

**Date:** 2026-08-07
**Scope:** `EgxCompositePriceCollector` / `CollectionService`
(`research/src/agx_research/collectors/egx_prices.py`,
`research/src/agx_research/collectors/service.py`,
`research/src/agx_research/collectors/raw.py`,
`research/src/agx_research/collectors/provenance_index.py`), plus the
production deployment surface that runs them
(`deploy/systemd/egx-collector.timer`/`.service`,
`deploy/systemd/egx-api.service`).
**Tooling:** `research/scripts/profile_egx_collector_memory.py` — a
non-invasive tracemalloc + `/proc/self/status` RSS harness. It imports and
calls the real collector/service code exactly as production does, makes no
network calls (a `MappingFetcher` serves synthetic, wire-format-correct
Yahoo/StockAnalysis payloads), and never edits collector/service source to
take a measurement — instrumentation is a wrapper around `collector.fetch`,
not a patch.

## TL;DR

The EGX collector has **two separate memory stories**, and they have
opposite verdicts:

1. **A single run's peak is real, but it's batching, not a leak.** A
   cold-start run against the full ~101-ticker universe with deep Yahoo
   history genuinely holds hundreds of MB to multiple GB in flight at once
   (measured: **2.45 GB peak RSS** for 101 tickers × 5,500 days of
   synthetic history). This is an expected consequence of "fetch
   everything, then parse everything, then write everything" and does not
   accumulate across independent runs — each process exits and the memory
   is reclaimed.
2. **Across repeated runs, there was a genuine, unbounded memory/disk
   leak** — confirmed by reproducing it, and independently corroborated by
   a real production incident already on record in this repo
   (`docs/TECHNICAL_DEBT.md` TD-63: `provenance_index.json` broke
   GitHub's 100 MiB hard blob limit on 2026-08-01). `CollectionService`
   traced every parsed record as newly-written on **every single run**,
   not just genuinely new/changed ones. Combined with
   `deploy/systemd/egx-collector.timer` firing the full collector every
   **60 seconds**, forever, this made steady-state memory and disk usage
   grow without bound purely from *run count*, never plateauing even when
   the underlying market data never changes.

This report documents both findings with concrete numbers, then documents
the fix that was applied to #2 (verified before/after), plus a set of
smaller, VPS-coexistence-oriented changes made once the leak was confirmed
fixed.

---

## 1. Methodology

`research/scripts/profile_egx_collector_memory.py` supports two scenarios,
both driving the real `EgxCompositePriceCollector` → `CollectionService`
path with a `MappingFetcher` instead of the network:

- **`single`** — one collection run against a configurable universe size
  and Yahoo history depth. Measures `tracemalloc` peak/current, an
  after-fetch/before-parse checkpoint (a non-invasive wrapper around
  `collector.fetch`), the top allocation call sites, and process RSS.
- **`growth`** — the same run repeated for *N* simulated days, reusing the
  *same* `RawDocumentRepository`/`ProvenanceIndexRepository` instances
  across iterations — exactly what production does, since
  `ProductionPipeline._stage_collector_execution` reloads these from an
  ever-growing on-disk JSON file on every invocation
  (`storage.repository.JsonFileRepository._load`). A `--static` flag
  re-fetches **byte-identical** payloads every iteration instead of a new
  trading day, modeling `egx-collector.timer`'s real behavior between two
  calendar trading days (which is most of its 1,440 firings/day).

Universe tickers are real (`research/data/universe/EGX30.csv` +
`EGX70.csv`, 101 unique tickers — the same set the module docstring's
"101-symbol run" comment refers to). Price history is synthetic —
deterministic and wire-format-correct, but this script does not know real
EGX tickers' actual Yahoo `range=max` history depth or real
stockanalysis.com page weight (both unverified without a live fetch), so
depth/size are stress-test parameters, not measured facts. Every place this
report presents a number derived from synthetic input says so.

Two increasingly strong corroborations kept the synthetic-payload approach
honest:

- The `--static` growth scenario reproduces the finding with **zero**
  synthetic-parameter dependence: the pathology exists purely from *run
  count*, regardless of what values were fetched.
- TD-63 (below) is a **real, already-recorded production incident**, not
  something this report had to go looking for.

## 2. Top memory consumers and peak allocations (single run)

Six scenarios were swept (`universe_size` × `history_days`), then one
full-scale run (101 tickers × 5,500 days ≈ full multi-decade history) was
measured to confirm the extrapolation:

| Universe | History (days) | Peak RSS | tracemalloc peak | Price bars written |
|---:|---:|---:|---:|---:|
| 10 | 500 | 99.9 MB | 11.5 MB | 7,500 |
| 10 | 1,500 | 148.7 MB | 27.7 MB | 17,500 |
| 30 | 500 | 160.9 MB | 33.3 MB | 22,500 |
| 30 | 1,500 | 299.7 MB | 79.4 MB | 52,500 |
| 101 | 500 | 373.9 MB | 110.9 MB | 75,750 |
| 101 | 1,500 | 803.9 MB | 259.5 MB | 176,750 |
| **101** | **5,500** | **2,513.9 MB** | **864.6 MB** | **585,800** |

Peak RSS scales linearly in `universe_size × history_days` (ticker-days) at
roughly **~5 KB of resident memory per ticker-trading-day** held in flight
during one run — consistent across every scale tested, including the
104x-larger full-scale point.

**Top allocation sites** (101×1,500 run, `tracemalloc` diff, top consumers by
attributed allocation site):

| Site | Size | Share of tracked heap |
|---|---:|---:|
| `pydantic/main.py:263` (model construction) | 207.0 MB | 78% |
| `provenance_index.py:85` (`_revisions[...].append`) | 16.8 MB | 6% |
| `provenance_index.py:69` (`ProvenanceRecord(...)`) | 13.9 MB | 5% |
| `provenance_index.py:45` (record id string) | 12.1 MB | 5% |
| `provenance_index.py:81` (`materialized_at`) | 6.9 MB | 3% |
| `egx_prices.py:198` (`PriceBar(...)` construction) | 4.7 MB | 2% |

**The single largest, most counter-intuitive finding: the raw price data
itself is not the dominant cost.** For this same run, the actual fetched
JSON text (`raw_content_text_bytes`, measured right after `fetch()`
returns, before any parsing) was **10.8 MB**. The provenance/metadata
bookkeeping *about* that data — `provenance_index.py`'s four allocation
sites plus the matching share of the pydantic total — cost roughly
**15–20x more memory** than the price data it was tracking. At full scale
(101×5,500), the pattern is the same and more extreme: 34.7 MB of raw JSON
text vs. 685.0 MB of pydantic object construction, of which provenance
records account for the majority (588,022 `ProvenanceRecord` objects
against 585,800 price bars — almost exactly 1:1, i.e. one provenance
record was being created **per bar, per run**, independent of whether that
bar's value had ever changed).

## 3. Leak vs. batching — the verdict, precisely

**Single-run peak: batching, not a leak.** A fresh process's peak scales
with how much it fetches/parses/writes in that one run and is released
when the process exits (`Type=oneshot` — `egx-collector.service` really
does exit every minute). This is real and worth knowing about (2.45 GB is
a lot to ask of a shared VPS for one run), but it is bounded per-run and
does not compound.

**Cross-run: a genuine, unbounded leak**, reproduced directly:

`growth --static --universe-size 30 --history-days 200 --sa-days 150 --days 10`
(identical payloads re-fetched 10 times, simulating `egx-collector.timer`
polling between two calendar trading days — the common case, since EGX
trading days are a small fraction of the 1,440 times/day the timer fires):

| Run # | `provenance_records_in_memory` (before fix) | RSS (before fix) |
|---:|---:|---:|
| 1 | 10,530 | 84.4 MB |
| 2 | 21,060 | 100.7 MB |
| 5 | 63,180 | 163.5 MB |
| 10 | **105,300** | **225.9 MB** |

Linear, unbounded growth, **with zero new information arriving** — every
one of those 10 runs fetched byte-identical content. `raw_document_revisions_in_memory`
grew too (120 → 660), for the same root cause one layer up
(`RawDocumentRepository.record_step`).

This is exactly the shape of a leak: memory that grows without bound over
the life of the deployment, driven by *how often the code runs*, never by
how much has genuinely changed.

## 4. Real-world corroboration: this already happened in production

This is not a hypothetical risk. `docs/TECHNICAL_DEBT.md` (TD-63, now
updated) already recorded a real incident:
`research/data/production/provenance_index.json` crossed GitHub's *hard*
100 MiB per-blob limit on **2026-08-01**, silently breaking
`deploy-pages.yml`'s state-persistence step and skipping every step after
it (including the actual site deploy) for that run. That workflow runs
**once per trading day** (`cron: "30 15 * * 0-4"`). TD-63's original
diagnosis — "one record per ticker per collected day" — undersold the real
growth rate: it's one record per ticker **per historical day, per run**,
which is what let a handful of weeks of daily runs blow through 100 MiB.

The self-hosted VPS path added since
(`deploy/systemd/egx-collector.timer`, `OnCalendar=*:*`) fires the same
collector **every 60 seconds**, forever — roughly **1,440x** the run
frequency that already broke the GitHub Pages deploy in weeks. Extrapolating
this report's own measured per-run rate (177,356 new `ProvenanceRecord`
objects per run at 101×1,500) against that cadence: **~255 million new
provenance records per day**, before the fix below. This extrapolation is
flagged as such — it was not run for 1,440 iterations — but the linear,
unconditional-per-run growth this report measured directly makes it a
straightforward multiplication, not a guess about mechanism.

## 5. The fix

Root cause: six materialization functions in `collectors/service.py`
(`_write_price_bars`, `_write_macro_observations`, `_write_corporate_events`,
`_write_financial_statement_line_items`, `_write_index_constituents`,
`_write_sector_classifications`) called their `on_written` callback — which
feeds `ProvenanceIndexRepository.record()` and the run's health/metrics
bookkeeping — **unconditionally for every parsed record on every run**,
never checking whether the value actually differed from what was already on
disk. `RawDocumentRepository.record_step()` (`collectors/raw.py`) had the
identical defect one level up: an already-known, byte-identical document
still got a brand-new `validation_history` revision appended on every
re-collection.

**Fix:** both now compare the incoming value against what's already
persisted and only trace/version a record when it actually changed.

- `service.py`: a new `_row_changed(prior, new_row, fields)` helper
  compares a freshly-parsed record against the corresponding CSV row
  already on disk (accounting for the fact `csv.DictReader` returns
  strings). All six writers now pass through it before calling
  `on_written`. Corporate-events/financial-statement-item description-only
  fields, macro observation values, etc. are compared per-writer, since
  each writer's "value" fields differ.
- `raw.py`: `record_step()` now skips appending a new revision when the
  new step's `(performed_by, detail)` matches the most recently recorded
  step for that document — a genuinely different quality-assessment
  outcome (a different `detail`, e.g. a changed confidence score or
  collector version) still earns a new revision, exactly as before.

Both changes are precise, mechanical, and scoped to *when a provenance
entry is written*, not to what gets fetched, parsed, or stored in the CSVs
themselves — `KnowledgeStore`/genome/graph "everything is versioned"
principles and the CSV files' own idempotent-merge behavior are untouched.

### Before / after (measured, same synthetic payloads, same 10-run scenario)

Corrected the harness's synthetic StockAnalysis price generator first
(it previously computed a fully independent random walk from Yahoo's for
the overlapping recent window, which would never have agreed even in
reality — see the script's `_close_for`/`_volume_for` helpers, now
date-keyed so two "providers" covering the same date agree, matching how
two real quote sources report the same historical close).

| Run # | Provenance records — before | Provenance records — after | RSS — before | RSS — after |
|---:|---:|---:|---:|---:|
| 1 | 10,530 | 6,030 | 84.4 MB | 77.9 MB |
| 2 | 21,060 | 6,030 | 100.7 MB | 79.1 MB |
| 5 | 63,180 | 6,030 | 163.5 MB | 80.1 MB |
| 10 | **105,300** | **6,030** | **225.9 MB** | **81.0 MB** |

(Run 1's own baseline also dropped, 10,530 → 6,030 — the fix additionally
stops the StockAnalysis leg from re-tracing the ~150 dates the Yahoo leg
had *already* traced moments earlier in the same run, an intra-run
duplicate the same defect was also causing.)

After the fix: **zero growth from run 2 onward**, for as many runs as the
scenario is given (verified out to 10; the mechanism has no dependency on
run count, so this generalizes). Before: **10x growth in 10 runs**, with no
sign of ever plateauing.

`raw_document_revisions_in_memory` showed the same pattern: 120 → 660
before the fix (10 runs), flat at 120 after.

Verification: full test suite (`uv run pytest`, 1,041 tests) passes
unchanged, plus four new regression tests
(`test_reingesting_identical_price_data_does_not_regrow_provenance_index`,
`test_reingesting_changed_price_data_is_still_traced`,
`test_record_step_skips_an_identical_consecutive_step`,
`test_record_step_records_a_genuinely_different_outcome`) that lock in
both halves of the behavior: unchanged data doesn't grow the store, and
genuinely changed data still does.

## 6. Production deployment context (why this matters this much)

`deploy/` (systemd units) shows exactly what's persistent vs. periodic on
the shared VPS this report was requested for:

- `egx-api.service` — long-running Fastify process (Decision
  Center/Capital Allocation backend). Reads modest per-route JSON
  artifacts via `api/src/artifactsStore.ts`/`knowledgeStore.ts`, no
  request-scoped batching found.
- `egx-collector.service` — `Type=oneshot`, runs the full
  `agx_research.cli run --mode live` pipeline (the collector this report
  profiled, among others) and exits.
- `egx-collector.timer` — fires `egx-collector.service` on
  `OnCalendar=*:*`, i.e. **every minute**, unconditionally (not gated to
  EGX trading hours in the unit itself).
- `egx-deploy.timer`/`.service` — polls `origin/main` every 5 minutes,
  rebuilds and restarts the above two on a new commit.

Neither service had a memory ceiling before this pass — an unbounded
process on shared infrastructure can, in the worst case, pressure or OOM
other tenants' services, not just its own.

## 7. Other changes made this pass

- **`deploy/systemd/egx-api.service`**: added `MemoryHigh=512M` /
  `MemoryMax=768M`. This is a generous starting ceiling, not a precisely
  measured floor — `api/`'s route handlers were reviewed (see below) but
  not load-tested under this mission. `MemoryHigh` throttles via cgroup
  memory pressure before `MemoryMax`'s hard kill, so a brief spike degrades
  gracefully.
- **`deploy/systemd/egx-collector.service`**: added `MemoryHigh=3G` /
  `MemoryMax=4G`, sized with real margin above this report's measured
  worst-case single-run peak (2.45 GB) — the fix above stops cross-run
  accumulation, but a single large ingest (cold start, or a real Yahoo
  history deeper than this report's stress-test assumption) still has a
  legitimate standing cost, and this ceiling exists so that a worst case
  degrades this one `Type=oneshot` unit — the timer just retries next
  minute — instead of taking down every other tenant on the host.

### Light review of `api/` (flagged, not changed this pass)

`api/src/artifactsStore.ts` and `knowledgeStore.ts` re-read their JSON
files from disk on **every** request — no in-process caching, which is
good for memory (nothing accumulates across requests) at the cost of
repeated disk I/O (an acceptable trade for a memory-constrained goal).
One real, lower-priority inefficiency: `knowledgeStore.ts`'s `load()`
parses the **entire** versioned `knowledge.json` (every historical
revision of every `KnowledgeObject`, matching `JsonFileRepository`'s
"never overwrite, always append" persistence) even though
`allLatest()`/`getById()` only ever use the newest revision per entity.
This is architecturally the same *pattern* as the collector bug (loading
more history than the request needs), but not evidenced to be the same
*severity* — `KnowledgeStore.promote()` only fires when a hypothesis
survives the full 8-gate pipeline, so its growth rate is bounded by
genuine research output, not by run count the way per-bar provenance was.
No fix applied this pass; noted here as a scoped follow-up candidate if
`knowledge.json` is ever observed to grow large enough to matter (the same
"watch it, don't guess at a threshold" posture this repo's technical debt
register already uses elsewhere).

## 8. What this pass did *not* cover

"Optimize the entire project" is a much larger scope than one collector —
being explicit about what's still open:

- **`web/`** — not reviewed. It's a static Vite/React build served by
  nginx on the VPS (`deploy/nginx/egx-genom.conf`), not a persistent
  process, so it's a materially different (and likely much lower-priority)
  memory question than the two long-running/periodic backend services
  this report focused on.
- **`api/`** — reviewed for obvious anti-patterns only (§7), not
  load-tested or profiled the way the collector was.
- **Other collectors** (`stooq.py`, `fred.py`, `worldbank.py`,
  `egx_disclosures.py`, etc.) — not profiled individually. They share
  `CollectionService`, so §5's fix applies to all of them automatically,
  but none were measured for their own fetch/parse peak the way the EGX
  price collector was.
- **`egx-collector.timer`'s every-minute cadence itself** — out of scope
  for a memory-optimization pass to change unilaterally (it's a
  product/data-freshness decision, not a code defect), but worth naming:
  even with this pass's fix, every firing between real trading-data
  updates is still pure repeated work (network requests, CSV
  read-rewrite, quality scoring) that produces no new information. A
  slower cadence (or gating to EGX trading hours) would proportionally
  reduce both the remaining CPU cost this report's own sweep measured
  (single-run wall time scaled the same ~linear way memory did — 101×1,500
  took 4m24s) and outbound request volume, on top of anything already
  fixed here.

## 9. Reproducing this report

```bash
cd research

# Single-run peak at a given scale
uv run python scripts/profile_egx_collector_memory.py single \
    --universe-size 101 --history-days 1500 --sa-days 250 --top 15

# Cross-run growth, identical re-fetches (the leak's exact shape)
uv run python scripts/profile_egx_collector_memory.py growth --static \
    --universe-size 30 --history-days 200 --sa-days 150 --days 10

# Regression tests locking in the fix
uv run pytest tests/test_collection_service.py tests/test_raw_document.py -q
```
