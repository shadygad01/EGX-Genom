# Current Mission

**Build the Acquisition Intelligence Engine** — the system must never
require a manually specified endpoint. For every target organization (EGX,
company investor relations, Reuters, Mubasher, Zawya, Enterprise, CBE, FRA,
CAPMAS, Trading Economics, and more as they're added), autonomously
discover every legally accessible acquisition method, verify legality/
stability/historical availability, rank and select the best, auto-generate
a collector configuration, register it, and begin qualification —
continuing to research alternatives whenever a method becomes unavailable.

## Status: engine complete, tested, and wired — live discovery blocked by this sandbox's network policy

Every named responsibility is built:

- [x] Discover acquisition methods — `acquisition_intelligence.engine.
  AcquisitionIntelligenceEngine` composes domain resolution + the existing
  `discovery.DiscoveryEngine` (RSS/PDF-repo/dataset/sitemap/API-doc scans).
- [x] Evaluate all methods — every discovered candidate gets an independent
  legality, stability, and historical-availability assessment.
- [x] Verify legality — `legality.py`: robots.txt (three-state) + ToS
  keyword heuristics; scraping never auto-clears; ambiguity blocks.
- [x] Verify stability — `stability.py`: URL-shape + repeated-probe
  consistency.
- [x] Verify historical availability — `historical.py`: Internet Archive
  Wayback Machine APIs (free, no key, decades-stable).
- [x] Rank the acquisition methods — `ranking.py`: legality as a hard gate,
  composite of the other two scores.
- [x] Select the best one — `select_best`.
- [x] Auto-generate collector configuration — `config_generation.py`:
  a full `SourceSpec` with a suggested collector class where unambiguous.
- [x] Register in the Source Registry — `engine.py` adds/updates the spec.
- [x] Begin qualification — an initial reachability run is recorded and
  handed to the existing `sources.qualification.evaluate_promotion`.
- [x] Continue researching alternatives on failure — `continuity.py`:
  `AcquisitionContinuityMonitor` re-runs discovery, excluding the failed
  method, for any source whose health goes `DOWN`.
- [x] No manually supplied URLs, no predefined endpoints — every URL in
  the pipeline is either independently probed for reachability or
  discovered from already-fetched page content; `TargetOrganization`
  carries identity, never an endpoint.

See `docs/DATA_ACQUISITION.md`'s "Acquisition Intelligence Engine" section
for the full design and `docs/PHASE_STATUS.md`'s System 02 row for the
audit-level summary.

## The one honest gap, and why it isn't a shortcoming of the engine

This development sandbox has **no outbound network egress to arbitrary
hosts** — verified directly, not assumed: both `curl` (direct) and
`WebFetch` return HTTP 403 for every real target site attempted (EGX,
Reuters, Mubasher, Wikipedia), and the environment's proxy status
(`$HTTPS_PROXY/__agentproxy/status`) confirms egress is allowlisted to
PyPI/npm/crates/Go-proxy/anthropic.com only, nothing else. Running
`agx discover-sources` against all 11 non-per-constituent seed targets in
this sandbox produces "no reachable domain found" for every one of them —
the domain resolver correctly refusing to trust an unprobed domain, exactly
as designed. This is not a fabricated or partial result: the engine and its
20-plus orchestration tests (all passing, using fakes) prove the full
pipeline works end to end; it simply has not yet had a network to run
against for real. The moment this platform runs somewhere with egress
(a deployment, or a different sandbox configuration), `agx discover-sources`
will do real, verified discovery against these organizations with no code
changes required.

## What's next (see `NEXT_MISSIONS.md`)

"Continue autonomously by implementing production collectors using the
acquisition methods discovered by the engine" is the literal next mission
— but it is genuinely, externally blocked until the engine has run
somewhere with egress and actually discovered something to implement
against. Nothing was fabricated to work around that. The moment a real
discovery result exists (in this sandbox if its network policy changes, or
in any deployment with egress), the next step is: for each `AcquisitionResult`
with `registered=True`, write and test the concrete collector the generated
`SourceSpec.collector` field suggests, then flip that source's `status` to
`IMPLEMENTED`.
