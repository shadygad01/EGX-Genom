# Current Mission

**Build the AGX Data Acquisition Platform** — not more individual
collectors, but the infrastructure that makes adding a collector trivial:
registry, discovery, qualification, reputation, health monitoring, raw
archive, provenance, historical replay, and mission-control documentation,
per the standing instruction in `docs/DATA_ACQUISITION.md`'s originating
brief.

## Status: platform infrastructure complete

Every named subsystem is built, tested, and wired end-to-end:

- [x] Source Registry — `SourceSpec` with the full charter field set +
  three independent state axes (`status`/`lifecycle_state`/`health_status`/
  `activation_status`).
- [x] Collector Framework — `Collector` ABC serving RSS/REST-JSON/CSV/
  Excel/PDF/Filesystem/Browser(stub)/Archive-Replay, with retry/checkpoint/
  logging/metrics/timeouts/rate-limiting/provenance/versioning built into
  the shared framework, not repeated per collector.
- [x] Source Discovery Engine — RSS autodiscovery, PDF-repository scan,
  structured-dataset scan, sitemap scan, API-doc-link scan; structurally
  incapable of trusting a source itself.
- [x] Source Qualification Pipeline — Candidate → Quarantine → Evaluation
  → Trusted → Core, evidence-gated, one stage at a time.
- [x] Source Reputation Engine — the charter's 9 dimensions, computed from
  real per-run counters.
- [x] Source Health Monitoring — automatic failure/layout-change/schema-
  drift/staleness detection, with an append-only alert trail.
- [x] Raw Archive — content-addressed, write-once storage for every
  collected artifact, text and binary.
- [x] Canonical Transformation — `Collector.parse()`, a pure, versioned,
  replayable function of one `RawDocument`.
- [x] Provenance Layer — per-value trace (source/collector/artifact/
  transformation/timestamp/hash/schema-version) for every materialized
  value, not just news.
- [x] Historical Replay — rebuild materialized data from the Raw Archive
  alone after a parser change, with no new fetch.
- [x] Mission Control — this document set.

See `docs/DATA_ACQUISITION.md` for the full design and
`docs/PHASE_STATUS.md`'s System 02 row for the audit-level summary.

## What's genuinely still open (see `NEXT_MISSIONS.md`)

Production collectors beyond the four already `IMPLEMENTED` (Stooq, FRED,
World Bank, generic RSS) split cleanly into three blocking categories —
none silently skipped, each named with its exact blocker in the registry
and in `docs/DATA_ACQUISITION.md`'s "What's still blocked" section:

1. **Endpoint verification** (EGX, CBE, FRA, CAPMAS, MoF, Egypt Open Data,
   Company IR, Mubasher, Reuters, Zawya, Enterprise, Asharq Business, CNBC
   Arabia, Trading Economics, and the remaining Arabic/English news feeds)
   — this sandbox has no outbound network egress to confirm a live
   endpoint against the real site, and this codebase's own rule forbids
   fabricating one from memory. The generic collectors that would serve
   almost all of these already exist and are tested.
2. **User-supplied API key** (AlphaVantage, FMP) — collector code is
   complete and tested; only a credential is missing, and that's the
   user's decision to obtain, not engineering's to fake.
3. **ToS review** (Yahoo Finance, TradingView News, Investing.com, Google
   Trends automation, LinkedIn/company social, public Telegram, Google
   Scholar, ResearchGate) — a human legal/ToS judgment call, out of
   engineering's scope to resolve unilaterally.

None of these block calling the platform itself complete: the point of
this mission was that once any one of the three blockers above clears,
activating that source is a small, mechanical adapter — exactly what got
built.
