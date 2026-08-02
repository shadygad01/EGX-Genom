# EGX-Genom Decision Standards

**Status: permanent doctrine, operationalizing `docs/INVESTMENT_CONSTITUTION.md`.**
This document specifies, exactly, the minimum standard every recommendation
must clear before it may carry a given label. It is deliberately mechanical
— every rule below is a direct restatement of real, already-implemented
logic (`meta.decision_engine.MetaDecisionEngine._decision_for_prediction`,
`meta.decision_quality.evaluate_decision_quality`/`apply_decision_quality_gate`
(replacing `meta.publication_gate.evaluate_publication_gate`/
`apply_publication_gate`, 2026-08-02 — see `ARCHITECTURE_DECISIONS.md`),
`decision_service.service.DecisionService._resolve_action`), not a new
policy layered on top of it. If this document and the code it describes
ever disagree, that is a real bug to fix, not a discretionary judgment
call — file it exactly as `docs/ARCHITECTURE_DECISIONS.md` requires for
any correction to a previously-stated rule.

## Two taxonomies, one evidence chain

This platform uses two related but distinct label sets, and confusing
them is the single most common way to misread a decision:

1. **`DecisionAction`** (`meta.decision_engine`) — the *research* verdict
   for one horizon's prediction, computed without knowledge of any
   position: `BUY_CANDIDATE`, `WATCH`, `AVOID`, `ABSTAIN`.
2. **`PositionAction`** (`decision_service.service`) — the *position-aware*
   six-way action a real investor sees, computed by comparing a
   continuous target weight against the ticker's current weight:
   `buy`, `increase_position`, `hold`, `reduce_position`, `exit`,
   `no_action`.

`PositionAction` is always derived from a `DecisionAction` plus position
state plus the publication gate — never computed independently. **There
is no seventh `PositionAction` value called "abstain."** Abstention is a
boolean modifier (`PositionAwareDecision.abstained`) that determines
*which* of `hold`/`no_action` applies and *why* — see §7 below. Treat
"Abstain" in this document as "the abstained variant of Hold or No
Action," matching exactly what the code does.

---

## 0. The research-level floor every decision passes through first

Before any position-aware label can exist, `MetaDecisionEngine.
_decision_for_prediction()` must first produce a `DecisionAction` from
the raw prediction:

| Research verdict | Minimum standard |
|---|---|
| `BUY_CANDIDATE` | `confidence ≥ 0.60`, **and** `expected_return > 0`, **and** `risk_adjusted_score = confidence × expected_return / expected_risk ≥ 1.0`, **and** a real, positive reference price exists (no executable entry level, no `BUY_CANDIDATE` — it downgrades to `ABSTAIN` instead). |
| `WATCH` | `confidence ≥ 0.60`, `expected_return > 0`, but `risk_adjusted_score < 1.0` — real, positive expectancy, not yet strong enough to act on. |
| `AVOID` | `confidence ≥ 0.60`, `expected_return ≤ 0` — the evidence itself argues against the position. |
| `ABSTAIN` | `confidence < 0.60`, **or** a would-be `BUY_CANDIDATE` with no reference price. |

No `PositionAction` may ever be more permissive than this floor. A ticker
that fails to reach `BUY_CANDIDATE` here can never resolve to `buy` or
`increase_position` downstream, regardless of position state.

## 1. What Qualifies as **Buy**

Requires **all** of the following, simultaneously:

- The ticker is **not currently held** (`PositionState.held = False`, or
  absent from the positions supplied).
- A real `Recommendation` exists whose INVESTMENT-horizon `HorizonDecision`
  reached `BUY_CANDIDATE` (§0).
- That decision's `publication_status == PUBLICATION_READY` — the
  decision quality gate has cleared for *this specific decision*
  (`docs/INVESTMENT_CONSTITUTION.md` Article IX): supporting evidence
  present and traceable, a complete investment thesis, calculated
  confidence, defined invalidation conditions, defined monitoring/review
  conditions, and internal consistency — never a system-wide wait on
  external evidence, track record, or legal sign-off (2026-08-02, see
  `ARCHITECTURE_DECISIONS.md`).
- `abstained = False` — no hard override (illiquidity, country-risk
  crisis) and no decision-quality blocker applies.
- The resulting `target_weight`, after the ticker's score is normalized
  jointly against every other ticker competing for the same capital
  (`docs/INVESTMENT_CONSTITUTION.md` Article VII), is strictly positive
  (`> ε`, `ε = 1e-9`).

A `buy` label without an executable entry price, an invalidation level,
and a stated capital source (`docs/PORTFOLIO_STANDARDS.md` §5) is never
valid — `apply_decision_quality_gate()`'s internal-consistency check
explicitly downgrades any `BUY_CANDIDATE` lacking numeric entry/
invalidation levels back to `RESEARCH_ONLY`, and the Capital Allocation
Engine's `capital_sources` field is mandatory on every funded queue
entry.

## 2. What Qualifies as **Increase**

Requires **all** of the following:

- The ticker **is currently held**.
- `abstained = False`.
- The freshly re-evaluated `target_weight` is strictly greater than the
  ticker's `current_weight` (`target_weight > current_weight + ε`).

An increase is always a *fresh* re-evaluation, never an extrapolation of
the original thesis. The evidence that justifies a larger position must
independently clear §0's floor as of today, exactly as the evidence that
justified the original position did.

## 3. What Qualifies as **Hold**

`Hold` has two structurally different, equally valid causes, and a
correct decision record always states which one applies:

**(a) Confirmed hold** — the ticker is held, `abstained = False`, and the
re-evaluated `target_weight` is within tolerance of `current_weight`
(`|target_weight − current_weight| ≤ ε`). The evidence was re-checked and
genuinely still supports the current size, no more, no less.

**(b) Abstained hold** — the ticker is held, but `abstained = True`,
because at least one of:
- No current INVESTMENT-horizon evidence exists for this ticker at all
  (`decision is None`) — an evidence *gap*, not evidence *against* the
  position.
- The research-level decision itself is `ABSTAIN` (§0).
- `publication_status != PUBLICATION_READY` — a real, positive research
  case exists but has not cleared the publication gate.

In case (b), `target_weight` numerically computes to `0.0` (the
underlying score is treated as zero when ineligible), but the action is
still `hold`, never `exit` — `docs/INVESTMENT_CONSTITUTION.md` Article VI
states why: an evidence gap must never be read as a sell signal. Every
`hold` record must carry `reasons` explaining which of (a) or (b)
applies, and if (b), exactly which gate is unmet.

## 4. What Qualifies as **Reduce**

Requires **all** of the following:

- The ticker **is currently held**.
- `abstained = False`.
- The freshly re-evaluated `target_weight` is strictly positive but
  strictly less than `current_weight` (`0 < target_weight <
  current_weight − ε`).

A `reduce` label is only valid when the platform can also state *why*
less capital is warranted: either the ticker's own risk-adjusted score
weakened, or a stronger competing idea now outranks it for the same
shared budget. The Capital Allocation Engine's `CapitalRelease.
destinations` field is mandatory — a reduce with no stated destination
for the released capital does not meet this standard
(`docs/PORTFOLIO_STANDARDS.md` §5).

## 5. What Qualifies as **Exit**

Requires **all** of the following:

- The ticker **is currently held**.
- `abstained = False`.
- The freshly re-evaluated `target_weight` is effectively zero
  (`≤ ε`).

Exit is a **decisive** call — the evidence itself now argues against
holding any position, distinct from an abstained hold (§3b), which
carries the same numeric `target_weight = 0.0` but a different, weaker
claim. The three real triggers that legitimately produce `exit`, per
`docs/INVESTMENT_CONSTITUTION.md` Article VI, are: a hard override
(illiquidity or country-risk crisis) forcing the weight to zero; the
supporting knowledge being retired by `ContinuousLearningMonitor`
(`docs/INVESTMENT_CONSTITUTION.md` Article XI); or the risk-adjusted case
itself turning genuinely non-positive after re-evaluation. An `exit`
label attached to an evidence *gap* rather than one of these three real
triggers does not meet this standard and must be relabeled `hold`.

## 6. What Qualifies as **No Action**

Requires **all** of the following:

- The ticker is **not currently held**.
- Either `abstained = True`, **or** the resulting `target_weight` is
  effectively zero (`≤ ε`) with no positive research case.

No Action is the correct, honest default for the overwhelming majority
of the investable universe at any given time — most tickers will not
have a `BUY_CANDIDATE`-grade, publication-ready case on any given day, and
`no_action` states that plainly rather than fabricating a `WATCH` opinion
just to have something to say.

## 7. What Qualifies as **Abstain**

`abstained = True` is set whenever the platform is unable to state a
confident, actionable opinion, for one of these real, stated reasons —
never an unexplained gap:

- **No evidence exists** for the ticker at this horizon at all.
- **The research-level verdict is itself `ABSTAIN`** (§0): confidence
  below 60%, or a would-be buy with no executable reference price.
- **The publication gate is not cleared** — the case may be statistically
  excellent internally, but has not yet demonstrated live market data,
  four periods of disclosures, current macro data, two-source price
  corroboration, 30+ benchmark-outperforming results, and legal approval,
  simultaneously (`docs/INVESTMENT_CONSTITUTION.md` Article II/IX). This
  is, as of this writing, the reason the overwhelming majority of real
  decisions this platform produces are abstained: no licensed EGX market
  data vendor exists yet, so the gate can never fully clear
  (`docs/DECISION_SYSTEM_ACCEPTANCE.md`).
- **A hard override applies**: the ticker is below the liquidity floor
  (`docs/PORTFOLIO_STANDARDS.md` §3), or Country & Macro Risk severity is
  `CRISIS` (`docs/INVESTMENT_CONSTITUTION.md` Article III).

Every abstained decision's `reasons` field must name the specific,
real gate that was not cleared. A generic "insufficient evidence" with no
further detail does not meet this standard — the whole point of surfacing
abstention as a first-class, explained outcome (rather than a silent
`no_action`) is that a reader can tell *exactly* what would need to
change for the platform to have an opinion.

---

## Standards this document does not relax

- No standard above may be satisfied by an approximation, an analyst's
  override, or a "close enough" reading of a threshold. `ε = 1e-9` exists
  precisely to distinguish real floating-point noise from a genuine,
  material difference — it is not a discretionary tolerance band.
- No `PositionAction` may be assigned without the `Explanation`/
  `Provenance` pair `docs/INVESTMENT_CONSTITUTION.md`'s evidence
  discipline (Article IX) requires on every recommendation-like object in
  this platform. A decision with a label but no traceable evidence chain
  behind it does not meet any standard in this document, regardless of
  which label it carries.
