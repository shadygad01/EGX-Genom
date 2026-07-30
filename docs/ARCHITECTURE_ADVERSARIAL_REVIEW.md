# Architecture Adversarial Review — EGX-Genom Decision Redesign

**Status: research only. No production code changed. This document's job
is to find reasons the prior three documents
(`docs/FREE_DECISION_DATA_BLUEPRINT.md`, `docs/DECISION_CENTRIC_AUDIT_2026-07-30.md`,
`docs/DECISION_EVIDENCE_MATRIX.md`) are wrong, not to defend them. Where a
finding below survives its own scrutiny, it is stated as a change, not a
caveat.**

## How this review was conducted

Every major decision across the three prior documents was re-opened and
attacked on ten axes: why it could be wrong, what it assumes, what free
data could invalidate it, what unnecessary complexity it carries, what's
still missing, what could merge, what could be removed, what should be
promoted, and its highest implementation and maintenance risk. The ten
areas the project owner named explicitly (evidence weighting, confidence
model, mandatory gates, sovereign override, external-sector/FX layer,
position-aware taxonomy, peer comparison, layer ordering, agent
boundaries, pipeline boundaries) are each their own section below.
Several findings here reverse or demote decisions the prior documents
made — that is the point of this pass, not a failure of it.

---

## Part 1 — Architecture Weakness Report

### 1.1 Evidence weighting (Evidence Matrix Parts 1–2)

**Why it could be wrong.** Every Critical/High/Medium/Low label in the
Evidence Matrix is a declared judgment call, assigned by reasoning about
plausible importance — not measured against any realized outcome. That
is precisely the "declared, not measured" pattern the codebase's own
technical-debt register already names as acceptable-*only when
explicitly flagged as such* (TD-6, TD-17, TD-33) — and the Evidence
Matrix does not flag itself that way. A qualitative label reads as more
authoritative than an unlabeled guess, which makes this **more**
dangerous than having no weights at all, not less.

**Assumptions it depends on.** (1) That decision weight is stable across
market regimes — Q6 (trading behavior) plausibly matters far more in a
momentum-driven tape than a trendless one, yet carries one static weight.
(2) That decision weight is ticker-agnostic — Q3's FX-debt exposure
obviously matters more for an importer than a domestically-funded
consumer-staples name, yet only one row in the entire matrix
acknowledges sector-conditional weight at all.

**What free data might invalidate it.** The platform's own
`DecisionLedger`/`DecisionPerformanceSummary` machinery (already built,
already tested) is the correct falsification tool — once ≥30 evaluated
decisions per horizon exist, realized excess returns can be checked
against which questions' evidence actually predicted outcomes. **Today,
that sample does not exist**, which means every weight in the Evidence
Matrix is currently unfalsifiable. Building a scoring formula around
unfalsifiable weights is building on sand.

**Unnecessary complexity.** Thirty-one evidence rows, each independently
labeled, is a large surface for a decision the existing codebase
currently computes with one transparent formula
(`confidence × expected_return / risk`). The Matrix never specifies the
actual arithmetic that would turn "Critical/High/Medium/Low" into a
number — it reads as rigorous but does not yet cash out into anything
computable.

**What's missing.** A stated numeric mapping (what does "Critical" equal,
concretely, relative to "High"?) — without one, whoever implements this
must invent arbitrary numbers, and those numbers become unreviewed,
undocumented decisions baked silently into the system.

**What could be merged.** Q1 (valuation) and Q7 (peer comparison) are the
same statistical operation — a multiple — applied to two different
reference distributions (own history vs. peer set), not two independent
questions. PMI/sector-output data is currently double-booked under both
Q5 and Q7, risking silent double-counting in any weighted sum.

**What could be removed.** The double-booked PMI row under Q7 — keep it
under Q5 (macro) only.

**What should be promoted.** Liquidity (currently folded into Q6 as
"High" weight) deserves override-class treatment, not a weighted vote —
see 1.4 and 1.6.

**Highest implementation risk.** Implementing 31 hand-assigned weights as
an ad hoc point total produces a black-box-feeling score that is
arguably *less* defensible than the existing single transparent formula
it would replace.

**Highest maintenance risk.** Every future capability added or removed
now also requires editing this weight table, with nothing enforcing that
the table and the running code stay in sync — the same class of drift
`docs/PHASE_STATUS.md`'s own history has repeatedly had to correct after
the fact.

### 1.2 Confidence model (Evidence Matrix Part 1's Q10, Part 3.3)

**Why it could be wrong.** Four factors (corroboration, freshness,
calibration, sample size) multiplied together crash toward zero fast: even
at a generous 0.9 each, four factors compound to ≈0.66; applied honestly
against this platform's actual current data maturity (several factors
realistically well below 0.9 today), the model could produce a
near-permanent Abstain for nearly every ticker for a long time. That may
be the *intended* conservatism — or it may be a design flaw that makes
the system non-functional in practice for years. The Matrix asserts the
former without checking whether it's actually the latter.

**Assumptions it depends on.** That the four factors are independent, so
multiplying them is statistically meaningful. They are not: a source with
an uncalibrated heuristic classifier (calibration factor low) is also
likely to lack a second, corroborating source (corroboration factor also
low), because nobody has built a cross-check for exactly the sources
whose heuristics are weakest. Multiplying correlated weaknesses
double-penalizes the same underlying problem.

**What free data might invalidate it.** The same `DecisionLedger`
evidence named in 1.1 — whether lower computed confidence scores actually
correlate with worse realized outcomes is untested and currently
untestable at this sample size.

**Unnecessary complexity.** A simpler, fully discrete gate set (already
built: `meta.readiness.assess_decision_readiness`'s period/observation/
series floors) is more auditable than a continuous multiplicative score
nobody can intuit by eye, for probably the same practical effect.

**What could be merged.** The Evidence Matrix's own mandatory-evidence
gate (Part 3.1) and the Q10 multiplier are two independent mechanisms
both answering "should we trust this decision yet?" — layering a
continuous discount on top of a hard gate doubles the ways a ticker can
be wrongly suppressed (or wrongly not suppressed) if the two disagree.

**Highest implementation risk.** No document specifies the actual numeric
values ("degraded confidence" = 0.7? 0.5?) — another unreviewed
arbitrary-number risk, structurally identical to 1.1's.

**Highest maintenance risk.** A multiplicative model with room for future
factors is a one-directional ratchet: every well-intentioned new
confidence factor added later shrinks the achievable maximum further,
with no built-in re-normalization — the system could get monotonically
more conservative over time as a side effect of "improving" confidence,
silently degrading decision coverage.

### 1.3 Mandatory evidence gates (Evidence Matrix Part 3.1)

**Why it could be wrong.** A binary pass/fail gate treats a ticker
missing exactly one mandatory row (say, a free-float figure stale by a
few weeks) identically to a ticker with zero data of any kind. That is
false precision at the boundary — the same criticism cliff-edge
risk-model cutoffs generally get, and the specific period/series
thresholds behind it were never independently derived here; they're
inherited from the existing codebase's own admittedly uncalibrated
floors (TD-17).

**Assumptions it depends on.** That "insufficient evidence → don't
decide" is always the safe default. For a long-term investor who already
holds a position, an inability to refresh one input shouldn't
automatically force Hold — a stated, lower-confidence Reduce might
be more correct than silently doing nothing, since inaction is itself a
decision with real consequences.

**What could be merged/removed.** This review's single most important
structural finding here: **building this as a second, independent gate
system is itself the primary risk.** The platform already has
`meta.readiness`'s gate mechanism; a second, separately-maintained
mandatory-evidence gate in the Evidence Matrix is exactly the kind of
"two systems that could silently disagree" the codebase's own
`build_ticker_data_gap_report` docstring explicitly warns against
elsewhere. **Do not build a parallel gate — extend the existing one.**

**Highest implementation/maintenance risk.** Precisely that duplication,
if built as designed in the Evidence Matrix rather than merged into the
existing mechanism.

### 1.4 Sovereign override (Evidence Matrix Part 3.2, Q9)

**Why it could be wrong.** Rating actions are famously *lagging*, not
predictive, in sovereign-debt literature — by the time an agency
announces a downgrade, markets have typically already priced in much of
the move. An override that fires on the rating action itself may sell
*after* most of the damage, giving a false sense of protection while
actually lagging the real risk it claims to guard against.

**Assumptions it depends on.** That a rating action is a clean,
unambiguous trigger. In practice agencies split (one downgrades, another
affirms), and "outlook negative" carries very different severity than an
actual downgrade — the binary "triggered/not triggered" framing loses
this entirely, and no document ever specified the actual numeric/ordinal
threshold for "past a declared critical threshold." That phrase is a
placeholder, not a specification.

**What free data might invalidate it.** The Blueprint's own Part 2
already concedes the most genuinely predictive free-adjacent signal for
an Egyptian currency crisis specifically — a parallel/forward FX
market rate — **does not exist for free**. The override is built on the
best available free evidence (lagging rating actions), which the
Blueprint itself already flagged as second-best. That tension deserves to
be stated loudly, not built around quietly.

**Unnecessary complexity.** A wholly separate short-circuit code path for
one question, when every other question shares one combination
mechanism, is an asymmetry that doubles the combination logic that must
be tested and kept correct.

**What could be merged.** Same finding as 1.1: Q5 (macro/FX) and Q9
(sovereign risk) overlap heavily — a reserve drawdown is simultaneously a
Q5 signal and a leading indicator of a future Q9 rating action. Treating
them as one graduated "Country & Macro Risk" axis with an internal
severity ladder (normal → deteriorating → crisis) is more honest than
maintaining an artificial hard boundary between "feeds in normally" and
"can override everything."

**Highest implementation risk.** A wrong override in either direction has
portfolio-wide blast radius, larger than any single-ticker mistake
elsewhere in this design: a false trigger forces unnecessary Exits (real
transaction costs) across an entire book; a missed trigger (a real crisis
that doesn't match the declared rule — e.g. a currency float with no
preceding formal rating action) means the one mechanism built specifically
to catch catastrophic risk fails exactly when most needed. This is the
single highest-blast-radius component in the whole design.

**Highest maintenance risk.** An unspecified "critical threshold" is a
landmine: whoever implements this will invent a specific numeric rule
with no citation or validation behind it, and it will look authoritative
in code despite being an arbitrary implementation detail.

### 1.5 External-Sector / FX layer (Blueprint Part 1.7, Evidence Matrix Q5, prior reconciliation)

**Why it could be wrong.** The prior reconciliation (Evidence Matrix Part
4, finding 2) elevated Suez Canal/tourism/remittance data to a near-term
roadmap item largely by narrative argument — "Egypt's risk premium is
FX-dominated" — not by any measured correlation between these specific
feeds and EGX returns. That is an assumption dressed as a finding, and
this review names it as exactly that: **unvalidated.**

**Assumptions it depends on.** That monthly, backward-looking statistics
are decision-useful for a forward-looking thesis. By the time these
publish, faster-moving proxies (daily FX spot behavior, global shipping
indices) may have already priced in the same information — meaning this
layer might be structurally too slow to be the leading indicator it was
labeled.

**What could be merged/removed.** Suez Canal receipts, tourism revenue,
and remittances are literally line items that sum into CBE's own
current-account/balance-of-payments reporting. Collecting all three
*separately* may be redundant double-counting of a signal CBE already
reports in aggregate, for three new PDF-scraping targets' worth of
maintenance surface and marginal disaggregation benefit that has never
been shown to be worth the cost.

**Highest implementation risk.** Three brand-new extraction targets, each
needing its own heuristic, committed to a layer whose actual predictive
value has never been tested — a build-before-validate risk, and this
platform's own technical-debt register is already full of "declared
heuristic, uncalibrated" entries from doing exactly this pattern
elsewhere.

**Highest maintenance risk.** Three monthly PDF sources from three
different Egyptian government bodies, none with an attribution-API
guarantee, each liable to change format/URL/schedule without notice —
matching the exact fragility already documented for CBE/CAPMAS
elsewhere in this codebase's debt register, multiplied by three.

**Recommended demotion**: start with CBE's own aggregate reporting only;
treat the three disaggregated feeds as low-priority validation-only
additions pending real evidence they add information CBE's own aggregate
doesn't already carry.

### 1.6 Position-aware decision taxonomy (Evidence Matrix Part 3.4)

**Why it could be wrong.** A single discrete `PositionState` is a
simplification that may not match how a real long-term investor acts:
staged/dollar-cost-averaged entries, multiple cost-basis lots, and
tax-driven hold decisions (a thesis says Exit, but realizing a large
capital gain isn't costless) are all invisible to a six-way label.
"Reduce" also never specifies *by how much*.

**Assumptions it depends on.** That "cap" is a fixed, pre-known number
independent of conviction. In reality, a very high-confidence thesis
plausibly deserves a larger cap than a marginal one — "Increase vs. Hold"
is really an interaction between confidence *and* cap that the six-way
table flattens into a single lookup dimension.

**Unnecessary complexity / wrong primitive.** The six-way action was
designed as the computed *ground truth*, when it might be better
implemented as a **label derived from a continuous target-weight
number** — which the existing `PortfolioConstructor` already computes
via proportional scoring — compared against current weight. A continuous
primitive is strictly more expressive (it naturally answers "how much")
and can still render all six labels for display. Part 3.4's ~18-cell
lookup table is a symptom of building the display format as the
computation, rather than deriving the display format from a computation.

**What's missing.** Every future consideration (tax-lot awareness, staged
entry, confidence-scaled caps) multiplies the lookup table
combinatorially; discrete lookup tables are notoriously prone to silently
missing a cell as dimensions are added later.

**Highest implementation risk.** Retrofitting position awareness onto a
decision engine that has never tracked external state before is a larger
architectural change than "additive, PositionState=None keeps old
behavior" suggests — it is the platform's first genuinely stateful,
externally-dependent decision path, and every consumer of
`Recommendation`/`HorizonDecision` (the ledger, the publication gate, the
portfolio constructor, the dashboard) needs review for whether it
implicitly assumed a position-independent function. This is the largest
actual code-architecture risk in the entire roadmap — bigger than any
single new data source.

**Highest maintenance risk.** The combinatorial lookup-table growth named
above.

### 1.7 Peer comparison design (Evidence Matrix Q7, Part 4 finding 3)

**Why it could be wrong.** It assumes a clean, stable peer set (sector
membership) exists. It does not: `Sector Membership` is a named capability
gap in the Blueprint with exactly one, currently-blocked candidate
(`egx_official`). Building peer-fundamentals replication *before* real
sector-membership data exists means hand-curating peer sets initially —
asserting "these five companies are Company X's peers" with no sourced
taxonomy — which is exactly the kind of fabrication this platform's own
anti-fabrication discipline exists to prevent.

**Assumptions it depends on.** That "peer" means "same broad sector."
Real relative-valuation practice often needs a narrower group (sub-industry,
size, growth profile, ownership structure); a naive same-sector peer set
(a small regional bank vs. a mega-cap universal bank) could produce
actively misleading conclusions — worse than no peer comparison at all.

**Highest implementation risk.** Multiplying financial-statement
extraction across an entire peer set (potentially 5–10× today's
single-ticker extraction effort) when that single-ticker extraction is
*already* flagged uncalibrated (TD-30/31) is the single most expensive
line item in the whole roadmap relative to its unvalidated marginal
value.

**Reversal of the prior document's own recommendation.** The Evidence
Matrix's Part 4 finding 3 *promoted* peer-set fundamentals to its own
scoped roadmap item. On this review's scrutiny, that promotion was
premature: it depends on a foundational capability (Sector Membership)
that doesn't exist, and should instead be **demoted**, explicitly gated
behind that capability actually existing — not merely "scoped as its own
item" while nothing blocks starting it.

### 1.8 Layer ordering (Blueprint Part 5, Layers 0–7)

**Why it could be wrong.** The numbering implies a processing/dependency
order that doesn't actually hold. Layer 6 (Narrative) and Layer 3 (Event)
frequently originate from the *same* disclosure — a single press release
is simultaneously the primary event and its own narrative report,
especially for smaller issuers whose only disclosure channel is a wire
release. The clean separation is an artifact of the write-up, not of how
the data is actually collected.

**A real, previously unresolved inconsistency.** The Blueprint's Layer 7
("Data-Quality/Provenance Meta-Layer") frames data quality as a discrete
pipeline stage sitting logically above/after Layers 0–6. The Evidence
Matrix's Q10 frames the same concept as a **multiplier threaded through**
every other question, not a discrete stage at all. These are two
different mental models for the same concept — a pipeline stage vs. a
cross-cutting concern — and only one can be the actual implementation.
This was never reconciled between the two documents and must be resolved
before any code is written (resolved in Part 3 below).

### 1.9 Agent boundaries (existing 8-agent Scientist Framework vs. the redesign's implied Thesis Components)

**Why it could be wrong.** The redesign's Thesis Components (Valuation,
Growth/Quality, Balance-Sheet Safety, Catalyst/Event, Country-Risk,
Relative Positioning, Governance, Timing/Liquidity) map *almost* but not
cleanly onto the existing 8 agents, and no document ever stated whether
each is meant to extend an existing agent or requires an entirely new
one. That is a skipped design decision, not a resolved one.

**What could be merged.** Valuation, Growth, and Balance-Sheet Safety
(Q1–Q3) all draw on the exact same extracted financial-statement line
items. Maintaining them as three separately-computed "Reads" creates
three places that must independently agree on how to interpret the same
underlying numbers (three chances to disagree on what "declining margin"
means) — a coordination risk a single unified Fundamentals Read, with
three labeled outputs, avoids entirely.

**Highest implementation risk.** Agent-boundary sprawl: going from 8
agents to potentially 9+ independently-maintained components with no
stated rule for when a new "Read" earns its own component versus folding
into an existing one.

### 1.10 Pipeline boundaries (production/orchestration pipeline vs. the new decision function)

**Why it could be wrong.** The daily research pipeline's core, tested
property is determinism — same inputs produce the same output
(`test_production_pipeline.py`'s explicit determinism tests). A
position-aware decision function depends on externally supplied
`PositionState`, which is not part of the research pipeline's
reproducible inputs at all. If `PositionState` is folded into the same
daily pipeline invocation, identical market data on two different days
could correctly produce different decisions because the *portfolio*
changed — correct behavior for a decision engine, but a real risk of
silently violating an existing test's implicit assumption if research
determinism and decision determinism aren't cleanly separated in the
code, not just in prose.

**What's missing.** No document specified whether `PositionState` lives
inside the autonomous daily pipeline run or is queried by a separate,
on-demand service. Given the mission's own rule 4 ("the system must
operate autonomously without user intervention") and the plain fact that
a real portfolio's holdings cannot be autonomously discovered by this
platform, there is a genuine, unresolved tension between "fully
autonomous" and "position-aware" that must be scoped explicitly, not left
implicit.

**Highest implementation risk.** Silently coupling position state into
the deterministic daily pipeline, corrupting the reproducibility
guarantee every existing pipeline test currently relies on.

---

## Part 2 — Recommended Changes

Numbered for direct reference from Part 4's roadmap.

- **R1.** Do not implement the Evidence Matrix's 31-row Critical/High/
  Medium/Low weight table as a coded scoring formula. Until real
  decision-ledger history exists (the platform's own existing acceptance
  standard already requires ≥30 evaluated decisions per horizon before
  trusting *any* edge claim), use the existing simple
  `confidence × expected_return / risk` formula, extended only by the two
  hard overrides in R3/R4 — not a bespoke weight table. Revisit real
  per-question weights only once real outcome data exists to calibrate
  against, and label them "declared, not measured" honestly if adopted
  before then, per this codebase's own established discipline.
- **R2.** Do not build a second, parallel mandatory-evidence gate. Extend
  `meta.readiness.assess_decision_readiness` with exactly two new checks
  (country-risk data presence; a liquidity/tradability floor) rather than
  building the Evidence Matrix's separately-specified gate mechanism.
- **R3.** Merge Q5 (macro/FX) and Q9 (sovereign/country risk) into one
  graduated **Country & Macro Risk** axis with three severity rungs
  (normal / deteriorating / crisis). Implement the "override" as the
  crisis rung's behavior inside the same combination mechanism every
  other question uses — not a separate short-circuit code path.
- **R4.** Add a second, symmetric hard floor for liquidity/tradability
  (from Q6): below it, any positive thesis caps out at "No Action /
  minimal size" — illiquidity is a hard constraint, not merely weighted
  evidence, and deserves the same override-class treatment R3 gives
  country risk.
- **R5.** Do not treat the six-way action as the computed primitive.
  Compute a continuous target-portfolio-weight (extending the existing
  `PortfolioConstructor`'s proportional-scoring approach) and derive
  Buy/Increase/Hold/Reduce/Exit/No Action as **labels** from comparing
  target weight to current weight. This collapses Part 3.4's ~18-cell
  lookup table into one comparison and naturally answers "how much,"
  which the discrete taxonomy never did.
- **R6.** Reverse the prior promotion of peer-set fundamentals (Q7).
  Explicitly gate it behind real Sector Membership data existing (i.e.,
  behind `egx_official` or an equivalent becoming reachable) — do not
  hand-curate peer sets as a stopgap. Demote it to last in the roadmap.
- **R7.** Resolve the Blueprint-vs-Matrix inconsistency on data quality by
  treating it as a cross-cutting multiplier/gate (the Evidence Matrix's
  Q10 framing), not a discrete pipeline layer. The Blueprint's "Layer 7"
  framing is superseded by this review.
- **R8.** Do not build a new, standalone agent for Country & Macro Risk
  where avoidable. Extend the existing `MacroAgent` with a discrete
  severity classification on top of its existing correlation logic first;
  add a wholly new agent only where no existing boundary is a reasonable
  extension point (Governance is the clearest case that genuinely needs
  one).
- **R9.** Compute Valuation, Growth/Quality, and Balance-Sheet Safety
  (Q1–Q3) as three labeled outputs of **one** unified Fundamentals Read
  (one extraction pass, one consistency check), not three independently
  maintained components, closing the three-way-disagreement risk named
  in 1.9.
- **R10.** Treat the position-aware decision function as a separate,
  stateless-per-call **Decision Service**, invoked with (a) the
  deterministic daily research pipeline's unchanged output and (b)
  externally supplied `PositionState` at query time — not as a new stage
  inside the autonomous daily pipeline. This preserves the existing
  pipeline's determinism guarantees and every existing test untouched,
  and correctly scopes "autonomous" to research generation while decision
  rendering is legitimately on-demand.
- **R11.** Reduce the External-Sector/FX layer's initial scope to CBE's
  own aggregate current-account/balance-of-payments reporting only.
  Demote Suez Canal/tourism/remittance disaggregation to a low-priority,
  validation-only addition pending real evidence it adds information
  CBE's aggregate doesn't already carry.
- **R12.** Keep this document, not the Blueprint or the Evidence Matrix,
  as the authority wherever the three disagree. Both prior documents get
  a short pointer edit (see below) rather than silent, undiscovered
  contradiction.

---

## Part 3 — Final Revised Architecture

```
Layer 0 — Identity & Universe            (unchanged from the Blueprint)

Layer 1 — Market Evidence
  price, volume, liquidity
  → NEW: seat of the liquidity/tradability hard floor (R4)

Layer 2 — Fundamentals Read (unified, R9)
  one extraction pass over financial statements →
  three labeled outputs: Valuation / Growth-Quality / Balance-Sheet Safety

Layer 3 — Event Evidence
  corporate actions, disclosures, governance/ownership changes
  (Narrative/News remains corroboration-only against this layer, R-unchanged
   from the original Blueprint's discipline)

Layer 4 — Country & Macro Risk (merged, R3)
  domestic macro + external-sector context + sovereign/credit context,
  as one graduated severity axis (normal / deteriorating / crisis)
  → computed by an EXTENDED MacroAgent (R8), not a new agent
  → crisis rung = the override, inside the same combination mechanism
    every other Layer uses (no separate short-circuit code path)
  → initial external-sector scope: CBE aggregate only (R11)

Layer 5 — Relative Evidence (Peer)
  DEFERRED — gated behind real Sector Membership data existing (R6)

Layer 6 — Governance Evidence
  ownership/related-party/free-float — smallest new agent (R8's one
  genuine exception)

[Data-Quality is NOT a layer — R7]
  Corroboration/freshness/calibration/sample-size gates, reusing
  `meta.readiness` (R2), applied as a multiplier/gate across every layer
  above, not a discrete pipeline stage.

        │  (deterministic, autonomous daily Research Pipeline — unchanged)
        ▼
  Recommendation / KnowledgeStore output (as today)

        │  (NEW boundary — R10)
        ▼
  Decision Service (separate, stateless-per-call, NOT inside the
  autonomous daily pipeline)
    inputs:  Recommendation output (above) + externally supplied
             PositionState (held/not held, size, cost basis)
    computes: one continuous target-portfolio-weight (R5, extending
              PortfolioConstructor's existing scoring), subject to the
              two hard floors (country-risk crisis rung, liquidity floor)
    derives:  Buy / Increase / Hold / Reduce / Exit / No Action as a
              LABEL from comparing target weight to current weight,
              with an explicit Abstain overlay when the Data-Quality gate
              fails (never a silent weak-Hold)
```

### Why this differs from both prior documents

- The Blueprint's Layer 7 and the Evidence Matrix's Q10 are reconciled:
  data quality is a gate/multiplier, not a pipeline stage (R7).
- Q5/Q9 are one Layer, not two, with the override as a rung rather than a
  separate mechanism (R3).
- Q1/Q2/Q3 are one Read, not three (R9).
- Q7 is explicitly deferred, not scoped as near-term work (R6, reversing
  the Evidence Matrix's own prior promotion).
- The six-way taxonomy is a view over a continuous number, not the
  computed primitive itself (R5).
- The decision function is architecturally outside the autonomous daily
  pipeline, not a new stage inside it (R10) — resolving the
  autonomy-vs.-position-awareness tension named in 1.10 explicitly rather
  than leaving it implicit.

---

## Part 4 — Final Implementation Roadmap

Supersedes the Evidence Matrix's Part 5 sequence. Ordered by what
survived this review's scrutiny, not by what the prior documents assumed.

1. **Extend `meta.readiness`'s existing gate** with two new checks:
   country-risk data presence, liquidity/tradability floor (R2). No new
   parallel gate mechanism.
2. **Build the Decision Service** as a separate, stateless-per-call
   component (R10) computing a continuous target weight (R5) from
   existing `Recommendation`/`KnowledgeStore` output plus externally
   supplied `PositionState`, deriving six-way labels from a target-vs-
   current-weight comparison. Use the existing simple
   `confidence × expected_return / risk`-style formula, extended only by
   the two hard floors from step 4/5 below — explicitly not the 31-row
   bespoke weight table (R1).
3. **Extend `MacroAgent`** (not a new agent, R8) to add the merged
   Country & Macro Risk severity classification (R3), sourced initially
   from CBE's own aggregate reporting only (R11) — Suez Canal/tourism/
   remittance disaggregation deferred.
4. **Wire the liquidity/tradability hard floor** (R4) from the existing
   liquidity agent's output into the Decision Service's override check,
   alongside country risk.
5. **Add rating-agency press-release and IMF program-review monitoring**
   as new `TargetOrganization` candidates, feeding the Country & Macro
   Risk crisis rung specifically (still needed — just feeding a merged
   mechanism instead of a bespoke separate one).
6. **Un-stub `FinancialPerformanceAgent`** as a single unified
   Fundamentals Read (R9) producing Valuation/Growth/Balance-Sheet-Safety
   together, for a ticker's own data only — peer replication explicitly
   out of scope here (see step 11).
7. **Governance evidence collection** (Q8) — the one genuinely new,
   smallest agent (R8's exception).
8. **Merge the `Economic Releases` capability into `Macroeconomic`**
   (unchanged from the prior roadmap — a low-effort clarity item that
   survived scrutiny unmodified).
9. **Remove the 11 Tier-4 sources with zero capability mapping**
   (unchanged — survived scrutiny unmodified).
10. **Market Breadth artifact** (unchanged, low priority).
11. **Peer-set fundamentals (Q7)** — explicitly gated behind real Sector
    Membership data existing; **demoted to last**, reversing the Evidence
    Matrix's own prior promotion (R6).
12. **Amwal Al Ghad as a `TargetOrganization` candidate** (unchanged,
    low-touch, folds in alongside step 5's acquisition work).

**Explicitly changed relative to the Evidence Matrix's Part 5**: steps
1–2 merge the old items 1 ("position-aware decision function") and the
old item 2's Sovereign & Credit capability differently — the capability
work (step 5) now feeds a merged Country & Macro Risk mechanism (step 3)
instead of a standalone Q9 override, and the decision function itself
(step 2) is now explicitly a separate service, not folded into the daily
pipeline. Peer-set fundamentals moved from position 5 to position 11 —
the single largest reordering this review produced, and a genuine
reversal of the prior document's own conclusion under scrutiny.

**Still explicitly not recommended**, unchanged from every prior
document: a general source-discovery sprint, or any rewrite of
`MetaDecisionEngine`/`PortfolioConstructor`/the publication gate beyond
the additive changes above.

No code has been written or modified in the production of this document.
Implementation begins only on explicit confirmation of this sequence.
