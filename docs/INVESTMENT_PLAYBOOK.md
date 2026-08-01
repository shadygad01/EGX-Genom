# The EGX-Genom Investment Playbook

**Status: permanent doctrine, operationalizing `docs/INVESTMENT_CONSTITUTION.md`.**
The Constitution states the permanent principles; this playbook states how
those principles apply to twelve recurring market situations. Every
section names, explicitly, which part is a **real, already-computed
signal** this platform can act on today, and which part is **doctrine for
a detector that does not exist yet** — the same anti-fabrication
discipline the Constitution itself demands applies to this playbook: it
never claims the platform automatically recognizes a situation it cannot
yet actually detect.

No situation in this playbook introduces a new decision mechanism. Every
situation is read *through* the six-way action taxonomy
(`docs/DECISION_STANDARDS.md`), the Capital Allocation Engine
(Constitution Article VII), and the existing hard overrides (liquidity
floor, country-risk severity) — a playbook entry changes what a CIO
should *expect* and *watch for* in a given regime, never a separate
scoring formula living outside the Constitution's evidence chain.

## How to read each entry

- **Expected Behaviour** — what this situation looks like in the data
  AGX already computes (Market Regime, Market Breadth, Country & Macro
  Risk, corporate events), and what does not yet have a dedicated
  detector.
- **Decision Priorities** — how the six-way taxonomy and the abstention/
  hold discipline should be read in this situation.
- **Capital Allocation Priorities** — how the ranking/opportunity-cost/
  recycling mechanics (Constitution Article VII) should be interpreted
  contextually.
- **Risk Adjustments** — which hard overrides and thresholds become more
  central.
- **Monitoring Priorities** — which `MonitoringWarning` categories and
  committees deserve the most attention.

---

## 1. Bull Markets

**Expected Behaviour.** Detected today via `market_memory.regime.
compute_market_regime()`: `MarketTrend.BULLISH` fires when the
equal-weighted universe's trailing-20-trading-day cumulative adjusted
return is `≥ +3%`. A bull market does not, by itself, change what counts
as evidence — it changes the *base rate* of how many tickers are likely
to clear the funding threshold at once.

**Decision Priorities.** Rising prices are not evidence of anything by
themselves — the Constitution's evidence chain (Article IX) is unchanged.
The real risk in a bull market is a rising `price_vs_fair_value_pct`
across many tickers simultaneously: `meta.readiness`'s
`MAX_PRICE_ABOVE_FAIR_VALUE_PCT = 0.20` ceiling should be expected to
start blocking INVESTMENT-horizon readiness on names that were
comfortably below fair value weeks earlier. A `BUY_CANDIDATE` that only
clears the score threshold because expected volatility compressed (a
falling `expected_risk` inflating the risk-adjusted score) rather than
because expected return genuinely rose deserves the same scrutiny an
`AdversarialScientist` regime-dependency attack would apply.

**Capital Allocation Priorities.** More tickers clearing the funding bar
simultaneously means the Global Opportunity Ranking (Article VII) does
more real work than in a quiet market — expect genuine displacement
(weakest-holding-first) rather than idle-cash-only funding, since the
number of legitimate demanders for capital rises. `highest_opportunity_cost`
becomes a more informative section: with more real, funded ideas, more
real ideas are also being correctly rejected, and that list should grow,
not stay empty.

**Risk Adjustments.** The liquidity floor (EGP 1,000,000 average daily
traded value) does not loosen just because sentiment is positive — a
thin name trading actively for a week is not the same as a name that has
cleared the floor on a trailing basis. The 20%-above-fair-value ceiling
is the primary brake in this regime; it should be expected to fire more
often, not treated as a nuisance to raise.

**Monitoring Priorities.** `review_required` warnings (a decision's
`valid_until` passed, or its supporting knowledge is `MONITORING`)
deserve more attention in a fast-moving bull market, since evidence ages
faster relative to price than in a quiet one. `portfolio_concentration`
also deserves elevated attention — a bull market concentrates gains into
winners, and the Herfindahl/sector-concentration checks
(`docs/PORTFOLIO_STANDARDS.md`) should be expected to trip more often
purely from price appreciation, not new buying.

---

## 2. Bear Markets

**Expected Behaviour.** `MarketTrend.BEARISH` fires when the trailing
cumulative return is `≤ -3%`. As with bull markets, this is a base-rate
signal, not new evidence about any individual ticker.

**Decision Priorities.** A bear market is exactly where Article VI's
distinction between "the evidence says leave" and "the evidence went
quiet" matters most. A held ticker whose thesis is genuinely intact but
whose supporting knowledge has gone temporarily stale (no fresh
INVESTMENT-horizon finding) must still resolve to `HOLD`, never a
fabricated `EXIT` — a falling market is not itself contradicting evidence
unless it shows up as a real sibling-horizon disagreement or a retired
knowledge object. Conversely, a genuine `EXIT` (real evidence turned
negative) must not be second-guessed into a `HOLD` merely because "it's
already down" — sunk-cost reasoning has no place in either direction.

**Capital Allocation Priorities.** Expect `cash_waiting.idle_cash_after`
to rise structurally in a bear market: fewer tickers clear the funding
threshold, so more capital is correctly left idle rather than forced into
a weakening set of ideas. This is the Capital Allocation Engine working
as designed (Article III/VII), not a malfunction — a playbook reader
expecting the queue to always be "full" is misreading its purpose.

**Risk Adjustments.** Country & Macro Risk deserves closer reading in a
sustained bear market — a real EGP/USD move crossing the 5% deterioration
floor is more likely to co-occur with broad equity weakness than in a
calm market, and `DETERIORATING`/`CRISIS` severity overrides every
target weight regardless of individual thesis strength (Article III).

**Monitoring Priorities.** `broken_thesis` warnings are the highest
priority: `ContinuousLearningMonitor`'s retirement mechanism (Article XI)
is the platform's real defense against holding a position whose original
case has genuinely failed, and a bear market is exactly when a real
thesis failure is most likely to also coincide with price weakness —
making it tempting, and wrong, to attribute a retirement to "the market"
rather than to the evidence that actually triggered it.

---

## 3. Interest-Rate Cycles

**Expected Behaviour — doctrine, not yet a dedicated detector.** No
collector currently supplies a CBE policy-rate series distinctly enough
for a dedicated rate-cycle classifier to exist (`agents.macro`'s
mechanism is generic: it forward-fills whatever macro series it is given
and produces sensitivity findings, it does not itself classify "cycle
phase"). Until a policy-rate series is collected and a dedicated
sensitivity mechanism is built for it, a rate move is only visible
indirectly — as whatever real macro-sensitivity findings `MacroAgent`
produces from the series it does have, and as a real change in
`CountryRiskAssessment` if the move is severe enough to affect the
currency.

**Decision Priorities (doctrine).** A rate-cycle turn should be expected
to change sector-level expectancy disproportionately (rate-sensitive
sectors — banks, real estate, leveraged issuers) before it changes
individual-name evidence. Until a dedicated rate-sensitivity signal
exists, the correct interim discipline is unchanged from Article IX: no
recommendation changes because of a rate move unless a real
`KnowledgeObject` evidencing that sensitivity exists and survives the
full pipeline. Do not let a rate headline substitute for evidence.

**Capital Allocation Priorities (doctrine).** Once real rate-sensitivity
evidence exists, expect it to produce genuine sector-level rotation in
the Global Opportunity Ranking (Article VII) — rate-sensitive names'
`opportunity_score` should move together, and the Capital Allocation
Engine's existing mechanics (idle-cash-first, weakest-holding-displaced-
first) apply unchanged; no new allocation rule is needed once the
evidence layer exists.

**Risk Adjustments.** `RiskReviewer`'s expected-risk ceiling
(default 10%) should be expected to bind more often on leveraged/
rate-sensitive names during a hiking cycle — `expected_risk` for such
names is real evidence a rate move should widen, not something to
override.

**Monitoring Priorities.** Until a dedicated collector exists, this is
named explicitly as a gap: `docs/TECHNICAL_DEBT.md` should carry the
repayment trigger (a real CBE policy-rate source going `IMPLEMENTED`) the
same way every other declared-not-yet-measured mechanism in this
platform is tracked, not left as a silent absence.

---

## 4. Currency Shocks

**Expected Behaviour.** Real, mechanically detected today:
`decision_service.country_risk.assess_country_risk()` classifies
`DETERIORATING` when the resolved EGP/USD series moves `≥ 5%` cumulative
over the available window; `CRISIS` requires a real, discrete sovereign
rating downgrade on top of that (never inferred from the currency move
alone — Constitution Article X).

**Decision Priorities.** `DETERIORATING` is not itself a hard override —
it is a real, elevated-severity finding that shows up in
`macro_risk_increased` warnings and in every affected decision's
`contradicting_evidence`, but individual tickers still resolve on their
own evidence. `CRISIS` *is* a hard override: every target weight is
forced to zero, portfolio-wide, regardless of individual thesis strength
(Article III). The distinction matters operationally — a currency move
alone, however large, should never by itself force an `EXIT` across the
board; only a real rating downgrade does.

**Capital Allocation Priorities.** A `DETERIORATING` finding should be
expected to widen `expected_risk` on FX-sensitive names (import-heavy
importers, USD-debt issuers) via real `macro_agent` sensitivity findings,
which lowers their risk-adjusted score and their standing in the Global
Opportunity Ranking honestly, through the same mechanism every other
score change flows through — never a special-cased currency override
outside the normal ranking.

**Risk Adjustments.** This is the one situation where the platform's two
hard overrides (liquidity floor, country-risk crisis) can compound: a
severe currency shock often coincides with a liquidity contraction across
the exchange, and both overrides should be expected to bind
simultaneously on the same names.

**Monitoring Priorities.** `macro_risk_increased` is the primary signal;
`liquidity_deterioration` should be watched immediately alongside it,
since the two frequently move together in a real currency event.

---

## 5. Inflation Shocks

**Expected Behaviour — doctrine, not yet a dedicated detector.** Same
structural gap as interest-rate cycles: `agents.macro` is a generic
sensitivity mechanism, not an inflation-specific classifier. A real CPI
or equivalent price-level series is needed as input before any
inflation-specific behavior can be evidence-backed rather than asserted.

**Decision Priorities (doctrine).** The correct discipline, once a real
inflation series exists, is identical to Article IX: an inflation-driven
recommendation change requires a real `KnowledgeObject`, not an inference
from a headline CPI print. Until then, no decision may change "because of
inflation" without a real, promoted finding behind it.

**Capital Allocation Priorities (doctrine).** Inflation shocks should be
expected to compress real (inflation-adjusted) expected returns broadly,
which the Global Opportunity Ranking would reflect automatically once
real evidence flows through `expected_return`/`expected_risk` — again, no
new allocation mechanism is needed, only the evidence layer.

**Risk Adjustments.** Margin-sensitive sectors (retail, low-pricing-power
industrials) are the ones a real inflation-sensitivity finding should be
expected to hit hardest via `RiskReviewer`'s ceiling and the Fair Value
Engine's terminal-growth/WACC assumptions
(`valuation.engine.ValuationAssumptions`), which already model a real
terminal-growth rate (4%) and WACC (16%) — a sustained real inflation
shock is a legitimate future reason to revisit those declared
assumptions via the same amendment discipline Article XI's technical-debt
register uses, never a silent parameter change.

**Monitoring Priorities.** Same named gap as interest-rate cycles: track
this as an open item until a real inflation series is collected and
wired through `agents.macro`.

---

## 6. Political Risk

**Expected Behaviour.** Partially real today: a real, discrete political
event with a corroborating sovereign rating action reaches `CRISIS`
severity through the same mechanism currency shocks use (Article X);
short of that, real news-driven findings from `NewsIntelligenceAgent`
(headline-keyword sentiment feeding a mechanical event-study-lite signal,
mapped to `Category.CATALYST`) are the primary real evidence channel.
There is no dedicated "political risk" classifier distinct from the
country-risk/news mechanisms already described.

**Decision Priorities.** The same discipline as currency shocks applies:
a political headline alone changes nothing about any specific ticker's
decision unless it produces a real, evidenced finding (a real corporate
event, a real sovereign rating action, or a real
`NewsIntelligenceAgent`-derived knowledge object that survives the full
pipeline). Political risk is exactly the kind of situation where the
temptation to "just act on the headline" is strongest, and exactly where
Article IX's evidence discipline matters most.

**Capital Allocation Priorities.** No special treatment beyond what real
evidence produces — a political shock large enough to matter should show
up as a real change in `expected_risk`/`expected_return` on affected
names and in `CountryRiskAssessment`, and flow through the ranking
normally.

**Risk Adjustments.** Country-risk severity is the primary lever
available today; a genuinely severe political event without a
corroborating rating action is, honestly, currently under-covered by this
platform's mechanical detection (the same `docs/TECHNICAL_DEBT.md` gap
named for `SovereignRatingAction`'s missing collectors). This is not
silently accepted — it is the platform's own stated limit, and human
judgment should fill the gap until a real collector exists.

**Monitoring Priorities.** `macro_risk_increased` warnings and any
`NewsIntelligenceAgent`-sourced knowledge entering `MONITORING` status
are the two real signals to watch.

---

## 7. Liquidity Crises

**Expected Behaviour.** Real and mechanically detected today at the
individual-ticker level: `decision_service.liquidity_floor.
compute_illiquid_tickers()` flags any ticker whose average `close ×
volume` falls below EGP 1,000,000. `market_memory.breadth.
compute_market_breadth()` separately reports how many constituents are
trading above/below their own trailing 20-day average volume — a market-
wide liquidity crisis shows up as a broad shift toward
`tickers_below_average_volume`.

**Decision Priorities.** The liquidity floor is a hard override
(Article III) — an illiquid ticker's target weight is zero regardless of
thesis strength, full stop. A liquidity crisis does not change this rule;
it changes how many tickers it applies to at once. No decision should
ever attempt to "size around" illiquidity with a smaller position — the
override is binary by design (Constitution Article III, Portfolio
Standards §3), because a thin market does not become safely tradable at
a smaller size, it becomes unpredictable at any size.

**Capital Allocation Priorities.** Expect the Capital Allocation Engine's
matching to behave conservatively: fewer tickers pass the liquidity
floor to receive capital at all, and `capital_recycled` flows should be
expected to shrink even if the Global Opportunity Ranking still shows
attractive scores — a strong risk-adjusted score on an illiquid name is
real evidence of a good idea with no current way to execute it, and the
platform is required to say so rather than force a position.

**Risk Adjustments.** This is the one situation where the liquidity floor
itself — not just its application — deserves scrutiny: `docs/
TECHNICAL_DEBT.md`'s standing note that `DEFAULT_MIN_AVERAGE_TRADED_VALUE`
is a declared, uncalibrated floor becomes most relevant in exactly this
regime, since a genuine market-wide liquidity crisis is real evidence
relevant to whether EGP 1,000,000 is still the right number — never
changed unilaterally, only via the same amendment discipline Article XI
requires.

**Monitoring Priorities.** `liquidity_deterioration` warnings are the
direct signal; a rising count of them across the universe, correlated
with `market_breadth.tickers_below_average_volume`, is the platform's
honest signature of a market-wide (not single-name) liquidity event.

---

## 8. Strong Earnings

**Expected Behaviour.** Real signal sources: `CorporateEventsAgent`
(the `earnings` corporate-event type) and `FinancialPerformanceAgent`
(real revenue-growth-trend and leverage-trend findings from
`DatasetSnapshot.financial_statements`, mapped to `Category.QUALITY`) —
both produce genuine `KnowledgeObject` candidates when they exist, never
a fabricated read of an earnings print.

**Decision Priorities.** A strong earnings print is evidence, not a
verdict — it must still survive the full 8-gate pipeline before it can
influence `expected_return`. A single strong quarter does not itself
justify `INCREASE_POSITION`; it justifies a fresh, re-evaluated
risk-adjusted score, exactly as Article IV requires, and that score must
still outrank the competition for the same capital (Article VII).

**Capital Allocation Priorities.** A genuinely strong, promoted earnings
finding should be expected to raise a ticker's rank and make it a
legitimate demander in the Capital Allocation Queue — potentially
displacing a weaker existing holding, which is the correct, intended
behavior of "the weakest idea is displaced first" (Article VII), not a
forced trim to be second-guessed.

**Risk Adjustments.** The Fair Value Engine's `dcf`/`residual_income`/
`earnings_power` models should be expected to move meaningfully on a real
earnings beat (they consume `eps`/`free_cash_flow`/`operating_income`
directly) — a strengthening fair value can relax the 20%-above-fair-value
readiness ceiling that a prior, lower fair value was blocking, a
legitimate and expected consequence, not a threshold being loosened.

**Monitoring Priorities.** `catalyst_expired` warnings for the earnings
event itself (the platform's signal that the catalyst has passed and the
thesis is due for a fresh look) should be expected within
`CATALYST_RECENTLY_EXPIRED_DAYS` (7 days) of the print.

---

## 9. Weak Earnings

**Expected Behaviour.** The same real signal sources as strong earnings,
producing the opposite sign of finding — a genuine negative
revenue-growth-trend or leverage-deterioration finding from
`FinancialPerformanceAgent`, or an `earnings` corporate event with
negative sentiment from the news layer.

**Decision Priorities.** Symmetric to strong earnings: a weak print is
real evidence to re-score, not an automatic `REDUCE_POSITION`/`EXIT`. If
the re-evaluated risk-adjusted score turns non-positive, `AVOID`/`EXIT`
follows from the evidence, exactly as Articles II/VI require — but a
single weak quarter against an otherwise-intact multi-source thesis
should be expected to show up as `WEAKENING` in `ThesisSurvivalEngine`'s
assessment (new contradicting evidence, without necessarily a broken
assumption) rather than an immediate `BROKEN` verdict, unless the
knowledge that specifically underpinned the thesis was itself retired.

**Capital Allocation Priorities.** A genuinely weakened ticker's falling
`opportunity_score` should be expected to make it a real capital supplier
(Article VII) — its capital, if reduced or exited, is explicitly
attributed to whichever higher-ranked demander receives it
(`CapitalRelease.destinations`), never left as an unexplained trim.

**Risk Adjustments.** Fair value should be expected to fall on a genuine
earnings deterioration, which can newly trip the 20%-above-fair-value
ceiling even without any price movement at all — a legitimate,
evidence-driven readiness change, not a bug.

**Monitoring Priorities.** `review_required` (supporting knowledge moved
to `MONITORING`) is the earliest real signal a weak print produces, often
before a full retirement; watch it closely rather than waiting for
`broken_thesis`.

---

## 10. Sector Rotation

**Expected Behaviour — partially real, no dedicated rotation detector.**
The closest real signal today is `MarketStructureAgent`'s cross-ticker
co-movement/correlation findings (mapped to `Category.SECTOR` —
`investment_proof.categories`'s own documented "closest honest proxy to
a sector committee opinion available today," since no dedicated
sector-peer-average computation exists yet). `dashboard.portfolio_summary`
and `investment_proof.portfolio_validation` separately report real
sector exposures for whatever is currently held, but there is no
mechanism today that detects "capital is rotating from sector A to
sector B" as its own signal.

**Decision Priorities (doctrine).** Until a dedicated rotation detector
exists, sector-level moves are visible only indirectly, through
individual `market_structure_agent` findings on specific tickers. No
decision should be made "because a sector is rotating" without a real,
ticker-specific finding behind it — the same evidence discipline applies
regardless of how visually obvious a sector move looks on a chart.

**Capital Allocation Priorities.** The Sector Committee row in
`Investment Committee Summary` (`Category.SECTOR`'s agreement/
decisiveness rate) is the most honest real signal available today for
"is sector-level evidence actually moving the final decision" — read it
before inferring rotation from raw sector-weight changes alone, which can
also result from ordinary single-name idiosyncratic moves.

**Risk Adjustments.** `PortfolioValidationEngine`'s
`MAX_SECTOR_CONCENTRATION = 0.40` ceiling is the platform's real, existing
defense against an unintended rotation concentrating the portfolio in one
sector, whether or not the rotation itself was ever explicitly detected —
the concentration check does not need to know *why* weight concentrated
in one sector to correctly flag that it did.

**Monitoring Priorities.** `portfolio_concentration` warnings scoped to
sector (not just position) concentration are the primary signal;
`docs/TECHNICAL_DEBT.md` should carry a named gap for a dedicated
sector-rotation detector as a genuine future capability, not a silent
absence.

---

## 11. Market Panic

**Expected Behaviour.** Real composite signature, assembled from several
already-real signals rather than one dedicated "panic" classifier:
`MarketTrend.BEARISH` (`≤ -3%` trailing cumulative return) co-occurring
with `VolatilityLevel.HIGH` (`≥ 2.5%` daily volatility) and a broad
`market_breadth.decliners` majority with elevated
`tickers_below_average_volume`. Panic is this platform's honest reading
of "bearish trend + high volatility + broad, thin participation"
occurring together, not a single flag.

**Decision Priorities.** Panic is the single highest-risk regime for the
Constitution's central discipline (Article VI) to be violated under
pressure: a real evidence gap (no fresh knowledge, prices simply falling
with everything else) must still resolve to `HOLD`, never a fabricated
`EXIT`, exactly as in any other regime — the temptation to treat "the
whole market is down" as evidence against a specific, still-intact thesis
is exactly the failure mode Article VI exists to prevent. Conversely, a
real evidence-based `EXIT` must not be delayed by "waiting for calmer
markets" — the evidence chain does not pause for sentiment.

**Capital Allocation Priorities.** Expect the liquidity floor to bind
much more broadly than usual (thin, panicked markets produce genuinely
lower traded value, not just lower prices) — `cash_waiting.idle_cash_after`
should be expected to rise sharply and correctly, since fewer tickers
both clear the funding threshold *and* the liquidity floor
simultaneously. This is the Capital Allocation Engine correctly refusing
to force capital into a market that currently cannot absorb it, not a
malfunction to override.

**Risk Adjustments.** Both hard overrides (liquidity floor, country-risk
severity) deserve the closest possible reading in a panic — a real panic
is exactly the situation the constitution designed these overrides for.

**Monitoring Priorities.** `liquidity_deterioration` and
`macro_risk_increased` should be watched together; a rising count of
both, alongside `market_breadth`'s decliner count, is this platform's
honest, composite definition of a real panic event, and should trigger
the closest possible human review of every abstention reason currently
being reported — panic is when the difference between "the evidence
says leave" and "the evidence went quiet" matters most, and it is also
when it is hardest to keep straight under pressure.

---

## 12. Market Euphoria

**Expected Behaviour.** The composite mirror of panic:
`MarketTrend.BULLISH` co-occurring with `VolatilityLevel.ELEVATED`/`HIGH`
and a broad `market_breadth.advancers` majority. Elevated *volatility*
alongside a bullish trend (rather than the low volatility a calm,
genuine bull market would show) is the platform's honest signature that
strength has become euphoric rather than measured.

**Decision Priorities.** Euphoria is where Article II's abstention
discipline is under the most social pressure to be relaxed — "everything
is going up" is not evidence for any specific ticker, and a `WATCH` or
`ABSTAIN` verdict must not be quietly upgraded because ignoring a rally
feels wrong. The `price_vs_fair_value_pct` readiness check
(20% ceiling) is the platform's primary real defense here, and it should
be expected — correctly — to block a rising number of tickers from
INVESTMENT-horizon readiness exactly when sentiment says to buy more.

**Capital Allocation Priorities.** A euphoric market can produce a
*false* abundance of apparently-attractive `opportunity_score`s if
`expected_risk` compresses market-wide (lower measured volatility
inflating every score's denominator) — this is exactly the kind of
regime-dependency the `AdversarialScientist`'s `REGIME_DEPENDENCY` attack
exists to catch at the evidence layer, before a finding ever reaches the
ranking. The Capital Allocation Engine itself has no special "euphoria
mode" — it trusts whatever scores the evidence layer hands it, which is
exactly why the evidence layer's own defenses (Article IX) matter more,
not less, in this regime.

**Risk Adjustments.** The fair-value ceiling and `RiskReviewer`'s
expected-risk floor (real risk rarely falls as much as measured recent
volatility suggests in a genuine euphoria) are the two levers to trust
most; neither should be relaxed to "let the portfolio participate more."

**Monitoring Priorities.** A rising, not falling, count of `no_action`/
`abstain` outcomes across the universe during a broad rally is this
platform's own honest signature of euphoria being correctly resisted —
read a quiet Capital Deployment Queue during a loud market as the system
working, and verify it against the readiness/fair-value blockers actually
being reported before assuming something is wrong.

---

## Cross-Cutting Rule

No entry in this playbook ever authorizes skipping a gate, loosening a
threshold, or fabricating a signal that has no real detector behind it.
Every situation above is read through the same evidence chain, the same
six-way taxonomy, and the same Capital Allocation Engine every ordinary
day uses — a playbook entry changes what a CIO should expect and watch
for, never what counts as evidence.
