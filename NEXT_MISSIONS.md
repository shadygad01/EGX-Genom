# Next Missions

## Closed this phase: Zero-Cost Production Deployment + Shadow Fund

See `CURRENT_MISSION.md`'s "Zero-Cost Production Deployment + Shadow Fund"
entry, `docs/PHASE_STATUS.md`'s matching section, and AD-56/AD-57/TD-64.
**Genuinely next now**, in priority order:

1. **`InvestmentProofDashboard`** — unchanged from every prior mission's
   note (originally named after the Investment Proof Framework mission):
   `agx investment-proof`'s Capital Trust Report is still CLI-only, never
   wired into `agx_research.dashboard.export`/a matching API route/a web
   surface. This mission's redirection toward the Shadow Fund didn't
   reach it — still the top item on this list.
2. **NAV-history line chart on Monitoring** (TD-64) — `shadow_fund_history.json`'s
   full daily NAV series is already exported and already fetched
   (`getShadowFundHistory()`); only a chart component over already-wired
   data is missing, not a new backend capability.
3. **Real EGX30 (or other index-level) benchmark comparison** stays
   honestly flat for the Shadow Fund (TD-64) — same root cause and same
   trigger as TD-58's `DecisionLedger` benchmark gap, not a new blocker.
4. **Rebalance-threshold/risk-sample-size calibration** (TD-64:
   `REBALANCE_THRESHOLD_PCT = 0.01`/`MIN_RISK_SAMPLE_DAYS = 20`) — once
   real Shadow Fund NAV history accumulates across enough trading days,
   same calibration-trigger posture as every other declared threshold in
   `docs/TECHNICAL_DEBT.md`.
5. Everything already named as genuinely next before this phase (below)
   is unchanged.

## Closed prior phase: EGX Investment Methodology (permanent investment doctrine)

See `CURRENT_MISSION.md`'s "EGX Investment Methodology" entry and
`docs/PHASE_STATUS.md`'s matching section. **Genuinely next now**, in
priority order:

1. **The three named detector gaps in `docs/INVESTMENT_PLAYBOOK.md`** —
   interest-rate cycles, inflation shocks, and sector rotation each
   currently read only indirectly (via `agents.macro`'s generic
   sensitivity mechanism or `MarketStructureAgent`'s co-movement proxy).
   Real engineering work: a CBE policy-rate collector and a dedicated
   rate-sensitivity mechanism; a real CPI/inflation series and a
   dedicated inflation-sensitivity mechanism; a dedicated sector-rotation
   detector distinct from the existing sector-exposure/co-movement
   proxies. Each should close by extending the doctrine's own "doctrine,
   not yet a dedicated detector" label to "real, mechanically detected"
   in the same change that ships the detector — the playbook itself
   should never silently fall out of date with what the platform can
   actually see.
2. **Amendment discipline going forward**: every future mission touching
   `meta.decision_engine`/`meta.publication_gate`/`meta.readiness`/
   `decision_service/`/`capital_allocation/`/`investment_proof/` must
   update the doctrine set in the same change (`CLAUDE.md`'s new
   standing rule) — treat a decision-affecting threshold or gate change
   that doesn't touch `docs/INVESTMENT_CONSTITUTION.md`/`DECISION_
   STANDARDS.md`/`PORTFOLIO_STANDARDS.md` as incomplete, the same way a
   schema change without a matching `contracts/` regeneration already is.
3. Everything already named as genuinely next before this phase (below)
   is unchanged — this mission was documentation-only by explicit
   instruction and touched no source.

## Closed prior phase: Capital Allocation Intelligence

See `CURRENT_MISSION.md`'s "Capital Allocation Intelligence" entry and
`docs/PHASE_STATUS.md`'s matching section (including the mission's own
Mandatory Final Review). **Genuinely next now**, in priority order:

1. **TD-62**: extend `Portfolio.tsx` with the same `CapitalAllocationPlan`
   view CIO Desk now renders (or a shared component) — it already calls
   `postDecisions()` with the exact request `postCapitalAllocation()`
   needs; deliberately not done in this pass since CIO Desk was the
   mission's explicit target and a rushed second layout risked being
   inconsistent with the considered one just built.
2. **Real, populated capital-allocation numbers stay honestly zero** until
   a real, licensed EGX vendor exists and the publication gate actually
   clears — same root-cause caveat as every other mission's output
   (`docs/ROADMAP.md`). Once real data flows, re-verify the live queue/
   recycling/opportunity-cost views against a genuinely non-empty plan
   (this mission could only prove that path via engine-level tests and a
   component-level rendering test with a realistic fixture, not a live
   screenshot, since fabricating one would require inventing "live EGX
   data" evidence the gate correctly withholds).
3. Consider whether the position-unaware CIO Desk fallback (no holdings
   entered) should ever get its own, more limited ranking view (e.g.
   showing the model portfolio's own already-ranked positions with
   explicit rank numbers) rather than the current plain list — a real UX
   question, not started here since the mission's ranking/opportunity-
   cost/recycling concepts fundamentally require real capital to mean
   anything.
4. Re-run `agx allocate-capital`/`agx validate-investment`/`agx
   investment-proof` after any future change to `meta.decision_engine`/
   `decision_service`/`portfolio.constructor` — the fastest way to catch
   a regression in the properties each framework already proved, not
   just a one-time report.
5. Everything already named as genuinely next before this phase (below)
   is unchanged.

## Closed prior phase: EGX-Genom Final Product Mission (Institutional Investment Operating System)

See `CURRENT_MISSION.md`'s "EGX-Genom Final Product Mission" entry and
`docs/PHASE_STATUS.md`'s matching section. **Genuinely next now**, in
priority order:

1. **`InvestmentProofDashboard`** — unchanged from the Investment Proof
   Framework mission below: still CLI-only. Now more clearly in scope
   given the IOS mission's page conventions — likely a Research-hub
   sub-view or a Settings sub-view rather than a new top-level nav item,
   since a Capital Trust Report is an internal-capability artifact, not a
   daily-decision one (same Product Law reasoning that kept it off CIO
   Desk).
2. **TD-61**: `getRuntimeStatus()`/`getSourceTruth()`/
   `getEndpointCandidates()` remain unused by any page. Named, not
   force-built — wire in only if a real maintainer need (e.g. a
   data-quality incident review flow) justifies a System & Operations
   sub-view on Settings.
3. **Decision Center's `DECISION_DATA_DIR` wiring is still real but
   manual** (unchanged from the Market Regime mission's own note, now
   applying to Portfolio instead) — works today only against a local/
   self-hosted `api/` with the env var set; no automation points a
   deployed `api/` instance at production data yet (System 18's
   deployment/scheduling business-blocker, unchanged).
4. Everything already named as genuinely next before this phase (below,
   TD-59/TD-60/confidence-calibration/walk-forward-backtesting/etc.) is
   unchanged — this mission was a product/UX redesign layered on top of
   the existing decision engine, not a change to any of those
   still-open items.
5. Re-verify the live browser walkthrough (Playwright, both EN and AR)
   after any future CIO Desk/Portfolio/Investment Case CSS or layout
   change — this mission's own RTL table-overflow bug (inline `<span>`
   `max-width` silently doing nothing) is the concrete class of defect
   that only a real rendered check catches, not `tsc`/vitest alone.

## Closed prior phase: Investment Proof Framework (Capital Trust Report)

See `CURRENT_MISSION.md`'s "Investment Proof Framework" entry and
`docs/PHASE_STATUS.md`'s matching section. **Genuinely next now**, in
priority order:

1. **`InvestmentProofDashboard`** — the mission's 10th named deliverable
   exists today only as `agx investment-proof`'s JSON/Markdown CLI output.
   A real `api`/`web` surface needs a `CapitalTrustReport` export through
   `agx_research.dashboard.export` plus a matching `api` route, following
   the same convention every other dashboard artifact already uses (see
   `docs/ARCHITECTURE.md`'s "Dashboard data providers" section) — not a
   one-off fetch wired into a component.
2. **TD-59** (fixed, but its wider implication is not): the same
   `max_position_pct`/publication-gate defect pattern that hit
   `DecisionService.decide_portfolio()` is worth a targeted audit of every
   other caller of `MetaDecisionEngine.decide()`'s output to confirm none
   of them silently skip `apply_publication_gate()` either.
3. **TD-60**: once `DecisionRecord` (or a linked artifact) carries
   per-category attribution at record time, `CommitteeValidationEngine`
   can compute real `historical_usefulness` correlations instead of
   `ready_for_data` — a real schema change, deliberately not made
   unilaterally mid-framework.
4. **Confidence calibration and walk-forward backtesting** stay `BLOCKED`
   until real, licensed EGX history exists — both `ConfidenceCalibrationFramework`
   and `WalkForwardInfrastructure` are architecturally complete and will
   produce real numbers with zero code change the moment that data exists.
5. Re-run `agx investment-proof` after any future change to
   `meta.decision_engine`/`decision_service`/`portfolio.constructor`/
   `horizons.knowledge_weighted` — like `validate-investment`, it's the
   fastest way to catch a regression in the properties this mission
   proved, not just a one-time report.
6. Everything already named as genuinely next before this phase (below) is
   unchanged.

## Closed prior phase: Institutional Investment Validation framework

See `CURRENT_MISSION.md`'s "Institutional Investment Validation" entry and
`docs/PHASE_STATUS.md`'s matching section. **Genuinely next now**, in
priority order:

1. **TD-57**: design and wire `ContinuousLearningMonitor`'s cadence into
   `production.pipeline.ProductionPipeline` — proven correct by the
   validation framework, but never autonomously invoked today.
2. **TD-58**: once a real EGX30 index-level price series is legally
   obtainable (same root cause as the broader Price Data wall,
   `docs/ACQUISITION_STRATEGY.md`), benchmark-evaluated decisions become
   possible with zero code change — the math is already proven correct.
3. **Q9's named limitation**: day-over-day `Recommendation` diffing needs
   a real architectural decision (a new versioned store for an entity
   that's deliberately ephemeral today) this validation mission
   deliberately did not make unilaterally.
4. Re-run `agx validate-investment` after any future change to
   `meta.decision_engine`/`decision_service`/`portfolio.constructor` — it
   is the fastest way to catch a regression in the properties this mission
   proved, not just a one-time report.
5. Everything already named as genuinely next before this phase (below) is
   unchanged.

## Closed prior phase: Market Regime classification

See `CURRENT_MISSION.md`'s "Market Regime classification" entry and
`docs/PHASE_STATUS.md`'s matching section. **Genuinely next now**, in
priority order:

1. **Historical-analog comparison** — Market Intelligence's card was
   "Market Regime & Historical Comparison"; only the regime half is closed.
   Genuinely blocked on years of real trading history (System 12's
   `HistoricalReviewer`, unchanged status) — not a code gap to force.
2. **Decision Center's `DECISION_DATA_DIR` wiring is real but manual** —
   works today only against a local/self-hosted `api/` with the env var
   set to a directory a real `agx run` produced; no automation points a
   deployed `api/` instance at production data yet (System 18's
   deployment/scheduling business-blocker, unchanged).
3. **TD-56's calibration trigger**: once real decision-ledger/regime
   history accumulates, review whether ±3% cumulative return and 1.5%/2.5%
   daily volatility are the thresholds that actually separate a genuine
   trend/volatility shift from routine noise.
4. Everything already named as genuinely next before this phase (below) is
   unchanged.

## Closed prior phase: decision object completeness + live Decision Center

See `CURRENT_MISSION.md`'s "complete the 12-field decision object; wire it
to the web" entry and `docs/PHASE_STATUS.md`'s matching section.

## Closed prior phase: the real DATA_COLLECTION-starvation bug and dead-source retirement

See `CURRENT_MISSION.md`'s "fix why no investment decision was ever
reachable" entry and `docs/PHASE_STATUS.md`'s matching section for full
detail. **Genuinely next now**, in priority order:

1. **Watch the next scheduled `deploy-pages.yml` run** (or trigger one
   manually) — the real, first-ever test of whether `LIVE_PRICE_LOOKBACK_DAYS`
   produces a promoted `KnowledgeObject` end to end in an actual live run,
   not just against a locally re-run copy of already-persisted data. This
   is the single most important thing to verify next; everything else on
   this list is secondary until that's confirmed.
2. **TD-53's calibration trigger**: once real decision-ledger history
   accumulates across enough trading days, review whether 180 days is the
   right shared window, and whether per-horizon windows (a shorter one
   for MICRO momentum, a longer one for INVESTMENT correlation) would
   separate signal from noise better than one number for all of them.
3. **TD-54's flagging extension**: if a future source review finds a
   still-catalogued source silently orphaned from every capability's
   candidate pool (unlike `fred`, which is deliberately kept), consider
   whether `retire_removed` should flag it for a maintainer rather than
   requiring a manual catalog deletion first.
4. Everything already named as genuinely next before this phase (below)
   is unchanged — this phase's fixes didn't touch acquisition
   architecture, calibration of the pre-existing declared thresholds
   (TD-44/45/46/51/52), or the sovereign-rating/Amwal-Al-Ghad items.

---

## Closed prior phase: Market Breadth artifact

Item 4 from the list below is now closed — see `CURRENT_MISSION.md`'s
"Market Breadth artifact" entry and `docs/PHASE_STATUS.md`'s matching
section. **Genuinely next now**, from the same list, all still gated on
external evidence or a business decision this codebase's own rules forbid
guessing around:

1. **Connect a real `SovereignRatingAction` collector** (TD-48) once
   `moodys_ratings`/`sp_global_ratings`/`fitch_ratings` verify a real feed
   and go `IMPLEMENTED` — until then, `CountryRiskSeverity.CRISIS` stays
   honestly unreachable.
2. **Calibration pass** (TD-44/45/46/51/52) once real decision-ledger
   history exists (≥30 evaluated decisions per horizon) — every declared,
   uncalibrated threshold in this codebase (including the new
   `TRAILING_VOLUME_WINDOW_DAYS`) shares this same repayment trigger.
3. **Amwal Al Ghad + IDSC/rating-agency `TargetOrganization` candidates'
   next real `agx discover-sources` run** — needs real network egress, the
   same evidenced blocker every prior acquisition mission has hit.

Explicitly not next: a new source-discovery sprint, any rewrite of
`MetaDecisionEngine`/`PortfolioConstructor`/the publication gate, or
reopening the 31-row evidence-weight table the Adversarial Review
explicitly rejected coding — none of that changed with this phase.

## Genuinely next, after the Decision-Centric Redesign implementation (2026-07-30)

The six research/architecture documents' roadmap
(`docs/DECISION_CENTRIC_AUDIT_2026-07-30.md` →
`docs/FREE_DECISION_DATA_BLUEPRINT.md` → `docs/DECISION_EVIDENCE_MATRIX.md`
→ `docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md`) is now implemented — see
`docs/PHASE_STATUS.md`'s "Decision-Centric Redesign implementation"
section and `docs/MISSION_COMPLETION_REVIEW.md`. What's genuinely next:

1. ~~Wire `decision_service.DecisionService` into a queryable command~~
   **Closed** (TD-47): `agx decide --date ... [--positions positions.json]`.
2. **Connect a real `SovereignRatingAction` collector** once
   `moodys_ratings`/`sp_global_ratings`/`fitch_ratings` verify a real
   feed and go `IMPLEMENTED` (TD-48) — until then,
   `CountryRiskSeverity.CRISIS` is honestly unreachable by design, not a
   bug; do not lower that bar to make the override "do something" before
   real evidence exists.
3. **Calibration pass** once real history exists (TD-44/45/46, new this
   phase): `FinancialPerformanceAgent`'s growth/leverage shift thresholds,
   `assess_country_risk`'s currency-deterioration threshold, and the
   liquidity floor are all declared, not measured — same posture as
   TD-6/17/20/33, and the same repayment trigger (real decision-ledger
   history, ≥30 evaluated decisions per horizon).
4. ~~Market Breadth artifact~~ **Closed**: `market_memory.breadth.compute_market_breadth()`
   → `market_breadth.json`, wired through `api`/`web` into Market
   Intelligence's breadth card. See `CURRENT_MISSION.md`'s "Market Breadth
   artifact" entry.
5. **Amwal Al Ghad + IDSC/rating-agency `TargetOrganization` candidates'
   next real `agx discover-sources` run** — the identity-only entries are
   seeded; only a real network-egress run can confirm reachability, the
   same evidenced blocker every prior acquisition mission has hit.

Explicitly not next: a new source-discovery sprint (still true — the
original audit found the existing catalog already covers the credible
free/legal universe), any rewrite of `MetaDecisionEngine`/
`PortfolioConstructor`/the publication gate (the Decision Service is
additive, composed on top, not a replacement), or reopening the 31-row
evidence-weight table the Adversarial Review explicitly rejected coding.

---

## Closed this phase: TD-39 EGX30+EGX70 Financial Source Registry

See `CURRENT_MISSION.md`'s "TD-39" entry and `docs/TECHNICAL_DEBT.md`'s
matching row. The registry mechanism, classifier, and CI wiring are done
and tested; the actual per-company data is not, because no company's
homepage could be reached from this sandbox. **Genuinely next now**:

1. **A real `.github/workflows/discovery.yml` run with network egress**
   (next scheduled Monday, or `workflow_dispatch` now) — the single
   blocking step for everything else in this list. Confirms how many of
   the 26 `BLOCKED` EGX30 companies move to `DISCOVERED`, and is the only
   way any company can honestly reach `VALIDATED`.
2. **Calibrate `classify_financial_document()`'s keyword lists** once real
   IR-page anchor text/URLs exist to check them against (currently an
   uncalibrated starting heuristic, same posture as TD-28/TD-29).
3. **Extend `egx30_web_search_domain_hints.json` to EGX70** (TD-38's own
   next item — unblocks `HOMEPAGE_UNRESOLVED` for 70 of the 75 companies
   currently stuck there).
4. **Financial metric availability / automation capability fields**
   requested alongside the registry are represented in the schema
   (`CompanyFinancialSourceRecord.robots_allowed`, per-document
   `source_type`/`collector_recommendation`) but a *metric-level*
   breakdown (which of revenue/EPS/assets/... a given statement actually
   contains) needs a real fetched financial-statement document to inspect
   — same "can't invent it, needs a real document" constraint as
   everything else on this list, deferred until item 1 produces one.

None of these are engineering tasks this session can advance further
without either real network egress or a document item 1 produces.

## Closed prior phase: TD-38 EGX30 company domain-hint coverage

See `CURRENT_MISSION.md`'s "TD-38" entry and `docs/TECHNICAL_DEBT.md`'s
matching row for full detail. **Genuinely next now** for this specific
line of work, in priority order:

1. **A real `agx discover-sources` run with network egress** (e.g. inside
   `.github/workflows/discovery.yml`'s environment, or any environment
   this sandbox's egress policy doesn't block) — confirms how many of the
   26 hinted hostnames actually resolve/qualify, and is the only way to
   move any of them from `domain_hints` to an actual registered,
   `QUARANTINE`-stage `SourceSpec`. Nothing further can be verified from
   inside this session (see TD-38's evidenced egress-block detail).
2. **Extend `egx30_web_search_domain_hints.json` to EGX70** — this pass
   deliberately scoped to EGX30 only (CLAUDE.md's stated primary focus)
   given the size of a full EGX70 web-search pass; the same
   `load_web_search_domain_hints()` mechanism already generalizes, only
   the data file needs extending.
3. **Revisit the 5 unresolved EGX30 tickers** (EGCH, HELI, MCQE, OIH,
   PHDC) if a confidently-resolvable official domain turns up later —
   never guess one to fill the gap now.

This does not reopen the broader acquisition freeze (`MISSION_CONTROL.md`):
new source *families* beyond company domain-hint coverage still need a
new named business input.

## Closed prior phase: TD-34 web/API wiring

Item 1 from the "Genuinely next now" list below is now closed — see
`CURRENT_MISSION.md`'s "TD-34" entry and `docs/PHASE_STATUS.md`'s
matching section. This was the last purely-engineering item on the
punch list the project owner's "continue all remaining legal/free
directions" instruction opened; everything genuinely next now waits on
either real accumulated evidence or an external verified source:

1. **Calibrate `agents.news_sentiment.classify_headline_sentiment()`'s
   phrase lists** (TD-35) once a meaningful batch of real live headlines
   accumulates.
2. **Source a verified Arabic-language EGX constituent list** to close
   TD-36 (no fabricated transliteration is an option).
3. **Consult a real publication-schedule source** to replace
   `data.point_in_time`'s declared lag floors with cited, source-specific
   figures (TD-37).
4. **Watch the next scheduled/manual `discovery.yml` run** and the next
   real trading day the production pipeline runs against (both named in
   earlier phases, neither closeable from inside this session).

None of these are engineering tasks this session can advance further
right now without either real accumulated evidence or the project owner
supplying an external input — see each item's own TD entry for its exact
repayment trigger.

## Closed prior phase: Monte Carlo stress simulator

Item 2 from the "Genuinely next now" list below is now closed — see
`CURRENT_MISSION.md`'s "Monte Carlo stress simulator" entry and
`docs/PHASE_STATUS.md`'s matching section.

**Genuinely next now** (in priority order):

1. **`ticker_data_gap_report.json` web/API wiring** (TD-34) — the last
   item on this list that's pure engineering, not waiting on external
   evidence.
2. **Calibrate `agents.news_sentiment.classify_headline_sentiment()`'s
   phrase lists** (TD-35), source a verified Arabic-language EGX
   constituent list (TD-36), and consult a real publication-schedule
   source to replace `data.point_in_time`'s declared lag floors with
   cited figures (TD-37) — all three wait on real accumulated evidence
   or an external source, not more engineering right now.

## Closed prior phase: macro frequency alignment + no-look-ahead discipline

Item 2 from the "Genuinely next now" list below is now closed — see
`CURRENT_MISSION.md`'s "macro frequency alignment + no-look-ahead
discipline" entry and `docs/PHASE_STATUS.md`'s matching section.

**Genuinely next now** (in priority order):

1. **`ticker_data_gap_report.json` web/API wiring** (TD-34).
2. **Monte Carlo stress simulator** (System 10).
3. **Calibrate `agents.news_sentiment.classify_headline_sentiment()`'s
   phrase lists** (TD-35), source a verified Arabic-language EGX
   constituent list (TD-36), and consult a real publication-schedule
   source to replace `data.point_in_time`'s declared lag floors with
   cited figures (TD-37) — all three wait on real accumulated evidence
   or an external source, not more engineering right now.

## Closed prior phase: entity resolution for news-to-ticker matching

Item 1 from the "Genuinely next" list below is now closed — see
`CURRENT_MISSION.md`'s "entity resolution for news-to-ticker matching"
entry and `docs/PHASE_STATUS.md`'s matching section.

**Genuinely next now** (in priority order):

1. **Monte Carlo stress simulator** (System 10).
2. **Macro frequency alignment + no-look-ahead discipline**.
3. **`ticker_data_gap_report.json` web/API wiring** (TD-34).
4. **Calibrate `agents.news_sentiment.classify_headline_sentiment()`'s
   phrase lists** (TD-35) and, separately, source a verified
   Arabic-language EGX constituent list to close TD-36 — both wait on
   real accumulated evidence, not more engineering right now.

## Closed prior phase: NewsIntelligenceAgent

Item 2 from the "Beyond this" list below is now closed — see
`CURRENT_MISSION.md`'s "NewsIntelligenceAgent" entry and
`docs/PHASE_STATUS.md`'s matching section for full evidence. System 08 is
now 6 of 8 agents real.

**Genuinely next, all legal/free and not acquisition-architecture work**
(in the order they'd most directly improve real recommendation quality):

1. **Entity resolution for news** (Arabic + English alias lists per
   EGX30/EGX70 company — legal name, trading name, ticker, ISIN) so a
   headline is matched to the right ticker, not a similarly-named one.
   Directly strengthens `NewsIntelligenceAgent`'s own ticker attribution
   (today: whatever `ticker_hints` a collector happens to be configured
   with) as well as `corporate_event_classifier`'s.
2. **Monte Carlo stress simulator** (System 10) — the one Experiment
   Factory gap that's a design decision, not a data blocker; strengthens
   every hypothesis reaching Stress Testing, including the new News
   findings.
3. **Macro frequency alignment + no-look-ahead discipline** — normalize
   daily/monthly/quarterly/annual series onto a common comparison
   calendar and distinguish `period_end_date` from real publication date,
   closing a real look-ahead-bias risk before more macro series connect.
4. **`ticker_data_gap_report.json` web/API wiring** (TD-34) — route +
   provider + types, following `financial_statements.json`'s pattern.
5. **Calibrate `agents.news_sentiment.classify_headline_sentiment()`'s
   phrase lists** (TD-35) once a meaningful batch of real live headlines
   accumulates.

## Closed prior phase: TargetOrganization entries for 14 of 20 untargeted sources

Item 1 below (partially) and item 3 (fully) from the phase below are now
closed — see `CURRENT_MISSION.md`'s "target the closeable half of
not_targeted" entry for the full evidence and reasoning (grounded in the
first real live discovery run's own `discovery_metrics.json`).

**Genuinely next:**

1. **The remaining 6 untargeted sources** (`github_releases`,
   `company_social_official`, `public_telegram`, `patents`,
   `hiring_signals`, `company_ir`'s per-constituent marker) stay
   untargeted on purpose — each names more than one candidate
   organization or is inherently per-company/per-channel. Needs the
   project owner to name a specific organization/channel/office, or a
   `generate_company_ir_targets`-style per-entity expansion.
2. **Wire `AcquisitionContinuityMonitor.check_and_recover()`** into the
   weekly schedule (TD-23's remaining half).
3. **Watch the next scheduled/manual `discovery.yml` run** with the 14
   new targets wired in — the real test of whether any of them resolve
   to a reachable domain and clear the legality gate.
4. **Enable "Allow GitHub Actions to create and approve pull requests"**
   (Settings → Actions → General) so `discovery.yml`'s own `gh pr create`
   step succeeds unattended — the first live run had to have its PR
   opened manually because this repo setting was off.

## Closed this phase: weekly Discovery workflow

The "dozens of sources stay PLANNED, waiting on network egress" item from
the phase below is now closed, not deferred: `.github/workflows/discovery.yml`
runs `agx discover-planned-report` weekly against every in-scope
`PLANNED`/`CANDIDATE` source, entirely separate from the production
deploy, landing evidence via a reviewed PR (never a direct commit, never
an automatic status flip). See `CURRENT_MISSION.md`'s "weekly Discovery
workflow" entry and `docs/DATA_ACQUISITION.md`'s "Discovery workflow"
section.

**Genuinely next, once real scheduled runs accumulate evidence:**

1. **Add `TargetOrganization` entries for the 20 catalogued `PLANNED`
   sources with none yet** (`mof_egypt`, `egypt_open_data`, `investing_com`,
   `tradingview`, `imf`, `oecd`, `suez_canal_stats`, `wikipedia_pageviews`,
   `google_trends`, `github_releases`, `company_social_official`,
   `public_telegram`, `patents`, `hiring_signals`, `arxiv`, `ssrn`, `nber`,
   `google_scholar`, `researchgate`, plus `yahoo_finance`/`stockanalysis`
   which are intentionally excluded as provider legs, not gaps). Each
   needs a real, publicly-known domain hint researched per organization —
   a genuine per-source decision, not something to batch-guess.
2. **Wire `AcquisitionContinuityMonitor.check_and_recover()` into the same
   weekly schedule** (TD-23's remaining half) so a source that went `DOWN`
   also gets proactive alternative-method discovery, not just the
   PLANNED-source verification the current workflow covers.
3. **Watch the first real scheduled/`workflow_dispatch` run** on GitHub
   Actions (this session cannot verify it directly — no egress here) and
   review whatever PR it opens against `main`.

## Closed this phase: provider-leg health measurement accuracy

The project owner's source-dashboard review named one genuinely
closeable engineering gap (provider legs inside a composite collector
never had their own health/reputation measured — see `CURRENT_MISSION.md`
and `docs/PHASE_STATUS.md`'s "Provider-Leg Health Measurement Accuracy"
section) — closed this phase. The review's other three points remain
correctly business/infrastructure-blocked, not code gaps, and are named
here explicitly so the project owner can act on them directly rather than
have this codebase guess or fabricate around them:

- **Dozens of sources stay `PLANNED`** until a verified real endpoint
  exists for each (this dev sandbox has no arbitrary outbound egress;
  the GitHub Actions production deployment does — see
  `CURRENT_MISSION.md`'s "Superseded six times" note). Converting one to
  `IMPLEMENTED` is real, source-by-source acquisition work the standing
  freeze (below) explicitly defers pending a new named business input.
- **`NEEDS_KEY` sources (FMP, AlphaVantage, Polygon, Tiingo)** — the
  project owner reviewed this and decided against it explicitly: the
  platform is scoped to genuinely free, no-registration sources only, so
  waiting on a key serves no goal. All four catalog entries and the two
  collector classes (`AlphaVantageCollector`, `FmpCollector`) plus their
  tests were removed this phase — see `docs/DATA_ACQUISITION.md`'s "No
  API-key sources" section. This is now closed, not deferred.
- **No scheduled recurring discovery/collection run** exists yet because
  it needs System 18's managed-scheduling decision (cloud target +
  secrets + scheduler) — named in `docs/ROADMAP.md` and TD-23's own
  repayment trigger ("System-18 scheduling exists → wire a periodic
  full-catalog `agx discover-sources` pass"). `AcquisitionContinuityMonitor`
  already re-runs discovery reactively on a `DOWN` health signal; only the
  *proactive periodic* pass awaits real deployment scheduling.

## Immediately next: from the project owner's data-sources completion plan

The project owner's latest plan (see `CURRENT_MISSION.md`'s "Ticker Data
Gap Report" entry) named two real, scoped engineering tasks this phase
deliberately left for next, having closed the gap-report item first:

1. **Entity resolution for news** (plan item 4): build Arabic + English
   alias lists per EGX30/EGX70 company (legal name, trading name, ticker,
   ISIN) so a headline mentioning a company is matched to the right
   ticker and not a similarly-named one (the plan's own example: VLMR vs.
   VLMRA). Today, ticker matching is whatever hint list a collector was
   configured with (`RssNewsCollector`'s `ticker_hints`) — there is no
   shared alias registry a news/disclosure classifier consults. Success
   criterion per the plan: every news item lands on the correct ticker,
   raising real news/event coverage.
2. **Macro frequency alignment + no-look-ahead discipline** (plan item
   5): `agents/macro.py` already correlates macro series against ticker
   returns, but nothing yet normalizes daily/monthly/quarterly/annual
   series onto a common comparison calendar, and nothing yet distinguishes
   a macro/financial value's `period_end_date` from its real publication
   date (the plan's explicit warning: a quarter's results can't be used
   as of the quarter's end if they weren't actually announced until weeks
   later). This is a real look-ahead-bias risk worth closing before more
   macro series are connected, independent of any new data source.
3. **Web/API wiring for `ticker_data_gap_report.json`** (TD-34): route +
   provider + types, following `financial_statements.json`'s exact
   existing pattern, then a dashboard UI surface (likely an addition to
   Opportunity Center or a new "Data Coverage" view) once the artifact
   itself has been reviewed.

None of these require a new `TargetOrganization`, collector, or
source-discovery change — the freeze below still applies to acquisition
architecture specifically.

---

**Acquisition architecture is frozen as of this commit** (see
`CURRENT_MISSION.md` and `docs/ACQUISITION_STRATEGY.md`'s "Final Data
Acquisition Sprint" section). Every mission from here forward must
increase AGX's ability to **generate, validate, rank, and explain**
investment decisions from the evidence already connected (World Bank,
Enterprise, FRA) — not collect additional data. Grounded in
`docs/PHASE_STATUS.md`'s per-system audit (all 18 charter systems
architecturally DONE), here is what that actually means, in priority
order:

## 1. ~~Monte Carlo stress simulator (System 10, Experiment Factory)~~ — Closed

See the "Closed this phase" section at the top of this document and
`docs/PHASE_STATUS.md`'s "Monte Carlo stress simulator" section — block
bootstrap over real observed returns was the methodology chosen, matching
`HistoricalWorstWindowStressTester`'s exact philosophy.

## 2. ~~NewsIntelligenceAgent (System 08, Scientist Framework)~~ — Closed

See the "Closed this phase" section at the top of this document and
`docs/PHASE_STATUS.md`'s "NewsIntelligenceAgent" section.

## 3. Verify the pipeline against the next real trading day

Not new engineering — an operational checkpoint. Every real event
registered so far (`fra_egypt`'s 10 disclosures, `enterprise_press`'s 6
news items) landed on non-trading days, so the research pipeline
correctly produced zero hypotheses from them (an honest calendar gap,
not a strategy failure — see `MISSION_CONTROL.md`). The next scheduled
live run that lands on a real trading day is the first real test of
whether the full Observation → Hypothesis → ... → Promotion lifecycle
produces anything from genuinely live evidence. Watch it; don't force it.

## 4. Still correctly data-blocked — do not force these

Per `docs/PHASE_STATUS.md`, these remain honest gaps until enough real
history exists, not because the engineering is missing:

- **`HistoricalReviewer`** (System 12) — needs a historical-analog
  database; there isn't enough real trading history yet to build one
  without fabricating analogs.
- **`FinancialPerformanceAgent`** (System 08) — needs a real fundamentals
  feed, which is itself gated on the same business decisions
  `MISSION_CONTROL.md`'s "Known blockers" names (verified constituent
  list, licensed vendor) — not a new acquisition target to chase.
- **`HistoricalPatternsAgent`** (System 08) — needs years of real price
  history; genuinely blocked on the same Price Data wall
  `docs/ACQUISITION_STRATEGY.md`'s "Price Data Feasibility Mission"
  documents in full.
- **Trained prediction models** (System 14) — explicitly deferred until
  years of real data exist, "otherwise fabricated science" per the
  system's own DONE-with-caveat status.

Do not chase a new data source to unblock these — that would violate this
sprint's freeze. They unblock themselves once real history accumulates
from the sources already connected, or once the project owner clears a
named business blocker.

## 5. Known frontend gaps waiting on new backend artifacts

Still open, still honest "not yet available" states rather than
fabricated content (per `CLAUDE.md`'s anti-fabrication principle) — worth
closing once the artifact they depend on exists, but none of them require
new data collection:

- ~~**Market Regime classification** (Market Intelligence)~~ **Closed**:
  `market_memory.regime.compute_market_regime()` → `market_regime.json`,
  wired through `api`/`web` into a landing-page banner and Market
  Intelligence's card. See `CURRENT_MISSION.md`'s "Market Regime
  classification" entry. Company Research Workspace's own per-ticker
  regime/macro-exposure view is still open (a different, per-ticker
  question this market-wide artifact doesn't answer).
- ~~**Market Breadth & Liquidity** (Market Intelligence)~~ **Closed**
  (prior phase): `market_memory.breadth.compute_market_breadth()` →
  `market_breadth.json`, wired through `api`/`web`.
- **Review Board decision history** (Research Center) — no repository
  persists past `BoardDecision`s yet.
- ~~**Discovery Engine detail** (Mission Control) — `acquisition_intelligence`
  has no dashboard export yet~~ **Closed**: the weekly Discovery
  workflow's `discovery_report.json`/`discovery_metrics.json`/
  `endpoint_candidates.json` are now wired into Mission Control's "Weekly
  Discovery" section and Source Intelligence's "Discovery Evidence"
  block — see `CURRENT_MISSION.md`'s "surface already-computed data"
  entry. Renders an honest empty state until the first scheduled run's PR
  merges.
- **Raw log lines** (System Administration) — no artifact carries them
  yet.

## Beyond this

Every other named technical debt item in `docs/TECHNICAL_DEBT.md` that
touches acquisition/discovery/collectors is now dormant by design (frozen
architecture) unless a named business input clears its trigger. Debt
items touching validation/genome/explainability/review calibration (TD-6,
TD-17) remain open the same way items 4 above are — waiting on real run
history, not new engineering. Future missions should come from this list,
a genuine gap the project owner surfaces, or what item 3's real-trading-
day checkpoint reveals — never from re-opening acquisition work.
