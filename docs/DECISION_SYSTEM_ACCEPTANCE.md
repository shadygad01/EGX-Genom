# Decision System Acceptance Standard

This is the measurable definition of "100%" for AGX as a public-facing
investment-decision system. Engineering completion and publication readiness
are deliberately separate; a green test suite cannot grant data rights or a
legal approval.

## Engineering gates

- [x] One action per ticker and horizon; no blended horizon drives an action.
- [x] Explicit validity, risk metric, confidence, position cap, invalidation,
  abstention reasons, evidence references, and publication status.
- [x] Horizon-specific readiness and matching active knowledge.
- [x] Production sample floors; clean adversarial checks do not add confidence.
- [x] Family-wise multiple-testing correction.
- [x] Out-of-sample backtest after transaction costs.
- [x] Append-only decision ledger with automatic post-expiry evaluation.
- [x] Performance summary refuses an edge claim below 30 benchmark-matched
  evaluated decisions, and refuses sufficiency when EGX30 benchmark history is
  missing.
- [x] Source truth distinguishes catalogued, legally usable, attempted, fetched,
  fresh, productive, corroborated, and decision-reaching sources.
- [x] Arabic RTL decision-first UI with permanent research/demo warning.
- [x] Python, API and web tests plus production builds and rendered-browser QA.
- [x] Fail-closed publication gate: boolean claims without evidence references,
  expired legal approval, missing benchmark performance, or any incomplete
  external condition force every horizon decision to `research_only`.
- [x] Chronological test tail is hidden before hypothesis discovery; paired
  returns are joined on shared dates, and expected return/risk use 3/20/126-day
  forward units for short/medium/long horizons.
- [x] Production readiness is an issuance gate; non-executed actions never enter
  the trade-performance sample; research-only decisions display zero position.
- [x] Source implementation and legal-use clearance are independent; production
  collectors preserve the shared robots policy.
- [x] Publication evidence resolves against immutable RawDocument ids, source
  ids, SHA-256 hashes and fetch timestamps; freshness, full coverage, legal
  clearance and independent price-provider groups are enforced.
- [x] Moving-block bootstrap preserves local time dependence; overlapping
  walk-forward inference uses Newey-West HAC; multiple-testing family size is
  cumulative across persisted attempts rather than reset each run.
- [x] A buy candidate requires a fresh positive reference price plus numeric
  entry and invalidation levels; missing price forces abstention.
- [x] Portfolio allocation runs after publication gating and accepts only
  publication-ready buy decisions with numeric execution levels and a non-zero
  approved position cap; all research-only output remains cash.
- [x] Decision Center exposes per-ticker data-layer gaps and next actions in
  both API and static modes; core decision summaries, risk, invalidation and
  evidence-reference surfaces are Arabic and retain traceable ids/versions.
- [x] The decision engine itself emits Arabic entry, review, invalidation,
  abstention, readiness blockers and next actions; Arabic output does not rely
  on cosmetic heading translation in the web layer.
- [x] The primary briefing surface presents system health, market summary,
  opportunities, risks, news, catalysts, knowledge, discoveries and portfolio
  allocation in Arabic.
- [x] Primary navigation, Market Intelligence, Company Workspace and Source
  Intelligence use Arabic labels, empty states and operational explanations.
- [x] Research Center and Knowledge Graph use Arabic pipeline states, table
  labels, empty states and relationship guidance while preserving technical ids.
- [x] Mission Control and System Administration use Arabic operational labels;
  the static audit finds zero English page/card/table/empty-state titles in
  `web/src/pages` (source-provided content and technical identifiers excluded).
- [x] Dashboard validation enforces cross-artifact publication safety: every
  `publication_ready` decision in `investment_cases.json` is independently
  re-derived against `meta.decision_quality.evaluate_decision_quality()` and
  must genuinely pass; a non-cash portfolio requires at least one ticker with
  a publication-ready numeric buy decision, and every published portfolio
  ticker must have one.
- [x] The Pages release workflow requires system maturity, decision history,
  benchmark performance, source truth and ticker gap artifacts before upload;
  missing safety output fails the deployment.

## Decision Quality Gate (2026-08-02, superseding the prior "external
publication gates" checklist below)

Publication is governed by the quality of each specific decision, not by a
system-wide switch requiring every ticker to wait on the same external
evidence, track record, or legal sign-off — project owner direction,
2026-08-02, see `docs/ARCHITECTURE_DECISIONS.md` for the full reasoning and
`meta.decision_quality`'s module docstring for the mechanism. A decision
publishes when, for that specific ticker and horizon:

- [x] Supporting evidence is present and traceable (`supporting_evidence`/
  `evidence_refs` both non-empty).
- [x] The investment thesis is complete (`why_this_stock`/`why_now`/
  `why_not_others` all stated).
- [x] Confidence was actually calculated (a finite number in `[0, 1]`).
- [x] Invalidation conditions are defined.
- [x] Entry and review (monitoring) conditions are defined.
- [x] The decision is internally consistent (a `BUY_CANDIDATE` carries
  numeric entry and invalidation price levels).

All six, automatically, per decision — no file to author, no separate
command to run before a decision can publish.

### System Maturity — informational only, never a gate

The five items the old checklist required simultaneously before *any*
decision could publish (live EGX market data; four periods of official
disclosures; current CBE/CAPMAS macro data; two independent price
corroborations; 30+ per-horizon benchmark-outperforming results; human legal
review) still matter — as inputs to
`meta.system_maturity.compute_system_maturity()`'s non-blocking credibility label
(`early`/`validating`/`developing`/`established`/`verified`), reported by
`agx publication-status` (always exits `0` — there is no "blocked" outcome
left to signal). A human legal/governance review file remains available and
optional, and can only ever raise the reported level to `verified`; it never
gates whether `agx decide`/`agx run` publishes anything. Exact mechanism
documented in [`PUBLICATION_EVIDENCE_RUNBOOK.md`](PUBLICATION_EVIDENCE_RUNBOOK.md).
