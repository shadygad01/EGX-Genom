# Decision Evidence Matrix — EGX-Genom

**Status: research and architecture only. No production code changed.**
This document is decision-first: every row starts from a question the
long-term investment decision needs answered, and asks what evidence
answers it — never the reverse ("here is a source, what could it be
used for"). It builds directly on
`docs/FREE_DECISION_DATA_BLUEPRINT.md`'s ten first-principles questions
(Part 0) and its source survey (Part 1), and on
`docs/DECISION_CENTRIC_AUDIT_2026-07-30.md`'s finding that the platform's
decision output must become a **position-aware six-way action**: Buy,
Hold, Increase Position, Reduce Position, Exit, No Action. Scope: this
matrix is deliberately built for the mission's stated audience — a
**long-term** investor — not the platform's existing MICRO/SWING horizons.

---

## How to read this matrix

Each of the ten questions gets:

1. **Evidence required** — every distinct piece of evidence that answers
   the question, each rated Mandatory/Optional, an expected decision
   weight (Critical/High/Medium/Low, matching the Blueprint's priority
   scale), and confidence considerations (what would make this specific
   evidence untrustworthy).
2. **Decision contribution** — one row showing, in plain terms, what
   pattern of this question's evidence points toward each of the six
   actions. No single question ever produces a final decision alone —
   Part 3 below defines how the ten combine.

**The six actions, defined operationally for this matrix:**

| Action | Meaning | Position precondition |
|---|---|---|
| Buy | Initiate a new position | Not currently held |
| Increase Position | Add to an existing position | Currently held, below its size cap |
| Hold | Keep the existing position unchanged | Currently held |
| Reduce Position | Trim, but do not fully exit | Currently held |
| Exit | Fully close the position | Currently held |
| No Action | Do nothing; no position and no new evidence justifies one | Not currently held |

**Abstain is not a seventh action** — it is an overlay applied when
Question 10 (data trustworthiness) fails its confidence floor. An
abstained read still resolves to Hold (if held) or No Action (if not
held) operationally, but must be flagged distinctly in the explanation as
"insufficient evidence," never presented as a confident neutral read (see
Part 3.3).

---

## Part 1 — The ten questions, evidence-first

### Q1 — Is the stock cheap or expensive relative to its own fundamentals?

| Evidence required | Source(s) (Blueprint §) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Multi-period financial statements (revenue, net income, book value, cash flow) | Company IR / EGX official disclosure (§3) | Mandatory | Critical | PDF-extraction quality; needs ≥4 comparable periods to be non-trivial; currency-reporting consistency (EGP vs. USD across issuers) |
| Current, corroborated price | Price & Trading Data (§2) | Mandatory | Critical | Two-source agreement; freshness (days since last observation) |
| Peer valuation multiples | Sector/Peer comparables (§10) | Optional | High | Peer-set completeness; same-currency/same-period comparability |
| Own historical multiple range | Same fundamentals + historical price | Optional | Medium | Needs enough historical periods to be meaningful — a genuine data-depth gap early on, not a methodology flaw |

**Decision contribution — Q1:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Discount to own history/peers, no offsetting Q2/Q3 deterioration | Discount deepens further while held, thesis intact | Fairly valued vs. history/peers | Valuation turns rich vs. history/peers | Extreme overvaluation, or the fundamentals behind the multiple deteriorated (interacts Q2/Q3) | Fairly valued, not held, no discount to justify entry |

### Q2 — Is the underlying business growing, stable, or deteriorating?

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Revenue/earnings trend across periods | Company IR / EGX disclosure (§3) | Mandatory | Critical | Same ≥4-period floor as Q1; one-off/non-recurring items are hard to separate from PDF prose |
| Sector-level demand corroboration | CAPMAS sector output / PMI (§6, §10) | Optional | Medium | Sector aggregate ≠ company-specific; monthly-lagged |
| Disclosed guidance/new contracts | Company press releases / EGX disclosure (§4) | Optional | Medium | Headline-only extraction (no numeric detail by design, see Gap Audit TD-29), qualitative |

**Decision contribution — Q2:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Clear improving trend, not already priced in (interacts Q1) | Accelerating trend while held | Stable trend, thesis intact | Deceleration/margin compression emerging, not severe | Structural decline confirmed across periods, or a disclosed event invalidates the growth thesis (interacts Q4) | Stable/mixed trend, not held, insufficient edge |

### Q3 — Is the balance sheet safe (leverage, liquidity, FX exposure)?

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Leverage ratios (debt/equity, interest coverage) | Company IR / EGX disclosure (§3) | Mandatory | Critical | Same extraction-quality caveat as Q1/Q2 |
| FX-denominated debt disclosure | Company IR / EGX disclosure (§3, §4) | Mandatory for FX-exposed sectors (banks, importers); Optional otherwise | High | Often buried in financial-statement notes, non-standard disclosure format — a real extraction-completeness risk, not just a formatting one |
| System-wide FX reserve adequacy (macro backdrop) | CBE (§6) | Optional | Medium | Automated collection historically WAF-blocked; needs live re-verification |

**Decision contribution — Q3:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Strong balance sheet, low FX mismatch, supports entry despite country risk | Balance sheet improving (deleveraging) while held | Safety unchanged, thesis intact | Leverage or FX mismatch rising, not yet critical | Balance-sheet risk becomes severe, or a devaluation event crystallizes an FX mismatch into a real loss (interacts Q9) | Weak/mixed balance sheet, not held, insufficient safety margin |

### Q4 — Is there a near-term catalyst or event risk?

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Corporate-action disclosures (dividends, splits, M&A, management change) | EGX / FRA disclosure (§4) | Mandatory | Critical | Headline-classifier accuracy is a declared, uncalibrated heuristic today (Gap Audit TD-29) |
| Independent news corroboration | Primary financial press (§11) | Optional | High | Per-outlet reliability varies; a discovery-tier aggregator (e.g. GDELT) never counts alone |
| Applicable regulatory circular | FRA (§4, §12) | Optional | Medium | Scope check needed — market-wide vs. issuer-specific |

**Decision contribution — Q4:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Positive disclosed catalyst (buyback approval, contract win), no offsetting Q1–Q3 concern | Confirmed positive catalyst arrives while held (earnings beat, resumed dividend) | No material new catalyst, thesis stands | Moderately negative disclosed event, not thesis-ending | Disclosed event invalidates the original thesis (going-concern flag, fraud disclosure, delisting notice, sharply negative guidance) | No material catalyst, not held |

### Q5 — What is the macro/FX backdrop doing to earnings power and the multiple the market will pay?

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| CBE policy rate, inflation, FX reserves | CBE (§6) | Mandatory | Critical | Automated-collection WAF risk (needs re-verification); monthly/quarterly lag |
| External-sector data (Suez Canal receipts, tourism, remittances) | §7 | Optional but high-value | High | Monthly frequency, no stated seasonal adjustment, aggregate not company-specific |
| Global context (oil, wheat, US rates/DXY) | §9 | Optional | Medium | Indirect, sector-dependent transmission — must not be applied uniformly across tickers (oil matters oppositely for an energy consumer vs. producer) |

**Decision contribution — Q5:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Stable/improving backdrop (reserves rising, inflation moderating) supports the multiple | Macro tailwind strengthens while held (reserve buildup, rate-cut cycle beginning) | Backdrop broadly unchanged | Backdrop deteriorating (reserve drawdown, re-accelerating inflation), not yet a crisis | A macro/FX shock materializes (currency float, sudden reserve depletion, external financing gap) — interacts with Q9's override | Weak/uncertain backdrop, not held, insufficient conviction to initiate against it |

### Q6 — Does trading behavior (liquidity, momentum) confirm or contradict the fundamental thesis?

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Own price/volume series, corporate-action-adjusted | Price & Trading Data (§2) | Mandatory | Critical | Must be split/dividend-adjusted or return calculations are simply wrong — a known real bug class, not a hypothetical |
| Market breadth / index-level context | §2, §10 | Optional | Medium | A derived artifact not yet built anywhere in the existing platform (named gap) |
| Liquidity (traded value, free float) | §1, §2 | Mandatory for sizing; Optional for signal direction | High | EGX has real liquidity concentration; a thin name needs a wider confidence band on any price signal |

**Decision contribution — Q6:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Price/volume confirms the thesis (accumulation, rising relative strength) and liquidity supports a sane entry size | Confirming strength while held (adds evidence, doesn't independently justify entry) | Neutral behavior, consistent with unchanged thesis | Behavior contradicts the thesis (distribution, key support breaking) while held — an early warning even if fundamentals look unchanged | Severe liquidity deterioration or a sustained trend break contradicting the thesis, combined with any other negative question | Neutral/contradictory behavior, not held, insufficient confirmation |

### Q7 — How does it compare to sector peers?

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Peer fundamentals (Q1–Q3's data, replicated across the sector peer set) | Peer companies' own IR pages (§10) | Optional (Q1–Q3 answerable in absolute terms without it) | High | Same extraction-quality caveat as Q1, multiplied by peer count — the largest new engineering surface this matrix surfaces (Part 4) |
| Sector index level/trend | EGX sector indices (§10) | Optional | Medium | Index composition/weighting not always transparent |
| PMI / sector output statistics | §6, §10 | Optional | Medium | Aggregate, not company-specific; monthly-lagged |

**Decision contribution — Q7:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Cheaper and/or better-quality than peers on a comparable basis | Relative advantage over peers widening while held | Roughly in line with peers, no relative edge | Peers overtaking on growth/quality/valuation while held | Structural loss of competitive position vs. peers confirmed over multiple periods | In line with or weaker than peers, not held |

### Q8 — Is governance and ownership trustworthy (related-party risk, insider activity, free float)?

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Major-shareholder / ownership-threshold-crossing disclosures | EGX / issuer disclosure (§5) | Mandatory | High | Event-driven — absence of a disclosure is not evidence of absence of activity, only absence of a threshold crossing |
| Board composition / related-party transaction disclosure | Company annual reports (§5) | Optional | Medium | Buried in long-form annual reports; high extraction effort; annual-only update |
| Free float / state-ownership percentage | EGX (§1, §5) | Mandatory | High | Slow-changing, high reliability once collected |

**Decision contribution — Q8:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Clean ownership structure, adequate free float, no adverse related-party pattern, possibly insider buying | Insider buying, or a related-party risk resolving favorably, while held | No new governance concern | A related-party transaction or governance flag emerges while held, not yet disqualifying | Large-scale insider selling, a related-party transaction disadvantaging minority holders, or a state-ownership/free-float change materially altering the case | Governance data thin/mixed, not held, insufficient trust to initiate |

### Q9 — What is the sovereign/country-risk backdrop (credit, capital controls, political stability)?

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Sovereign credit rating actions | Moody's / S&P Global / Fitch press releases (§8) | Mandatory | Critical | Rare, discrete, high reliability when they occur — but silence is not itself informative (absence of an action ≠ absence of risk) |
| IMF program review outcomes | §6, §8 | Optional but high-value | High | Infrequent (roughly semi-annual), historically high information content for Egypt specifically |
| CBE reserve/FX data (shared with Q5) | §6 | Mandatory | Critical | Same confidence caveats as Q5 |

**Decision contribution — Q9:**

| Buy | Increase | Hold | Reduce | Exit | No Action |
|---|---|---|---|---|---|
| Stable/improving country-risk backdrop (rating affirmed/upgraded, program on track) | Backdrop improving further while held (upgrade, successful review) | No change in backdrop | Backdrop deteriorating (negative outlook, delayed review), not yet a crisis | **Override case**: a severe country-risk event (downgrade past a critical threshold, program breakdown, capital controls, a currency float) forces Exit/Reduce regardless of every other question's read (Part 3.2) | Weak/uncertain backdrop, not held, insufficient conviction given elevated systemic risk |

### Q10 — Is the underlying data itself trustworthy enough to act on?

Q10 is structurally different from Q1–Q9: it never casts its own
directional vote. It multiplies the confidence of every other question's
contribution, and below a floor, forces the Abstain overlay.

| Evidence required | Source(s) | Mandatory/Optional | Decision weight | Confidence considerations |
|---|---|---|---|---|
| Cross-source corroboration status | All (meta-evidence about every source above) | Mandatory | Critical | This *is* the confidence measure, not a separate input to it |
| Freshness/staleness of each contributing evidence item | All | Mandatory | Critical | A stale disclosure or price should shrink confidence even if the fact itself is unchanged |
| Extraction/heuristic calibration status | All heuristic classifiers (event-type, sentiment, ticker-matching) | Mandatory | High | Several classifiers are declared-but-uncalibrated today (Gap Audit TD-29/TD-35/TD-42) — this is real, named, current-state risk, not speculative |
| Sample-size sufficiency | Q1–Q3 (financial periods), Q6 (price observations) | Mandatory | Critical | Matches the existing readiness gate's own period/observation floors |

**Confidence contribution — Q10** (multiplicative, not directional):

| Full confidence | Degraded confidence | Below floor |
|---|---|---|
| Full weight applied to whatever Q1–Q9 indicate | Weight shrinks proportionally — a marginal Buy/Increase signal should shrink toward Hold/No Action as confidence falls, never stay full-strength with a footnote | **Abstain overlay forced** regardless of what Q1–Q9 indicate; resolves operationally to Hold (if held) / No Action (if not held), explicitly flagged as "insufficient evidence" in the explanation, never presented as a confident neutral read |

---

## Part 2 — Condensed full traceability table

One row per evidence item across all ten questions, for a single
scannable view (detail lives in Part 1; this is the index).

| Question | Evidence | Mandatory? | Weight | Primary action(s) it can trigger |
|---|---|---|---|---|
| Q1 | Multi-period financial statements | Yes | Critical | Buy, Increase, Reduce, Exit |
| Q1 | Corroborated current price | Yes | Critical | Buy, Increase, Reduce, Exit |
| Q1 | Peer valuation multiples | No | High | Buy, Reduce |
| Q1 | Own historical multiple range | No | Medium | Buy, Reduce |
| Q2 | Revenue/earnings trend | Yes | Critical | Buy, Increase, Exit |
| Q2 | Sector demand corroboration | No | Medium | Buy, Reduce |
| Q2 | Disclosed guidance/contracts | No | Medium | Increase, Reduce |
| Q3 | Leverage ratios | Yes | Critical | Buy, Exit |
| Q3 | FX-denominated debt disclosure | Yes (FX-exposed sectors) | High | Exit |
| Q3 | System FX reserve adequacy | No | Medium | Exit |
| Q4 | Corporate-action disclosures | Yes | Critical | Buy, Increase, Reduce, Exit |
| Q4 | Independent news corroboration | No | High | Increase, Reduce |
| Q4 | Applicable regulatory circular | No | Medium | Reduce, Exit |
| Q5 | CBE rate/inflation/reserves | Yes | Critical | Buy, Increase, Reduce, Exit |
| Q5 | External-sector data (Canal/tourism/remittances) | No | High | Buy, Reduce |
| Q5 | Global commodity/rate context | No | Medium | Reduce |
| Q6 | Adjusted price/volume series | Yes | Critical | Buy, Reduce |
| Q6 | Market breadth/index context | No | Medium | Reduce |
| Q6 | Liquidity/free float | Yes (sizing) | High | All (sizing constraint) |
| Q7 | Peer fundamentals | No | High | Buy, Reduce, Exit |
| Q7 | Sector index level/trend | No | Medium | Reduce |
| Q7 | PMI/sector output stats | No | Medium | Reduce |
| Q8 | Ownership-threshold disclosures | Yes | High | Buy, Increase, Exit |
| Q8 | Board/related-party disclosure | No | Medium | Reduce, Exit |
| Q8 | Free float/state ownership | Yes | High | Buy, Exit |
| Q9 | Sovereign rating actions | Yes | Critical | **Override**: Exit/Reduce (all tickers) |
| Q9 | IMF program review outcomes | No | High | Reduce, Exit |
| Q9 | CBE reserve/FX data | Yes | Critical | Reduce, Exit |
| Q10 | Cross-source corroboration | Yes | Critical | Confidence multiplier on all above |
| Q10 | Freshness/staleness | Yes | Critical | Confidence multiplier on all above |
| Q10 | Extraction/heuristic calibration | Yes | High | Confidence multiplier on all above |
| Q10 | Sample-size sufficiency | Yes | Critical | Confidence multiplier on all above |

---

## Part 3 — How the ten questions combine into one decision

### 3.1 Mandatory-evidence gate

No action beyond Abstain may be emitted for a ticker unless every
**Mandatory** row for Q1, Q4, Q5, Q6, Q8, and Q9 is present. Q2/Q3's
mandatory rows are folded into Q1's (they come from the same financial
statements). This is a decision-first restatement of the existing
platform's readiness gate — same underlying floors (≥4 financial
periods, price freshness/depth, macro series count), reorganized around
"what does the decision itself require," not "what layer of data exists."
**New relative to the existing gate**: Q9's mandatory evidence
(sovereign rating status, CBE reserve data) is not part of today's
readiness check at all — see Part 4.

### 3.2 Country-risk override rule

If Q9's evidence indicates a severe event (a downgrade past a declared
critical threshold, an IMF program breakdown, capital controls, or a
currency float), the resulting signal forces **Exit** for every held
position and **No Action** for every unheld ticker, regardless of what
Q1–Q8 indicate. This is a hard override, not a heavily-weighted vote —
implemented as a short-circuit check before the weighted combination
below runs, not as a large negative number folded into the same sum
(a large-but-finite negative weight could theoretically be outvoted by
enough positive evidence elsewhere; a true country-risk crisis should
not be arguable away by a strong balance sheet).

### 3.3 Confidence as a multiplier, not a vote

Q10 never contributes a directional signal (Part 1's Q10 table has no
Buy/Hold/etc. cells for exactly this reason). It multiplies the combined
weight of Q1–Q9's signal. Below a declared confidence floor, the
multiplier collapses the signal to zero, which resolves to the Abstain
overlay (Hold if held, No Action if not held) — never silently to a
"weak Hold" that looks the same as an actually-neutral read.

### 3.4 Position-state × signal-direction resolution

The combined, confidence-discounted signal from Q1–Q9 (after the Q9
override check) is bucketed into five directional strengths, then
resolved against position state:

| Aggregate signal | Not held | Held, below size cap | Held, at size cap |
|---|---|---|---|
| Strongly positive | **Buy** | **Increase** | **Hold** (cap already reached) |
| Positive | **Buy** (reduced size) | **Increase** (reduced size) | **Hold** |
| Neutral | **No Action** | **Hold** | **Hold** |
| Negative | **No Action** | **Reduce** | **Reduce** |
| Strongly negative / thesis invalidated | **No Action** | **Exit** | **Exit** |
| Q9 override triggered | **No Action** | **Exit** | **Exit** |
| Q10 confidence below floor | **No Action** (Abstain) | **Hold** (Abstain) | **Hold** (Abstain) |

This table is the direct specification for the Gap Audit's roadmap item
3.1 (the position-aware six-way decision function) — every cell here is
implementable as-is.

---

## Part 4 — Reconciliation: reviewing the Blueprint, the Gap Audit, and this Matrix together

Three real findings emerge only from reading all three documents side by
side — none of them was visible from any single document alone:

**1. Q9 (sovereign/country risk) and its override rule have no
supporting capability in the platform today, and this matrix shows it is
structurally load-bearing, not optional enrichment.** The Gap Audit's
roadmap never mentions sovereign credit or IMF program data at all
(it audited existing code, which has no such capability to find). The
Blueprint ranked Sovereign & Credit Context "High" priority as a source
category. This matrix goes one step further: Q9 isn't just a
high-priority *input*, it's the one question with **veto power** over
every other question's conclusion (3.2). A six-way decision function
built per roadmap item 3.1 without Q9's override would be
**structurally incomplete**, not just missing an enrichment source. This
reprioritizes new acquisition work (rating-agency press releases, IMF
program review outcomes) from "not on the roadmap" to "a prerequisite
for roadmap item 3.1 to be correct," not merely a nice-to-have addition
after it.

**2. Q5's External-Sector/FX-driver data (Suez Canal, tourism,
remittances) is the same situation one level down.** `suez_canal_stats`
already exists in the current source catalog as a `PLANNED` entry, but
the Gap Audit separately found it has **zero capability mapping** in
`acquisition_intelligence/capability.py` — i.e., even the platform's own
capability engine doesn't currently attempt to collect it for any
purpose. This matrix's Q5 table shows why that matters: this data
answers Q5 with a distinctiveness (leading, Egypt-specific, independent
of CBE's own aggregate reporting) that generic global macro data cannot
substitute for. This reprioritizes "give External-Sector data a real
capability mapping" from an unlisted gap to a near-term roadmap item.

**3. Q7's peer-fundamentals requirement is larger new engineering scope
than the Gap Audit's roadmap implies.** Roadmap item 3.2 ("un-stub
`FinancialPerformanceAgent`") reads as one agent, one ticker at a time.
This matrix's Q7 row makes explicit that a genuinely decision-quality
peer-comparison capability needs the *same* fundamentals extraction
replicated across a sector's peer set — not a new kind of data, but
materially more extraction volume/effort than un-stubbing a single-ticker
agent implies. This doesn't change item 3.2's priority, but it means
item 3.2 and a (previously unnamed) "peer-set fundamentals" item should
be scoped and staffed as two related but distinct pieces of work, not
assumed to fall out of the same change.

**No other reprioritization is warranted.** The rest of the Gap Audit's
roadmap (un-stubbing `FinancialPerformanceAgent` first among data-gap
items, merging Economic Releases into Macroeconomic, removing the 11
Tier-4 sources, the Market Breadth artifact, Amwal Al Ghad/IDSC as new
`TargetOrganization` candidates) holds up against both the Blueprint and
this Matrix — those items were already well-reasoned and remain correctly
prioritized below the items reordered above.

---

## Superseded by the adversarial review

`docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md` re-opened this matrix under
deliberately hostile scrutiny and changed several load-bearing pieces of
it: the 31-row weight table above should not be coded as-is (R1); Part
3.1's mandatory gate should extend `meta.readiness`, not exist as a
second parallel mechanism (R2); Q5/Q9 should merge into one graduated
axis with the override as its top rung, not a separate short-circuit
(R3); a symmetric liquidity floor is missing (R4); the six-way action in
Part 3.4 should be a label derived from a continuous target weight, not
the computed primitive itself (R5); and Q7's promotion to a near-term
roadmap item in Part 4 below was reversed — it is gated behind Sector
Membership data that doesn't yet exist (R6). Part 5's sequence below is
superseded by that review's Part 4 roadmap; the per-question evidence
tables in Parts 1–2 above remain the source of record for *what evidence
exists*, just not for *how it is weighted/combined*.

## Part 5 — Proposed production implementation sequence

This is the first point across all three documents where an actual build
order is proposed. Ordered by what Part 4 reconciliation established:
Q9's override is a *correctness* prerequisite, not an enrichment, so it
moves ahead of everything except the core decision function it plugs
into.

1. **Position-aware six-way decision function** (Buy/Increase/Hold/
   Reduce/Exit/No Action), built directly to Part 3's specification —
   including the Q9 override short-circuit and the Q10 multiplicative
   confidence discount **from the start**, not bolted on later. This
   supersedes the Gap Audit's original items 3.1 and 3.4, which are now
   merged into one correctly-scoped item per Part 4 finding 1.
2. **Minimal Sovereign & Credit Context capability**: rating-agency
   (Moody's/S&P Global/Fitch) public press-release monitoring and IMF
   program-review-outcome tracking, added as new identity-only
   `TargetOrganization` candidates for the existing, unmodified
   Acquisition Intelligence Engine to resolve — through the same
   mechanism the Gap Audit's item 3.7 already established, not by
   reopening acquisition architecture generally. Prerequisite for step 1
   to be correct, per Part 4 finding 1.
3. **External-Sector/FX-driver capability repair**: give
   `suez_canal_stats` a real entry in the capability map, and add
   Ministry of Tourism (tourist arrivals/revenue) as a new
   `TargetOrganization` candidate. Per Part 4 finding 2.
4. **Un-stub `FinancialPerformanceAgent`** for a ticker's own
   fundamentals (Q1–Q3), exactly as the Gap Audit's item 3.2 specified.
5. **Peer-set fundamentals extraction** (Q7), scoped and staffed as its
   own item per Part 4 finding 3 — same extraction technique as step 4,
   applied across a sector's peer set, feeding relative valuation and
   relative-quality reads.
6. **Governance/ownership evidence collection** (Q8): major-shareholder
   threshold-crossing disclosures and free-float/state-ownership data —
   previously named only as a general "no sector/peer layer" gap in the
   Gap Audit; this Matrix's Q8 row makes it a distinct, scoped item.
7. **Merge the `Economic Releases` capability into `Macroeconomic`**
   (Gap Audit item 3.3, unchanged — low-effort clarity).
8. **Remove the 11 Tier-4 sources with zero capability mapping**
   (Gap Audit item 3.5, unchanged).
9. **Market Breadth artifact** (Q6 context; Gap Audit item 3.6,
   unchanged).
10. **Amwal Al Ghad as a `TargetOrganization` candidate** (Gap Audit item
    3.7's remaining half; IDSC is now folded into step 3's macro-context
    work).

Steps 1–3 are the only reordering relative to the Gap Audit's original
roadmap; steps 4 onward preserve that roadmap's original priority order,
with step 5 newly named and step 6 elevated from an implicit note to an
explicit item, both per Part 4.

**Still explicitly not recommended, unchanged from the Gap Audit**: a
general source-discovery sprint, or any rewrite of `MetaDecisionEngine`/
`PortfolioConstructor`/the publication gate beyond the additive change
step 1 requires.

No code has been written or modified in the production of this document.
Implementation begins only on explicit confirmation of this sequence.
