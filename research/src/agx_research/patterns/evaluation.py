"""Discovery statistics: turns a candidate's matched outcome sample into
the metrics the mission requires ("never rank patterns by raw return
alone").

`confidence_interval_95` is a plain i.i.d. percentile bootstrap over the
matched-outcome sample, not a moving-block bootstrap like
`hypotheses.experiment_factory.BootstrapExperiment` — deliberately: that
experiment resamples a *contiguous* daily-return series where blocking
preserves real serial dependence, while a pattern's matched outcomes are
an irregular subset of trigger dates whose own targets may still overlap
in calendar time. That overlap is exactly what `validation.py`'s
purge/embargo walk-forward exists to handle at the *validation* stage —
this module only describes the discovery-sample distribution, it does not
itself claim statistical significance.
"""

from __future__ import annotations

import random
import statistics
from datetime import date

from pydantic import BaseModel


class OutcomeDistribution(BaseModel):
    sample_count: int
    hit_rate: float
    mean_outcome: float
    median_outcome: float
    expectancy: float
    stdev: float
    downside_deviation: float
    mfe_mean: float | None = None
    mae_mean: float | None = None
    profit_factor: float | None = None
    max_drawdown_mean: float | None = None
    confidence_interval_95: tuple[float, float] | None = None
    stability_score: float | None = None
    p_value_bootstrap: float | None = None


def _bootstrap(
    outcomes: list[float], *, iterations: int, seed: int, alpha: float
) -> tuple[tuple[float, float], float]:
    """Returns `(confidence_interval, two_sided_p_value)`. The p-value is
    the same construction `hypotheses.experiment_factory.BootstrapExperiment`
    uses: twice the smaller tail of resampled means falling on the
    opposite side of zero from the observed mean, capped at 1 — a
    nonparametric significance read consistent with the rest of this
    codebase's bootstrap methodology, not a fresh invention."""
    rng = random.Random(seed)
    n = len(outcomes)
    means = [
        statistics.fmean(outcomes[rng.randrange(n)] for _ in range(n)) for _ in range(iterations)
    ]
    observed_mean = statistics.fmean(outcomes)
    opposite_side = sum(1 for m in means if (m <= 0) != (observed_mean <= 0))
    p_value = min(1.0, 2 * min(opposite_side, iterations - opposite_side) / iterations)
    means.sort()
    lower_idx = max(0, int((alpha / 2) * iterations))
    upper_idx = min(iterations - 1, int((1 - alpha / 2) * iterations))
    return (means[lower_idx], means[upper_idx]), p_value


def _stability_score(outcomes: list[float], dates: list[date], n_buckets: int) -> float | None:
    if len(outcomes) < n_buckets * 2:
        return None
    order = sorted(range(len(outcomes)), key=lambda i: dates[i])
    ordered_outcomes = [outcomes[i] for i in order]
    bucket_size = len(ordered_outcomes) // n_buckets
    overall_sign = statistics.fmean(ordered_outcomes) >= 0
    agreeing = 0
    for b in range(n_buckets):
        start = b * bucket_size
        end = len(ordered_outcomes) if b == n_buckets - 1 else start + bucket_size
        chunk = ordered_outcomes[start:end]
        if not chunk:
            continue
        if (statistics.fmean(chunk) >= 0) == overall_sign:
            agreeing += 1
    return agreeing / n_buckets


def evaluate_outcomes(
    outcomes: list[float],
    *,
    dates: list[date] | None = None,
    mfe: list[float] | None = None,
    mae: list[float] | None = None,
    drawdowns: list[float] | None = None,
    bootstrap_iterations: int = 1000,
    seed: int = 42,
    n_time_buckets: int = 4,
) -> OutcomeDistribution | None:
    """None (never a fabricated statistic) when fewer than 2 observations
    exist — matching every other "not enough data" refusal in this
    codebase (e.g. `hypotheses.experiment_factory`'s experiments)."""
    if len(outcomes) < 2:
        return None

    mean_outcome = statistics.fmean(outcomes)
    downside = [min(0.0, o) for o in outcomes]
    positive_sum = sum(o for o in outcomes if o > 0)
    negative_sum = sum(o for o in outcomes if o < 0)
    ci, p_value = _bootstrap(outcomes, iterations=bootstrap_iterations, seed=seed, alpha=0.05)

    return OutcomeDistribution(
        sample_count=len(outcomes),
        hit_rate=sum(1 for o in outcomes if o > 0) / len(outcomes),
        mean_outcome=mean_outcome,
        median_outcome=statistics.median(outcomes),
        expectancy=mean_outcome,
        stdev=statistics.pstdev(outcomes),
        downside_deviation=(sum(d * d for d in downside) / len(downside)) ** 0.5,
        mfe_mean=statistics.fmean(mfe) if mfe else None,
        mae_mean=statistics.fmean(mae) if mae else None,
        profit_factor=(positive_sum / abs(negative_sum)) if negative_sum != 0 else None,
        max_drawdown_mean=statistics.fmean(drawdowns) if drawdowns else None,
        confidence_interval_95=ci,
        stability_score=(
            _stability_score(outcomes, dates, n_time_buckets) if dates is not None else None
        ),
        p_value_bootstrap=p_value,
    )


__all__ = ["OutcomeDistribution", "evaluate_outcomes"]
