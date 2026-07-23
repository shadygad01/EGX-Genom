# Completion Report — Priority-Ordered Live Source Connection

## Mission

Connect AGX's first live production sources, in strict business-value
order, autonomously. The project owner reset priorities: engineering
elegance is secondary to business value now, and the objective is
continuously discovering statistically valid investment opportunities for
EGX30/EGX70 — not building more software. World Bank/IMF/FRED are
enrichment only. The explicit order: EGX official (1), EGX30 Investor
Relations (2), EGX70 Investor Relations (3), CBE (4), FRA (5), CAPMAS (6),
Enterprise (7), Mubasher (8), Zawya (9), Reuters (10), Trading Economics
(11), anything else the Acquisition Intelligence Engine discovers on its
own (12).

## Delivered

| Module | Delivers |
|---|---|
| `acquisition_intelligence/target.py` | `TargetOrganization.priority` (new field, 12 named tiers matching the mission's order exactly) + `company_ticker`; every seeded target reassigned; `generate_company_ir_targets(companies)` (new) expands the old `company_ir` per-constituent marker into one real target per EGX30 constituent, with no fabricated domain hints. |
| `discovery/engine.py` | `discover_company_directory_links()` (new) — real anchor-text token matching against a company's name on an already-fetched directory page; `_PageLinkParser` extended to capture anchor text across `handle_starttag`/`handle_data`/`handle_endtag`. |
| `acquisition_intelligence/engine.py` | `AcquisitionIntelligenceEngine.run_catalog()` (new) — processes targets in priority order and feeds any company hint discovered from an earlier-resolved target (e.g. EGX's own directory) into not-yet-run company IR targets. |
| `cli.py` | `discover-sources` now builds the full catalog (named orgs + generated company IR targets) and runs it through `run_catalog` by default, in priority order. |
| `sources/qualification.py` | Fixed a real, pre-existing circular-import bug (`agx_research.discovery` failed to import first in a fresh process) with a `TYPE_CHECKING`-guarded import. |

## The gap this closed

The Acquisition Intelligence Engine (built the mission before this one)
already covered priorities 1 and 4–11 as seeded named organizations.
Priority 2/3 — the highest business-value gap, EGX30/EGX70 company
Investor Relations — had only a marker entry with no actual per-company
expansion, and no ordering existed to make "EGX official first, unlocking
company IR hints" an executable dependency rather than just a wishlist.
Both gaps are closed: `run_catalog()` encodes the ordering and the
hint-feeding dependency as real logic, and `generate_company_ir_targets()`
expands to one target per company today (10, the placeholder EGX30 list)
and automatically to however many exist once a real, complete EGX30/EGX70
list is supplied.

## Verification

- 431 Python tests (up from 413), 18 new — 14 for the priority-ordered
  catalog work, plus 4 more from closing TD-16's remaining half
  (`HttpFetcher` request-latency timing feeding `reputation.py`, found and
  closed while auditing for further unblocked engineering work; see
  `docs/PHASE_STATUS.md`). Covers: priority ordering of
  every named target matches the mission's list exactly; company IR target
  generation produces one target per company with `domain_hints == []`
  (never guessed) and deterministic ticker ordering; `run_catalog()`
  processes in priority order and correctly feeds discovered hints forward
  without overriding a target's own existing hints; `discover_company_
  directory_links()` matches real anchor text against real company names
  with a token-subset heuristic; a fresh-subprocess regression test proves
  `agx_research.discovery` now imports cleanly first.
- `ruff check` clean; `contracts/` unchanged (no new pydantic model exposed
  to the API — `TargetOrganization` isn't API-facing).
- Live verification: ran `discover-sources` against the full 21-target
  catalog (EGX official + 10 company IR + 10 named organizations) in the
  background (exceeded the default command timeout at this scale). Exit
  code 0. Every target processed in exact priority order, each correctly
  reporting "no reachable domain" — this sandbox's confirmed lack of
  outbound network egress, not a defect (see below).

## What did not change, deliberately

- No redesign of the Acquisition Intelligence Engine, Discovery Engine, or
  Source Registry — every change composes or extends what already existed
  (`priority` is a new field, not a new sorting system; `run_catalog` calls
  the existing `run_for_target` per target).
- No fabricated domain hints, ticker/company-name pairs, or EGX70
  constituent list — `generate_company_ir_targets()`'s docstring and its
  test (`test_generate_company_ir_targets_produces_one_per_company_with_no_fabricated_hints`)
  both assert this explicitly.
- `cli.py`'s other subcommands (`run`, `collect`, `status`,
  `export-dashboard`) untouched.

## Genuine blocker — this mission's stop condition

Two blockers, both outside what engineering can resolve from inside this
sandbox, are what stop further live connection (stop condition 1, external
dependency):

1. **No outbound network egress.** Confirmed directly and repeatedly
   across three missions (`curl`/`WebFetch` against `www.egx.com.eg`,
   `cbe.org.eg`, `fra.gov.eg`, `capmas.gov.eg`, `mubasher.info`,
   `stooq.com`, `fred.stlouisfed.org`, `api.worldbank.org` all return
   `CONNECT tunnel failed, response 403`; only PyPI/npm/anthropic.com are
   allowlisted).
2. **No verified, complete EGX30/EGX70 constituent list exists in this
   codebase** — only a 10-company EGX30 placeholder, no EGX70 list at all.
   Fabricating ~90 more ticker/company-name pairs from training-data recall
   would itself violate "never fabricate data" applied to index
   membership — the correct source is EGX's own site (priority 1, blocked
   by #1 above) or a verified list the project owner supplies.

Everything engineering could complete without either input has been
completed. See `NEXT_MISSIONS.md` for what runs automatically the moment
either clears, and `CURRENT_MISSION.md` for the full honesty note.
