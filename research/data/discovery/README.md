# Weekly Source Discovery evidence

Written by `.github/workflows/discovery.yml` (never by hand, never by the
production `agx run` pipeline) via `agx discover-planned-report`. See
`docs/DATA_ACQUISITION.md`'s "Discovery workflow" section for the full
design.

- `discovery_history.json` — the incremental cache: the last real (non-cached)
  verification attempt per source, with an expiry and an input fingerprint,
  so an unchanged source is not re-probed every week.
- `discovery_report.json` — one evidenced row per in-scope `PLANNED`/
  `CANDIDATE` source: what was found, why it did or didn't verify, and a
  recommendation for a human maintainer. Never a promotion decision by
  itself.
- `discovery_metrics.json` — aggregate counts for the run that produced the
  current `discovery_report.json`.
- `endpoint_candidates.json` — every ranked candidate the engine considered
  per source, not just the winner.

These files live on the `discovery/latest` branch and reach `main` only
through a reviewed pull request the workflow opens/updates — never a
direct commit to `main`. Nothing here ever flips a `SourceSpec.status`; see
`docs/DATA_ACQUISITION.md`.
