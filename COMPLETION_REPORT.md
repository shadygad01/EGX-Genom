# Completion Report — Universe Engine + Corporate Disclosures

## Mission

The project owner handed over full engineering ownership: no more
isolated tasks, continue autonomously through the entire remaining
backlog until a genuine blocker is hit, in this refined business-priority
order: (1) EGX official, (2) Universe Engine, (3) Investor Relations
discovery, (4) Corporate disclosures, (5) Financial statement collection,
(6) Historical backfill, (7) Live incremental synchronization, (8–15) CBE/
FRA/CAPMAS/Enterprise/Mubasher/Zawya/Reuters/Trading Economics, (16)
anything else discovered automatically.

## Delivered

| Module | Delivers |
|---|---|
| `universe/constituent.py` | `IndexConstituent` — `{index, ticker, company_name, as_of_date}`, a date per row (not one overwritten snapshot) for point-in-time-correct universe membership. |
| `collectors/base.py`, `collectors/service.py`, `collectors/quality.py` | `CollectionBatch` gained `index_constituents` + `corporate_events`; `CollectionService` materializes both to CSV (merged by natural key, provenance-traced) exactly like the existing price/macro writers. |
| `universe/collected.py` | `CollectedUniverseProvider` (reads the collected CSV, never fabricates) + `FallbackUniverseProvider` (mirrors `FallbackDataProvider`); wired into `production.pipeline` and `cli.py`'s `discover-sources`. |
| `collectors/index_constituents.py` | `IndexConstituentCollector` — generic header-matching CSV parser for a constituent-list export; built and tested, not yet wireable (endpoint unverified). |
| `collectors/corporate_event_classifier.py` | `classify_corporate_event_type()` — declared headline keyword heuristic reusing `events.adapters`'s exact taxonomy keys. |
| `collectors/rss.py` | `RssNewsCollector` gained `classify_corporate_events`, applying the classifier per entry alongside the existing `NewsItem` production. |
| `production/collector_plan.py` | `rss_generic`'s mock/replay collector now classifies corporate events; verified live. |

## The gaps this closed

**Universe Engine (priority 2).** `universe.UniverseProvider` had exactly
one implementation (`StaticUniverseProvider`, a fixed placeholder) and no
path for a real collected constituent list to ever reach it — even once
one could be collected, nothing would have known where to write it or how
to read it back. Both halves now exist: the generic collection +
materialization + read-back infrastructure (fully real, fully tested), and
the collector itself (built, tested, but honestly gated on endpoint
verification — see below).

**Corporate disclosures (priority 4), closing TD-24.** `CorporateEvent`
had a schema and a read path but nothing ever produced one —
`CorporateEventsAgent` found nothing from `--data-dir`. A declared
headline-keyword classifier now produces real (if narrow, headline-only)
corporate events from the same RSS content the platform already collects
for news, verified with a live mock-mode pipeline run.

**Investor Relations discovery (priority 3)** needed no new engineering —
confirmed already fully built two missions ago and ready to scale the
moment the Universe Engine (or a user-supplied list) provides a real
constituent set.

**Historical Backfill (priority 6) / Live Incremental Sync (priority 7)**
needed no new engineering either — confirmed already satisfied by every
collector's existing "fetch full series" + "merge idempotently by key"
design.

## Verification

- 462 Python tests (up from 431), 31 new. Covers: `IndexConstituent`
  point-in-time correctness (never looks ahead of the query date, empty
  when nothing collected or every snapshot postdates the query);
  `FallbackUniverseProvider`'s preference order; `IndexConstituentCollector`'s
  header-matching (order-independent, warns rather than guesses on
  ambiguous/malformed input); `CollectionService`'s materialization and
  idempotent re-ingestion of both new record types with correct provenance
  keys; the corporate-event classifier's keyword coverage and
  false-positive avoidance (no keyword match → `None`, never a guess);
  `RssNewsCollector`'s classification requiring exactly one ticker match;
  that `CollectionService` never double-registers a corporate event as an
  Event (materializes only, composing with the existing
  `events_from_corporate_events` adapter rather than duplicating it).
- `ruff check` clean; `contracts/` unchanged (neither new type is
  API-facing).
- **Live verification**: `agx run --mode mock` now writes real
  `COMI,2026-06-09,EARNINGS,...` and `MFPC,2026-06-04,DIVIDEND,...` rows
  to `--data-dir/corporate_events.csv`, derived from the platform's
  existing mock RSS headlines — a genuine, working capability, run and
  confirmed directly, not merely unit-tested in isolation.

## What did not change, deliberately

- No redesign of `CollectionService`, `RssNewsCollector`, or
  `UniverseProvider` — every change extends an existing interface
  (`CollectionBatch` gained fields; `RssNewsCollector` gained an opt-in
  flag; `FallbackUniverseProvider` mirrors `FallbackDataProvider`'s
  existing pattern exactly) rather than introducing a parallel mechanism.
- No specific EGX wire-format assumptions: `IndexConstituentCollector`'s
  column detection is header-text-matching, not a hardcoded column order,
  because no real EGX constituent-list page has ever been fetched to
  verify one — inventing a specific parser for an unverified format would
  be guessing a wire format, not parsing a real one (new debt, TD-30).
- No numeric detail fabricated from a headline: classified corporate
  events always carry `details={}` — a split ratio or dividend amount
  cannot be reliably read off a title, and guessing one would corrupt
  `data.adjustments` (new debt, TD-29; new risk, R-20, for the
  `events_from_corporate_events` confidence-modeling question this exposes).
- `egx_official`'s `SourceSpec` stays `PLANNED` — not flipped to
  `IMPLEMENTED` to make the new collector "usable," since that would
  misrepresent verification that hasn't happened.

## Genuine blockers — unchanged, named again for this phase

1. **No outbound network egress** from this sandbox (confirmed directly
   and repeatedly across four missions now) — blocks verifying
   `egx_official`'s real endpoint, which blocks `IndexConstituentCollector`
   ever running live, which blocks priorities 1, 2 (at real scale), 3 (at
   real scale), and 8–16.
2. **No verified, complete EGX30/EGX70 constituent list** exists in this
   codebase — a business decision reserved for the project owner;
   fabricating one from training-data recall would violate the platform's
   anti-fabrication principle.

Everything engineering could complete without either input has been
completed this phase. The next milestone needing neither input —
**Financial Statement Collection (priority 5)** — is already queued in
`NEXT_MISSIONS.md` and underway.
