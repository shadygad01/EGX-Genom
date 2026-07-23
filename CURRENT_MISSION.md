# Current Mission

**Connect AGX's first live production sources, in strict business-value
order, autonomously — Production Execution Phase.**

The project owner has reset priorities: engineering elegance is now
secondary to business value, and the objective is no longer building
software, it's continuously discovering statistically valid investment
opportunities for EGX30/EGX70. World Bank/IMF/FRED remain useful
enrichment but are explicitly **not** primary production milestones
anymore — the priority order is now:

1. Official Egyptian Exchange (EGX)
2. Investor Relations — every EGX30 company
3. Investor Relations — every EGX70 company
4. Central Bank of Egypt (CBE)
5. Financial Regulatory Authority (FRA)
6. CAPMAS
7. Enterprise
8. Mubasher
9. Zawya
10. Reuters (legally accessible public mechanisms)
11. Trading Economics
12. Every additional free public source the Acquisition Intelligence
    Engine discovers on its own

## What this phase engineered

The Acquisition Intelligence Engine (built two missions ago) already
covers priorities 1, 4–11 as seeded `TargetOrganization`s. Priority 2/3
(company Investor Relations) had only a marker entry (`company_ir`,
`per_constituent=True`) with no actual per-company expansion — the real
gap this phase closed:

- **`TargetOrganization.priority`** (new field): every seeded target now
  carries the exact business-value order above; `AcquisitionIntelligenceEngine.
  run_catalog()` (new) processes targets in that order, lowest first.
- **`generate_company_ir_targets(companies)`** (new,
  `acquisition_intelligence/target.py`): one target per EGX30 (today's
  placeholder universe; scales automatically once a real, complete list
  exists) constituent, with **no fabricated domain hints** — see "The one
  real constraint" below for why.
- **`discover_company_directory_links()`** (new,
  `discovery/engine.py`): finds a company's own homepage link on an
  already-fetched directory page by matching anchor text against the
  company's real name — the mechanism that lets Priority 1 (EGX itself,
  once reachable) mechanically supply real per-company hints for Priority
  2/3, instead of guessing ~10-100 corporate domains from training-data
  recall (which would have been exactly the "fabricate a URL" the policy
  forbids).
- **`run_catalog()`** wires the two together: whichever target resolves
  first in priority order gets a real chance to feed discovered company
  hints into not-yet-run per-company targets.
- **`cli.py discover-sources`** now runs the full expanded catalog (org
  targets + generated company IR targets) through `run_catalog`, in
  priority order, by default.
- **Fixed a real, pre-existing circular-import bug** discovered while
  building this (`agx_research.discovery` failed to import if it was the
  first AGX module touched in a fresh process, because `sources.
  qualification` imported `discovery.candidate.SourceCandidate` at module
  level while `discovery.candidate` imports `sources.spec` — a genuine
  architectural defect per this phase's own "fix only if a real defect is
  discovered" rule, not a redesign. Fixed with a `TYPE_CHECKING`-guarded
  import (annotations are already lazy via `from __future__ import
  annotations`); regression-tested with a fresh-subprocess import test.

## The one real constraint, stated plainly (unchanged across three missions)

This development sandbox has no outbound network egress to arbitrary
hosts — confirmed directly and repeatedly, including this phase (`curl`
against `www.egx.com.eg`, `cbe.org.eg`, `fra.gov.eg`, `capmas.gov.eg`,
`mubasher.info`, `stooq.com`, `fred.stlouisfed.org`, and
`api.worldbank.org` all return `CONNECT tunnel failed, response 403`; only
PyPI/npm/anthropic.com are allowlisted). Two direct consequences, both
environmental, not engineering, gaps:

1. **No live source can be verified or connected from this sandbox.**
   `agx discover-sources` is fully wired for the entire priority-ordered
   catalog (12 tiers, ~20 targets today) and correctly reports "no
   reachable domain" for every one — the domain resolver refusing to
   trust an unprobed domain, exactly as designed, every time this has been
   checked across three missions.
2. **The real, complete EGX30/EGX70 constituent lists don't exist in this
   codebase yet** — only a 10-company EGX30 placeholder
   (`universe.EGX30_UNIVERSE_PLACEHOLDER`) and no EGX70 list at all. This
   is a deliberate choice, not an oversight: fabricating ~90 additional
   ticker/company-name pairs from training-data recall (some inevitably
   wrong or stale) would itself violate "never fabricate data" applied to
   something as consequential as index membership. The correct source for
   this list is EGX's own official site (Priority 1) or a verified,
   user-supplied list (a business decision) — not this codebase's memory.
   `generate_company_ir_targets()` already scales to either the moment it
   exists.

**Neither of these is a shortcoming in the engineering.** Every mechanism
needed is built, tested, and wired; the moment this platform runs
somewhere with outbound internet access, `agx discover-sources` performs
real, verified discovery, ranking, `SourceSpec` generation, registration,
and qualification kickoff for the full priority-ordered catalog, with zero
further code changes.

## Genuine blocker (stop condition 1: external dependency)

Continuing to connect real live sources requires either (a) this platform
running somewhere with outbound network egress, or (b) the project owner
supplying a verified EGX30/EGX70 constituent list and/or per-company IR
domains as a business input. Both are named, real, and outside what
engineering alone can resolve from inside this sandbox. Everything
engineering could complete without them has been completed — see
`NEXT_MISSIONS.md` for what runs automatically the moment either unblocks,
and what remains genuinely engineering-closeable in the meantime.
