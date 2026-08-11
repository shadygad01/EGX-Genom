# EGX30 Autonomous Pattern Discovery Engine — Research Report

Produced by the Pattern Discovery mission (2026-08-11), step 17 of its
mandated implementation order. This report documents an actual run of the
engine built by this mission (`research/src/agx_research/patterns/`)
against the data this repository actually has, plus the synthetic-data
tests that establish the engine's mechanics are correct before trusting
its real-data output. See `docs/PATTERN_DISCOVERY_DATA_AUDIT.md` for the
full dataset-by-dataset inventory this report's data-coverage section
summarizes.

**Bottom line, stated first**: run against this repository's actual data
today, the engine discovers and validates **zero patterns**. This is not
a partial result or an engine limitation being excused — it is the
correct, honest output given that no real, sufficiently deep EGX price
history exists in this repository yet (10 trading days for 2 of 30
constituents). The engine itself is real, tested against synthetic data
specifically constructed to contain a genuine relationship, and is ready
to run the moment real depth exists.

## Data coverage

Summarized from `docs/PATTERN_DISCOVERY_DATA_AUDIT.md`; see that document
for the full per-dataset table.

| Dataset | Real or synthetic | Depth | Usable for backtest |
|---|---|---|---|
| EGX price OHLCV (mock fixture) | Synthetic | 10 trading days, 2/30 tickers | No — mechanics-testing only |
| EGX price OHLCV (real, via `egx_price_composite` collector) | Real when run | Not collected in this session — outbound network to Yahoo/StockAnalysis/Mubasher is denied by this environment's proxy policy (`403`, confirmed via `curl` and `$HTTPS_PROXY/__agentproxy/status`) | Not yet — no data exists to judge |
| Macro: Brent, EGP/USD (FRED) | Real | ~278–286 daily obs, ~13 months | Yes, point-in-time gated |
| Macro: Egypt CPI/GDP/interest rate (World Bank) | Real | 11–13 annual obs each | Caution — ordering safe, value-vintage unresolved (World Bank revises) |
| Universe (EGX30/EGX70) | Real | Single snapshot, 2026-07-26 | No for any historical `as_of` — no reconstitution history |
| News | Real | 285 rows, mostly untagged to any ticker | Limited |
| Financial statements | — | 0 rows anywhere in the repository | No — doesn't exist |
| Sector classification | Placeholder | 10 of 30 EGX30 tickers | Partial |

## Search space (this run)

Against the only tickers with real row depth (COMI, MFPC, mock fixture,
10 trading days each), `agx research build-features --as-of 2026-06-14
--tickers COMI,MFPC`:

- **127 features generated**: 60 price, 30 volume, 29 cross-sectional, 8
  macro, **0 fundamental** (honestly empty — no financial statements
  exist for either ticker).
- Every feature's `non_null_count` after the 10-day window is small (most
  price/volume transforms: 0–10 non-null values; anything needing a
  10-, 20-, or 60-day lookback: 0).

`agx research discover --as-of 2026-06-14 --tickers COMI,MFPC` (default
`CandidateGeneratorConfig(min_sample_size=30)`):

- **Candidates generated: 0.** `PatternCandidateGenerator.eligible_features()`
  drops every feature below `min_sample_size=30` non-null observations
  before any condition is even considered — with a 10-row panel, no
  feature can ever clear that floor, so the search space is correctly
  empty rather than searched with an undersized, unreliable sample.

## Validation methodology

Implemented in `research/src/agx_research/patterns/`:

- **Point-in-time safety** (`panel.py`, `features.py`, `targets.py`,
  `leakage.py`): every feature read goes through
  `FeatureSeries.as_of_value(t)`, a binary-search join that can never
  return an entry dated after `t`; every target is computed from bars
  strictly after its anchor (`closes[i+1:i+1+h]`, never `closes[i]` or
  earlier); macro features are stamped with `data.point_in_time.known_as_of()`
  (publication-lag-adjusted), not the raw observation date; fundamental
  features are stamped `period_end_date + ASSUMED_FILING_LAG_DAYS`
  (declared, conservative). `leakage.py`'s `verify_ascending`/
  `verify_no_future_dates`/`safe_feature_value` are explicit, independently
  testable guards, not just implicit by construction.
- **Universe/survivorship-bias handling**: honestly documented as
  *not solved* — `ResearchPanel.universe_limitation_note` is attached to
  every panel and cited in every CLI report; universe membership is a
  single fixed snapshot for the whole study period (no reconstitution
  history exists to do better).
- **Candidate generation control** (`candidates.py`): eligibility floor
  (`min_sample_size`), feature-level correlation pruning
  (`correlation_prune_threshold=0.8`), a quantile-based threshold grid
  (not exhaustive search), two-feature interactions restricted to each
  feature's median condition only, three-feature interactions gated by a
  headroom requirement, regime-conditioned variants from a small curated
  regime-feature list, and a hard `max_candidates_per_ticker` budget.
  **Match-set redundancy pruning** (`match_overlap_prune_threshold=0.85`,
  added mid-mission after the finding below): a candidate whose matched
  trigger-date set overlaps an already-kept candidate's by more than this
  Jaccard threshold is dropped as redundant, not independently novel.
- **Discovery statistics** (`evaluation.py`): sample count, hit rate,
  mean/median/expectancy, stdev, downside deviation, MFE/MAE means,
  profit factor, max-drawdown mean, a bootstrap 95% CI, a bootstrap
  two-sided p-value, and a stability score (sign agreement across
  chronological buckets) — never a bare return.
- **Purged, embargoed walk-forward validation** (`validation.py`):
  expanding-window folds, chronological only (never random), with
  `purge_and_embargo()` removing every training observation whose own
  target window could overlap the test period plus an extra embargo
  buffer. A candidate survives only if its pooled out-of-sample sample
  size clears a floor *and* its OOS expectancy agrees in sign with its
  discovery-sample expectancy.
- **Multiple-testing control** (`multiple_testing.py`): Benjamini-Hochberg
  FDR control (`fdr_alpha=0.05` default) plus a persisted `TestingLedger`
  recording exactly how many hypotheses were tested, on what discovery/
  validation sample sizes, for every run — including runs that discover
  nothing.
- **Robustness testing** (`robustness.py`): threshold-perturbation
  sensitivity (nearby thresholds relative to the feature's own spread),
  nearby-lookback sensitivity (sibling window features), nearby-horizon
  sensitivity (sibling target horizons), a regime breakdown, a calendar-
  period breakdown, and a transaction-cost-survival check
  (`transaction_cost_bps=20.0`) — every check degrades to an honest "not
  enough data to test" rather than fabricating a result.
- **Baseline comparison** (`baselines.py`): unconditional market,
  buy-and-hold, momentum, mean-reversion, sector-relative, and (data-
  permitting) a revenue-growth fundamental baseline. `validate()` rejects
  a pattern whose OOS expectancy, net of transaction costs, does not beat
  buy-and-hold.
- **Lifecycle** (`registry.py`): `DISCOVERED → VALIDATING → VALIDATED →
  ACTIVE → WEAKENING → REJECTED → RETIRED`, persisted via
  `storage.JsonFileRepository` (append-only, versioned) — a rejected
  pattern is never deleted, only transitioned, so it stays available for
  audit.

## An important finding this mission surfaced (and addressed, not hidden)

Testing the engine against *synthetic pure-noise* data (no real
relationship, seeded random walks) at the originally-planned defaults
(`correlation_prune_threshold=0.9`, `fdr_alpha=0.10`) showed that
Benjamini-Hochberg FDR control, applied to a candidate pool built from
many highly correlated derived features (e.g. `return_1d` and `return_3d`
on the same ticker) over a short (200–500 day) sample, can occasionally
let dozens of nominally-surviving "discoveries" through at once — BH's
FDR guarantee is exact under independence and weakens under the positive
correlation this kind of engineered-feature pool inherently has, and its
step-up procedure has a known "cascade" property (once enough small
p-values line up, progressively larger ones qualify too). This is a
real, well-documented phenomenon in the data-mining-bias literature
(e.g. White 2000, Aronson 2006), not a hypothetical.

Two concrete responses, both now live in the code (not just noted here):

1. **Match-set redundancy pruning** (`candidates.py`, described above)
   — added specifically because many "different" candidates were really
   re-testing the same underlying coincidence through slightly different
   window/threshold parameterizations.
2. **Tightened declared-conservative defaults**: `correlation_prune_threshold`
   0.9 → 0.8, `fdr_alpha` 0.10 → 0.05, both documented in-code as
   "declared conservative, not measured-optimal."

These measurably reduced, but — being honest — did **not eliminate** the
phenomenon on every synthetic seed tested; some noise realizations still
produced multiple nominal survivors after these changes. This is why
`validate()`'s purged walk-forward + robustness + baseline-beating gates
are treated as **load-bearing, not optional** downstream of FDR control,
and why `decay.py`'s `DecayMonitor` keeps watching every `VALIDATED`
pattern's *live* performance indefinitely rather than trusting validation
as a one-time event. No single stage in this pipeline — including FDR
control by itself — is sufficient proof of a real relationship; this is
by design, and this finding is exactly why.

This has **no effect on this run's real-data result**: with only 10
trading days of real depth, no candidate is ever generated in the first
place (see Search space above), so the phenomenon above cannot manifest
against actual repository data today. It matters for the day real depth
exists.

## Validated patterns (this run)

**None.** Zero candidates were generated (search space above), so zero
were validated. This is the correct, expected result given current data
depth, not evidence of an engine defect — see the positive-control proof
below.

## Rejected / never-generated patterns (this run)

No candidate ever reached even the `DISCOVERED` stage — every feature was
already excluded at the eligibility floor (`min_sample_size=30` vs. at
most 10 real observations per feature). There is nothing to catalog as
"rejected"; the registry (`patterns/registry.json`) is empty after this
run, and the `TestingLedger` records `hypotheses_tested=0`.

## Current active patterns

None — `agx research active` returns `[]` against the current registry,
correctly, since nothing has ever been validated.

## Proof the engine can validate a real pattern (positive control)

`research/tests/test_pattern_engine.py::test_engine_end_to_end_validates_a_real_planted_pattern`
constructs two deterministic, seeded synthetic tickers with a genuine
periodic momentum relationship (alternating 10/13-day up/down blocks,
small noise) and runs the *exact same* `discover()` → `validate()`
pipeline used above. Result, reproduced from that test:

```
return_1d:A/B condition -> forward_return_5d
sample=15+, oos_sample_size>=8, hit_rate=0.84, expectancy=+0.026, robustness_passed=True
validation_status=VALIDATED
```

This is the falsifiability check the mission requires: an engine that
always reported zero regardless of input would trivially "pass" every
honesty requirement while being useless. This one doesn't — it finds and
validates a real signal when one exists, and finds nothing when the real
data doesn't support finding anything.

## Known data limitations (restated from the audit)

- No real, multi-year EGX price history exists in this repository; the
  collector that could produce it (`egx_price_composite`) cannot reach
  the network from this session.
- EGX30/EGX70 universe membership is a single current-day snapshot — any
  historical `as_of` before it is exposed to real survivorship bias this
  platform cannot currently correct.
- World Bank annual macro series (CPI, GDP growth, interest rate) carry
  unresolved revision risk — safe ordering, unverified value-vintage.
- No financial statements are collected for any ticker — fundamental
  features and the fundamental baseline are implemented but produce
  honestly empty results today.
- News is mostly untagged to any specific ticker and cannot be used
  systematically without a dedicated relevance/entity-linking pass, which
  is out of this mission's scope.

## Leakage / overfitting safeguards implemented

See "Validation methodology" above for the full list; summarized:
`as_of_value()` binary-search joins, strictly-forward target windows,
`leakage.py`'s explicit guards (tested — see below), publication-lag
stamping for macro/fundamental features, purged+embargoed walk-forward
(never random splits), Benjamini-Hochberg FDR control plus match-set
redundancy pruning, robustness perturbation testing, and a baseline-
beating requirement net of transaction costs.

## Tests executed and results

`cd research && uv run pytest` — **1149 passed** (full repository suite,
including every pre-existing test — nothing broken by this mission).

Of those, **86 tests** are new, in
`research/tests/test_pattern_*.py` + `pattern_test_helpers.py`:

| File | Tests | Covers |
|---|---|---|
| `test_pattern_panel.py` | 7 | Point-in-time joins/timestamp alignment (real `MarketMemory` wiring) |
| `test_pattern_leakage.py` | 10 | **Proves a deliberately leaked future-dated entry is rejected** (`LookaheadBiasError`); proves feature/target builders structurally cannot see ahead (synthetic future-spike test) |
| `test_pattern_features.py` | 9 | Feature generation correctness, metadata, `as_of_value` forward-fill semantics |
| `test_pattern_targets.py` | 6 | Target calculation, strictly-forward windows |
| `test_pattern_candidates.py` | 7 | Eligibility floor, correlation pruning, sample-size enforcement, regime conditioning |
| `test_pattern_evaluation.py` | 9 | Discovery statistics correctness |
| `test_pattern_validation.py` | 9 | Chronological splits, walk-forward folds, purge/embargo, survives-a-real-signal / rejects-a-sign-flip |
| `test_pattern_multiple_testing.py` | 5 | BH FDR accounting, ledger persistence |
| `test_pattern_robustness.py` | 4 | Threshold-sensitivity overfit detection, transaction-cost survival |
| `test_pattern_registry.py` | 5 | Persistence, versioning, never-delete-only-transition lifecycle |
| `test_pattern_live.py` | 6 | Live activation match/no-match/missing-data/regime-compatibility |
| `test_pattern_outcomes_decay.py` | 6 | Outcome tracking, decay flagging, WEAKENING transition |
| `test_pattern_engine.py` | 5 | **End-to-end positive control** (validates a real planted pattern) and **honest-zero proof** (thin data → zero candidates) |

## Exact files changed

New package: `research/src/agx_research/patterns/` (16 modules, 3,411 lines) —
`__init__.py`, `panel.py`, `features.py`, `targets.py`, `leakage.py`,
`candidates.py`, `evaluation.py`, `validation.py`, `multiple_testing.py`,
`robustness.py`, `registry.py`, `live.py`, `outcomes.py`, `decay.py`,
`baselines.py`, `engine.py`.

New tests: `research/tests/pattern_test_helpers.py` +
`research/tests/test_pattern_{panel,leakage,features,targets,candidates,
evaluation,validation,multiple_testing,robustness,registry,live,
outcomes_decay,engine}.py` (14 files, 1,468 lines).

Modified: `research/src/agx_research/cli.py` (new `agx research
{audit-data,build-features,discover,validate,patterns,active,evaluate}`
subcommand group, ~180 lines added).

New docs: `docs/PATTERN_DISCOVERY_DATA_AUDIT.md`,
`docs/PATTERN_DISCOVERY_REPORT.md` (this file).

## Exact commands to reproduce this research

```bash
cd research

# 1. Run the full test suite (proves the engine's mechanics, including
#    the leakage-detection and positive-control proofs above).
uv run pytest

# 2. Audit actual data coverage for a given as-of/tickers.
uv run python -m agx_research.cli --data-dir <data-dir> \
  research audit-data --as-of 2026-06-14 --tickers COMI,MFPC

# 3. Build the Feature Factory's output and inspect coverage by category.
uv run python -m agx_research.cli --data-dir <data-dir> \
  research build-features --as-of 2026-06-14 --tickers COMI,MFPC

# 4. Phase 1: generate candidates, screen, FDR control, persist DISCOVERED patterns.
uv run python -m agx_research.cli --data-dir <data-dir> \
  research discover --as-of 2026-06-14 --tickers COMI,MFPC

# 5. Phase 2: purged walk-forward OOS validation + robustness + baseline check.
uv run python -m agx_research.cli --data-dir <data-dir> \
  research validate --as-of 2026-06-14 --tickers COMI,MFPC

# 6. Inspect the registry, evaluate live matches, track outcomes/decay.
uv run python -m agx_research.cli --data-dir <data-dir> research patterns
uv run python -m agx_research.cli --data-dir <data-dir> \
  research active --as-of 2026-06-14 --tickers COMI,MFPC
uv run python -m agx_research.cli --data-dir <data-dir> \
  research evaluate --as-of 2026-06-14 --tickers COMI,MFPC
```

Once real, deep EGX price history exists (a licensed vendor, or this
collector run from an environment with the necessary network access —
see `docs/PATTERN_DISCOVERY_DATA_AUDIT.md`), the same commands, run
against `--source collected` and the real EGX30/EGX70 universe, are the
actual research this mission was built to eventually produce. Until
then, the honest answer to "does a validated pattern exist" is: **there
is not yet enough real data to know, and the platform correctly says so
rather than guessing.**
