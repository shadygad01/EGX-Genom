"""Strengthened multiple-testing control (Mission 2, Phase 7).

`multiple_testing.benjamini_hochberg()` (Mission 1) already controls the
expected false-discovery *proportion* across every candidate tested, but
Mission 1's own real-data finding — documented in `docs/
PATTERN_DISCOVERY_REPORT.md` — showed BH's guarantee weakens when many
tested candidates are mutually correlated (near-duplicate threshold/
window variants of one underlying feature idea), letting more nominal
survivors through on pure noise than the textbook guarantee suggests.
This module adds three further, real, independently-computed layers,
per the mission's explicit ask — none of them replace BH-FDR or the
existing match-set redundancy pruning (`candidates.py`), all of them
stack on top:

1. **Hypothesis-family accounting** (`candidate_family_key`) — groups
   candidates that are really re-testing the same underlying idea
   (same ticker, same target, the same primary feature's window-stripped
   base, same regime-conditioning status) so a family's size is visible
   and auditable, not hidden inside a flat candidate count.
2. **Family-size correction** (`family_corrected_p_value`) — a
   Bonferroni-style penalty scaled by how many candidates *within the
   same family* were tried, applied in addition to (never instead of)
   the global BH-FDR pass across every family combined.
3. **Block-bootstrap significance** (`block_bootstrap_p_value`) — resamples
   a candidate's own matched-outcome sequence in contiguous blocks
   (preserving local/serial dependence, the same reasoning
   `hypotheses.experiment_factory.BootstrapExperiment` already uses for
   this codebase's price-return series) rather than i.i.d., which is the
   statistically appropriate resampling scheme for the kind of serially-
   dependent financial outcome series a candidate's forward-return
   matches actually are. This is a real, more conservative significance
   check than `evaluation.py`'s existing i.i.d. bootstrap p-value — it is
   *not* a full re-simulation of candidate generation across bootstrap
   replicates (White's Reality Check / Hansen's SPA test in their full
   form), which would require regenerating and re-screening the entire
   candidate pool per replicate; that full form is documented here as
   the honest scope limitation, not silently implied to already exist.
4. **Deflated performance metrics** (`deflated_sharpe_ratio`) — Bailey &
   López de Prado (2014)'s closed-form Probabilistic/Deflated Sharpe
   Ratio: adjusts a Sharpe-like statistic's significance for the number
   of trials searched, the sample size, and the outcome distribution's
   skewness/kurtosis. A DSR well below 0.95 means the observed statistic
   is plausibly explained by data-mining across that many trials alone.
"""

from __future__ import annotations

import math
import random
import re
import statistics

from scipy import stats as scipy_stats

from agx_research.patterns.candidates import PatternCandidate

EULER_MASCHERONI = 0.5772156649015329


def candidate_family_key(candidate: PatternCandidate) -> str:
    if not candidate.conditions:
        base = "no_condition"
    else:
        base = re.sub(r"_\d+d(?=:)", "", candidate.conditions[0].feature_id)
    regime = "regime" if candidate.regime_filter else "no_regime"
    return f"{candidate.ticker}|{base}|{candidate.target_id}|{regime}"


def group_by_family(candidates: list[PatternCandidate]) -> dict[str, list[PatternCandidate]]:
    families: dict[str, list[PatternCandidate]] = {}
    for candidate in candidates:
        families.setdefault(candidate_family_key(candidate), []).append(candidate)
    return families


def family_corrected_p_value(p_value: float, family_size: int) -> float:
    return min(1.0, p_value * max(1, family_size))


def block_bootstrap_p_value(
    outcomes: list[float], *, iterations: int = 1000, seed: int = 42, block_size: int | None = None
) -> float:
    """Two-sided significance of `mean(outcomes) != 0` under a moving-
    block bootstrap over the outcomes in their own chronological order
    (caller must pass them already date-sorted) — preserves local serial
    dependence, unlike an i.i.d. resample. Mirrors
    `hypotheses.experiment_factory.BootstrapExperiment`'s exact block-size
    heuristic (`n ** (1/3)`) and p-value construction for consistency
    with the rest of this codebase's bootstrap methodology."""
    n = len(outcomes)
    if n < 5:
        return 1.0
    rng = random.Random(seed)
    block = block_size or max(2, round(n ** (1 / 3)))
    block = min(block, n)
    observed_mean = statistics.fmean(outcomes)

    resampled_means = []
    for _ in range(iterations):
        indices: list[int] = []
        while len(indices) < n:
            start = rng.randrange(n)
            indices.extend((start + offset) % n for offset in range(block))
        indices = indices[:n]
        resampled_means.append(statistics.fmean(outcomes[i] for i in indices))

    opposite_side = sum(1 for m in resampled_means if (m <= 0) != (observed_mean <= 0))
    return min(1.0, 2 * min(opposite_side, iterations - opposite_side) / iterations)


def sharpe_like_statistic(outcomes: list[float]) -> float:
    if len(outcomes) < 2:
        return 0.0
    std = statistics.pstdev(outcomes)
    return statistics.fmean(outcomes) / std if std > 0 else 0.0


def expected_max_sharpe_under_noise(n_trials: int, sharpe_variance: float) -> float:
    """Bailey & López de Prado (2014): the expected maximum Sharpe ratio
    achievable purely by chance across `n_trials` independent attempts,
    each with Sharpe-estimate variance `sharpe_variance`."""
    if n_trials <= 1 or sharpe_variance <= 0:
        return 0.0
    return math.sqrt(sharpe_variance) * (
        (1 - EULER_MASCHERONI) * scipy_stats.norm.ppf(1 - 1 / n_trials)
        + EULER_MASCHERONI * scipy_stats.norm.ppf(1 - 1 / (n_trials * math.e))
    )


def deflated_sharpe_ratio(
    outcomes: list[float], *, n_trials: int, sharpe_variance: float = 1.0
) -> float | None:
    """Returns the DSR — the probability the *true* Sharpe ratio exceeds
    the noise-adjusted benchmark `expected_max_sharpe_under_noise(n_trials, ...)`,
    given the observed outcome sample's own skewness/kurtosis. `None` when
    there isn't enough sample to compute skew/kurtosis meaningfully.
    A DSR well below 0.95 means the observed Sharpe-like statistic is
    plausibly just the best of `n_trials` noise draws, not a real edge."""
    if len(outcomes) < 5:
        return None
    observed_sharpe = sharpe_like_statistic(outcomes)
    sr0 = expected_max_sharpe_under_noise(n_trials, sharpe_variance)
    skewness = float(scipy_stats.skew(outcomes))
    kurtosis = float(scipy_stats.kurtosis(outcomes, fisher=False))  # Pearson kurtosis (normal = 3)
    denominator = max(
        1e-9, 1 - skewness * observed_sharpe + ((kurtosis - 1) / 4) * observed_sharpe**2
    )
    z = (observed_sharpe - sr0) * math.sqrt(len(outcomes) - 1) / math.sqrt(denominator)
    return float(scipy_stats.norm.cdf(z))


__all__ = [
    "EULER_MASCHERONI",
    "block_bootstrap_p_value",
    "candidate_family_key",
    "deflated_sharpe_ratio",
    "expected_max_sharpe_under_noise",
    "family_corrected_p_value",
    "group_by_family",
    "sharpe_like_statistic",
]
