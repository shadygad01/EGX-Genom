# EGX30 Pattern Discovery — Positive/Negative Control Suite

Generated 2026-08-11T13:27:36.374640+00:00 by `research/scripts/run_pattern_control_suite.py` (`agx_research.patterns.control_suite` v1.0.0), 516s total.

## Purpose (mission Phase 8)

Proves the FULL `discover -> validate -> final_holdout` pipeline, run with the engine's own real, shipped safety gates (`run_robustness=True`, `require_beats_baseline=True` — disabling either would defeat the point of a control suite testing the AS-SHIPPED pipeline), can recover a real, planted relationship (positive controls) and does not *consistently* manufacture a VALIDATED pattern from data carrying no real relationship (negative controls). Every construction and every number below is real: no threshold was loosened and no construction was retried until the suite reported green — see `agx_research.patterns.control_suite`'s module docstring and `agx_research.patterns.candidates`/`engine`'s own `fdr_alpha` docstring for the pre-existing, already-disclosed statistical tradeoff this suite empirically measures rather than invents.

**Regime-conditioned positive control — reduced scope.** Full `discover -> validate -> final_holdout` recovery of a regime-conditioned pattern was attempted (a two-ticker `market_breadth`-gated construction) and, even after disabling two/three-feature interactions to give the regime-conditioning candidate-generation step room under the `max_candidates_per_ticker` budget, zero regime-conditioned candidates survived to `DISCOVERED` — candidate generation itself does produce real, correctly-flagged regime-conditioned candidates in isolation (confirmed directly against the generator, and already covered by the passing unit test `test_pattern_candidates.py::test_regime_conditioned_candidate_has_a_regime_filter_and_higher_complexity`), but none cleared family-correction + BH-FDR inside the full `discover()` run at the sample sizes a 2-ticker synthetic panel affords. This control is therefore verified at the candidate-generation level only, not end-to-end — a disclosed scope limitation, not a fabricated pass. See TD-73.

## Summary

| Control | Kind | Seeds | Rate | Rule | Verdict |
|---|---|---:|---:|---|---|
| momentum | positive | 5/5 | 100% | recovered (>=1 VALIDATED pattern) in a majority (>50%) of seeds | PASS |
| mean_reversion | positive | 5/5 | 100% | recovered (>=1 VALIDATED pattern) in a majority (>50%) of seeds | PASS |
| lead_lag | positive | 5/5 | 100% | recovered (>=1 VALIDATED pattern) in a majority (>50%) of seeds | PASS |
| pure_noise | negative | 2/5 | 40% | false VALIDATED rate <= 40% of seeds (declared, not measured-optimal -- see module docstring) | PASS |
| shuffled_returns | negative | 1/5 | 20% | false VALIDATED rate <= 40% of seeds (declared, not measured-optimal -- see module docstring) | PASS |
| shuffled_timestamps | negative | 0/5 | 0% | false VALIDATED rate <= 40% of seeds (declared, not measured-optimal -- see module docstring) | PASS |
| independent_random_predictor | negative | 2/5 | 40% | false VALIDATED rate <= 40% of seeds (declared, not measured-optimal -- see module docstring) | PASS |
| regime_conditioned (candidate-generation-level only) | positive | n/a | n/a | real, correctly-flagged regime-conditioned candidates are generated | PASS (reduced scope) |

## Positive controls

### momentum

Alternating-block momentum: yesterday's return sign genuinely predicts today's.

| Seed | Candidates | Discovered | Surviving to VALIDATING | VALIDATED |
|---:|---:|---:|---:|---:|
| 1 | 150 | 40 | 4 | 4 |
| 2 | 150 | 43 | 6 | 6 |
| 3 | 150 | 40 | 6 | 6 |
| 4 | 150 | 44 | 6 | 6 |
| 5 | 150 | 41 | 6 | 6 |

### mean_reversion

Daily-alternating drift: today's return genuinely anti-predicts tomorrow's.

| Seed | Candidates | Discovered | Surviving to VALIDATING | VALIDATED |
|---:|---:|---:|---:|---:|
| 1 | 146 | 25 | 4 | 4 |
| 2 | 146 | 24 | 4 | 4 |
| 3 | 146 | 28 | 6 | 5 |
| 4 | 146 | 24 | 4 | 4 |
| 5 | 146 | 24 | 2 | 2 |

### lead_lag

FOLLOWER's return is literally LEADER's lagged return plus tiny noise.

| Seed | Candidates | Discovered | Surviving to VALIDATING | VALIDATED |
|---:|---:|---:|---:|---:|
| 1 | 196 | 75 | 13 | 13 |
| 2 | 196 | 76 | 14 | 14 |
| 3 | 196 | 79 | 13 | 13 |
| 4 | 196 | 78 | 15 | 15 |
| 5 | 196 | 76 | 15 | 15 |

## Negative controls

### pure_noise

Two independent zero-drift-in-expectation random walks.

| Seed | Candidates | Discovered | Surviving to VALIDATING | VALIDATED |
|---:|---:|---:|---:|---:|
| 1 | 150 | 93 | 43 | 0 |
| 2 | 150 | 1 | 0 | 0 |
| 3 | 150 | 11 | 4 | 4 |
| 4 | 150 | 27 | 0 | 0 |
| 5 | 150 | 92 | 52 | 27 |

Falsely VALIDATED pattern(s) on seeds with `VALIDATED > 0` above:
- seed 3: `cross_sectional_dispersion_10d:MARKET > 0.0139 [lag=60d] -> forward_return_5d:A`
- seed 3: `return_3d:B < -0.0048 -> forward_return_5d:B`
- seed 3: `return_3d:B < 0.0012 -> forward_return_5d:B`
- seed 3: `distance_from_low_3d:B < 0.0020 -> forward_return_5d:B`
- seed 5: `return_1d:A < -0.0029 -> forward_return_5d:A`
- seed 5: `return_1d:A < 0.0014 -> forward_return_5d:A`
- seed 5: `return_1d:A < 0.0056 -> forward_return_5d:A`
- seed 5: `acceleration_1d:A > -0.0061 -> forward_return_5d:A`
- seed 5: `return_3d:A < -0.0050 -> forward_return_5d:A`
- seed 5: `return_3d:A < 0.0043 -> forward_return_5d:A`
- seed 5: `return_3d:A < 0.0133 -> forward_return_5d:A`
- seed 5: `distance_from_high_3d:A < -0.0093 -> forward_return_5d:A`
- seed 5: `distance_from_high_3d:A < -0.0027 -> forward_return_5d:A`
- seed 5: `distance_from_low_3d:A < 0.0074 -> forward_return_5d:A`
- seed 5: `distance_from_low_3d:A < 0.0123 -> forward_return_5d:A`
- seed 5: `return_5d:A < -0.0020 -> forward_return_5d:A`
- seed 5: `return_5d:A < 0.0077 -> forward_return_5d:A`
- seed 5: `return_5d:A < 0.0172 -> forward_return_5d:A`
- seed 5: `cross_sectional_dispersion_5d:MARKET > 0.0090 [lag=1d] -> forward_return_5d:A`
- seed 5: `cross_sectional_dispersion_5d:MARKET > 0.0090 [lag=3d] -> forward_return_5d:A`
- seed 5: `cross_sectional_dispersion_5d:MARKET > 0.0090 [lag=60d] -> forward_return_5d:A`
- seed 5: `cross_sectional_dispersion_10d:MARKET > 0.0133 [lag=5d] -> forward_return_5d:A`
- seed 5: `cross_sectional_dispersion_20d:MARKET > 0.0221 [lag=60d] -> forward_return_5d:A`
- seed 5: `market_breadth:MARKET > 0.5000 [lag=10d] -> forward_return_5d:A`
- seed 5: `market_breadth:MARKET > 0.5000 [lag=20d] -> forward_return_5d:A`
- seed 5: `volume_concentration_hhi:MARKET > 0.5001 [lag=10d] -> forward_return_5d:A`
- seed 5: `return_1d:B > 0.0009 [lag=1d] -> forward_return_5d:A`
- seed 5: `return_1d:B > 0.0009 [lag=3d] -> forward_return_5d:A`
- seed 5: `return_5d:B > 0.0041 [lag=1d] -> forward_return_5d:A`
- seed 5: `return_5d:B > 0.0041 [lag=3d] -> forward_return_5d:A`
- seed 5: `return_5d:B > 0.0041 [lag=10d] -> forward_return_5d:A`

### shuffled_returns

The real momentum series with its daily returns fully permuted.

| Seed | Candidates | Discovered | Surviving to VALIDATING | VALIDATED |
|---:|---:|---:|---:|---:|
| 1 | 150 | 17 | 12 | 0 |
| 2 | 150 | 6 | 5 | 0 |
| 3 | 150 | 0 | 0 | 0 |
| 4 | 150 | 4 | 1 | 0 |
| 5 | 150 | 4 | 4 | 1 |

Falsely VALIDATED pattern(s) on seeds with `VALIDATED > 0` above:
- seed 5: `cross_sectional_dispersion_10d:MARKET > 0.0179 [lag=60d] -> forward_return_5d:B`

### shuffled_timestamps

The real momentum series, chunk-shuffled at 2-day granularity.

| Seed | Candidates | Discovered | Surviving to VALIDATING | VALIDATED |
|---:|---:|---:|---:|---:|
| 1 | 150 | 1 | 0 | 0 |
| 2 | 150 | 1 | 1 | 0 |
| 3 | 150 | 6 | 0 | 0 |
| 4 | 150 | 2 | 0 | 0 |
| 5 | 150 | 1 | 0 | 0 |

### independent_random_predictor

Two independent random-walk tickers sharing a sector -- no real lead/lag relationship.

| Seed | Candidates | Discovered | Surviving to VALIDATING | VALIDATED |
|---:|---:|---:|---:|---:|
| 1 | 198 | 1 | 0 | 0 |
| 2 | 198 | 3 | 1 | 1 |
| 3 | 198 | 14 | 0 | 0 |
| 4 | 198 | 5 | 3 | 1 |
| 5 | 198 | 1 | 1 | 0 |

Falsely VALIDATED pattern(s) on seeds with `VALIDATED > 0` above:
- seed 2: `cross_sectional_dispersion_20d:MARKET > 0.0206 [lag=60d] -> forward_return_5d:FOLLOWER2`
- seed 4: `return_5d:LEADER2 > -0.0006 [lag=60d] -> forward_return_5d:FOLLOWER2`

## Interpretation

Positive controls: all three recovered on every seed (5/5, 100%) — the full `discover -> validate -> final_holdout` pipeline, with real safety gates enabled, can and does find a genuine momentum, mean-reversion, or lead/lag relationship when one actually exists.

Negative controls: all four cleared this suite's own declared acceptance ceiling (false-VALIDATED rate <= 40% of seeds), but two of them — `pure_noise` (2/5, 40%) and `independent_random_predictor` (2/5, 40%) — sit exactly at that ceiling, not comfortably below it, and `pure_noise` seed 5 produced a burst of 27 simultaneously-VALIDATED false patterns on one ticker (see the per-seed detail above). This is a real, disclosed limitation, not a hidden one: **TD-72** records the exact numbers, the likely root cause (BH-FDR's guarantee weakening under this engine's necessarily-correlated candidate pool — the same risk `PatternDiscoveryEngineConfig.fdr_alpha`'s own docstring and TD-70 already flagged, now confirmed to survive the *entire* pipeline including final holdout, not just discovery-sample screening), and what fixing it would take. `shuffled_returns` (1/5, 20%) and `shuffled_timestamps` (0/5, 0%) stayed comfortably clean, which suggests the risk concentrates around a single ticker's own real (if directionless-in-expectation) realized-path drift rather than being generic to every negative-control construction. Practical takeaway: a single VALIDATED pattern — especially one of several VALIDATED together for the same ticker in one run — should be treated with real skepticism until TD-72's mitigation work lands, not treated as settled evidence on its own.

