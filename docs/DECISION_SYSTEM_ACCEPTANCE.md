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
- [x] Dashboard validation enforces cross-artifact publication safety: a
  blocked or missing gate cannot coexist with a publication-ready decision or
  a non-cash portfolio, and every published portfolio ticker must have a
  publication-ready numeric buy decision.
- [x] The Pages release workflow requires publication gate, decision history,
  benchmark performance, source truth and ticker gap artifacts before upload;
  missing safety output fails the deployment.

## External publication gates

- [ ] Point-in-time live EGX universe, prices, liquidity and corporate actions
  acquired under terms that permit automated research and the intended output.
- [ ] Official EGX disclosures and at least four comparable company financial
  periods connected with per-value provenance.
- [ ] Current CBE/CAPMAS macro series connected and freshness-monitored.
- [ ] At least two independent price observations agree within a documented
  tolerance for every published ticker/date.
- [ ] At least 30 expired, evaluated decisions per horizon and a positive result
  after costs versus cash and the correct point-in-time EGX benchmark.
- [ ] Human legal review for Egyptian publication, recorded with reviewer,
  scope, date and expiry; conflicts and methodology disclosures approved.

Until every external gate is checked with evidence, every decision remains
`research_only` and the only public-safe instruction is abstention/research.

Runtime evidence is supplied only through `publication_evidence.json` and
`legal_publication_approval.json` in the production data directory. The
pipeline exports its independently evaluated result as `publication_gate.json`;
editing a dashboard file cannot promote a decision.

Operators must run `publication-status` and receive exit code `0` before a
release can claim publication readiness. Exit code `2` is a hard stop. Exact
schemas, freshness limits and the human approval workflow are documented in
[`PUBLICATION_EVIDENCE_RUNBOOK.md`](PUBLICATION_EVIDENCE_RUNBOOK.md).
