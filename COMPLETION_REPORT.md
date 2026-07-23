# Completion Report — Acquisition Intelligence Engine

## Mission

The system must never require manually specified endpoints or manually
provided data sources. For every target organization (EGX, company
investor relations, Reuters, Mubasher, Zawya, Enterprise, CBE, FRA,
CAPMAS, Trading Economics, and more as they're added): discover every
legally accessible acquisition method, evaluate and verify each
(legality/stability/historical availability), rank them, select the best,
auto-generate the appropriate collector configuration, register it in the
Source Registry, and begin qualification — continuing to research
alternatives whenever a method becomes unavailable.

## Delivered

New package `research/src/agx_research/acquisition_intelligence/`:

| Module | Delivers |
|---|---|
| `target.py` | `TargetOrganization` — identity only (name/category/country/public-brand domain hints), never a URL; seeded for all 12 named organizations, linked to existing `SourceSpec` catalog entries. |
| `domain_resolution.py` | `HeuristicDomainResolver` — probes every hint and name-derived guess for actual reachability before trusting a domain; nothing is asserted without a successful probe. |
| `legality.py` | `assess_legality` — robots.txt (three-state, via new `HttpFetcher.robots_status`) + ToS red/green-flag keyword heuristics; `HTML_SCRAPE` can never auto-clear to `ALLOWED`; ambiguity blocks. |
| `stability.py` | `assess_stability` — URL-shape heuristics + repeated-probe status-code consistency. |
| `historical.py` | `assess_historical_availability` + `WaybackAvailabilityClient` — the Internet Archive's free, no-key `wayback/available` and CDX APIs, scored by archived-snapshot span. |
| `ranking.py` | `rank_methods`/`select_best` — legality as a hard gate (never scored down and reconsidered), composite of stability + historical scores among survivors. |
| `config_generation.py` | `generate_source_spec` — auto-generates a full `SourceSpec` (collector class suggested where unambiguous); `status` always stays `PLANNED`, never silently `IMPLEMENTED`. |
| `engine.py` | `AcquisitionIntelligenceEngine` — orchestrates domain resolution → discovery → verification → ranking → config generation → registration → an initial qualification-pipeline evaluation, end to end. |
| `continuity.py` | `AcquisitionContinuityMonitor` — re-runs discovery, excluding the failed method's URL, for any registered source whose health goes `DOWN`. |
| `live.py` | The one file wiring real network access (`HttpFetcher` + a live Wayback client) for a deployment with egress; every other module is network-free. |

Plus: `HttpFetcher.robots_status()` (a three-state robots.txt check
distinct from the existing permissive-by-default `fetch_bytes` behavior),
and `cli.py`'s new `discover-sources` subcommand.

## Verification

- 51 new tests (397 total, up from 346), 100% offline (fakes/fixtures only)
  — covering every module individually and the full orchestration pipeline:
  happy path, no-reachable-domain, unfetchable homepage, no candidates
  discovered, legality gate rejecting the only candidate, successful
  registration + qualification kickoff, idempotent re-runs, exclusion-driven
  alternative selection, and continuity recovery.
- `contracts/` drift check clean (no `SourceSpec` schema change this phase).
- `ruff check` clean.

## The one honest, verified gap

**This development sandbox has no outbound network egress to arbitrary
hosts.** This was checked directly, not assumed:

1. `curl` directly to `egx.com.eg`, `reuters.com`, `mubasher.info` — all
   returned `CONNECT tunnel failed, response 403`.
2. The environment's proxy status endpoint confirmed the policy: egress is
   allowlisted to `anthropic.com`, PyPI/npm/crates/Go-proxy registries, and
   local/private ranges only — nothing else.
3. `WebFetch` (routed through separate infrastructure) was also tried
   against `egx.com.eg` and `en.wikipedia.org` — both returned HTTP 403,
   while a control fetch of `pypi.org` succeeded, confirming the block is
   general, not site-specific.
4. Running `agx discover-sources` against all 11 non-per-constituent seed
   targets in this sandbox produced "no reachable domain found" for every
   one — the domain resolver correctly refusing to trust an unprobed
   domain, exactly as designed.

Because of this, the mission's final instruction — "continue autonomously
by implementing production collectors using the acquisition methods
discovered by the engine" — could not be carried out for real in this
session: the engine discovered nothing live to implement a collector
against, because it has not yet had a network to discover on. Fabricating
a plausible-looking discovery result to satisfy that step would have
violated this codebase's core, repeatedly-enforced anti-fabrication rule
(the same rule that keeps `data_quality_score` unset until measured, keeps
unimplemented experiments raising `NotImplementedError` instead of faking a
result, and keeps the seed catalog's 12 `PLANNED` sources honestly
unverified rather than guessed). The engine itself is complete, tested, and
ready — this is a genuine external dependency (no egress), exactly the kind
the mission's own build order anticipates as a legitimate stopping point,
not a shortcoming in the engineering.

## Follow-through

See `NEXT_MISSIONS.md`: item 1 is running the engine somewhere with
network egress; item 2 is implementing production collectors against
whatever it discovers there — the literal next step once item 1 is
possible.
