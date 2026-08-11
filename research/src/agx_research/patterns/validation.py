"""Chronological, purged, embargoed walk-forward validation.

No random train/test splitting anywhere in this module, per the mission's
explicit requirement — every split is index-ordered by date.
`purge_and_embargo()` implements the López de Prado-style purge: any
training observation whose own target window `[train_date, train_date +
horizon_days]` would overlap the test period is dropped, plus a further
`embargo_days` buffer immediately before the test window, because this
codebase's forward-return targets are themselves overlapping (adjacent
anchor dates share most of their forward window) — nothing in this
codebase implemented this before (`grep purg|embargo` across the
repository was empty prior to this mission; `validation.backtest` and
`investment_proof.walk_forward` both hold out a single trailing tail, not
purged rolling folds).

A candidate "survives" only if it clears an out-of-sample sample-size
floor *and* its out-of-sample expectancy agrees in sign with its
discovery-sample expectancy — never because it looked good on the data it
was found in (mission: "a pattern is NOT validated because it works on
the full historical dataset").
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from agx_research.patterns.candidates import PatternCandidate
from agx_research.patterns.evaluation import OutcomeDistribution, evaluate_outcomes
from agx_research.patterns.features import FeatureSeries
from agx_research.patterns.targets import TargetSeries


def chronological_split(dates: list[date], *, train_fraction: float = 0.7) -> tuple[list[date], list[date]]:
    """A single, date-ordered (never random) train/test split."""
    ordered = sorted(dates)
    split = int(len(ordered) * train_fraction)
    return ordered[:split], ordered[split:]


def walk_forward_index_folds(
    n: int, *, n_folds: int, min_train_size: int
) -> list[tuple[int, int, int, int]]:
    """Expanding-window walk-forward fold boundaries as
    `(train_start_idx, train_end_idx_exclusive, test_start_idx, test_end_idx_exclusive)`,
    over positions `0..n-1` of a date-ordered anchor sequence."""
    if n < min_train_size + n_folds:
        return []
    remaining = n - min_train_size
    test_size = max(1, remaining // n_folds)
    folds: list[tuple[int, int, int, int]] = []
    train_end = min_train_size
    fold_index = 0
    while train_end < n and fold_index < n_folds:
        test_end = min(n, train_end + test_size)
        if test_end <= train_end:
            break
        folds.append((0, train_end, train_end, test_end))
        train_end = test_end
        fold_index += 1
    return folds


def purge_and_embargo(
    train_end_idx: int, test_start_idx: int, *, horizon_days: int, embargo_days: int
) -> int:
    """The adjusted (shrunk) `train_end_idx` after removing every training
    position whose forward-looking target window could overlap the test
    window, plus an extra `embargo_days` buffer."""
    purge_boundary = test_start_idx - horizon_days - embargo_days
    return min(train_end_idx, max(0, purge_boundary))


class FoldResult(BaseModel):
    fold_index: int
    train_sample_size: int
    test_sample_size: int
    train_distribution: OutcomeDistribution | None = None
    test_distribution: OutcomeDistribution | None = None


class WalkForwardResult(BaseModel):
    candidate_id: str
    n_folds_attempted: int
    n_folds_valid: int
    folds: list[FoldResult] = Field(default_factory=list)
    discovery_distribution: OutcomeDistribution | None = None
    oos_distribution: OutcomeDistribution | None = None
    oos_sample_size: int = 0
    oos_period: tuple[date, date] | None = None
    survived: bool = False
    reasons: list[str] = Field(default_factory=list)


class WalkForwardValidatorConfig(BaseModel):
    n_folds: int = 4
    min_train_size: int = 30
    min_oos_sample_size: int = 10
    embargo_days: int = 2


class WalkForwardValidator:
    def __init__(self, config: WalkForwardValidatorConfig | None = None):
        self.config = config or WalkForwardValidatorConfig()

    def validate(
        self,
        candidate: PatternCandidate,
        *,
        anchor_dates: list[date],
        feature_lookup: dict[str, FeatureSeries],
        target: TargetSeries,
    ) -> WalkForwardResult:
        ordered_dates = sorted(anchor_dates)
        horizon = target.spec.horizon_days
        raw_folds = walk_forward_index_folds(
            len(ordered_dates), n_folds=self.config.n_folds, min_train_size=self.config.min_train_size
        )

        fold_results: list[FoldResult] = []
        oos_outcomes: list[float] = []
        oos_dates: list[date] = []
        for fold_index, (train_start_idx, train_end_idx, test_start_idx, test_end_idx) in enumerate(raw_folds):
            purged_train_end = purge_and_embargo(
                train_end_idx, test_start_idx, horizon_days=horizon, embargo_days=self.config.embargo_days
            )
            train_dates = ordered_dates[train_start_idx:purged_train_end]
            test_dates = ordered_dates[test_start_idx:test_end_idx]
            train_matched = self._matched_outcomes(candidate, train_dates, feature_lookup, target)
            test_matched = self._matched_outcomes(candidate, test_dates, feature_lookup, target)
            fold_results.append(
                FoldResult(
                    fold_index=fold_index,
                    train_sample_size=len(train_matched),
                    test_sample_size=len(test_matched),
                    train_distribution=evaluate_outcomes(
                        [v for _, v in train_matched], dates=[d for d, _ in train_matched]
                    ),
                    test_distribution=evaluate_outcomes(
                        [v for _, v in test_matched], dates=[d for d, _ in test_matched]
                    ),
                )
            )
            oos_outcomes.extend(v for _, v in test_matched)
            oos_dates.extend(d for d, _ in test_matched)

        full_matched = self._matched_outcomes(candidate, ordered_dates, feature_lookup, target)
        discovery_distribution = evaluate_outcomes(
            [v for _, v in full_matched], dates=[d for d, _ in full_matched]
        )
        oos_distribution = evaluate_outcomes(oos_outcomes, dates=oos_dates)

        reasons: list[str] = []
        survived = True
        if not raw_folds:
            survived = False
            reasons.append(
                f"Not enough anchor observations ({len(ordered_dates)}) for "
                f"{self.config.n_folds}-fold walk-forward with min_train_size="
                f"{self.config.min_train_size}."
            )
        elif oos_distribution is None or oos_distribution.sample_count < self.config.min_oos_sample_size:
            survived = False
            reasons.append(
                f"Out-of-sample sample size "
                f"{oos_distribution.sample_count if oos_distribution else 0} below floor "
                f"{self.config.min_oos_sample_size}."
            )
        elif discovery_distribution is not None and (
            (oos_distribution.expectancy > 0) != (discovery_distribution.expectancy > 0)
        ):
            survived = False
            reasons.append("Out-of-sample expectancy sign disagrees with the discovery-sample sign.")
        else:
            reasons.append(
                "Out-of-sample expectancy agrees in sign with the discovery sample and clears "
                "the out-of-sample sample-size floor."
            )

        return WalkForwardResult(
            candidate_id=candidate.id,
            n_folds_attempted=self.config.n_folds,
            n_folds_valid=len(raw_folds),
            folds=fold_results,
            discovery_distribution=discovery_distribution,
            oos_distribution=oos_distribution,
            oos_sample_size=oos_distribution.sample_count if oos_distribution else 0,
            oos_period=(min(oos_dates), max(oos_dates)) if oos_dates else None,
            survived=survived,
            reasons=reasons,
        )

    @staticmethod
    def _matched_outcomes(
        candidate: PatternCandidate,
        dates: list[date],
        feature_lookup: dict[str, FeatureSeries],
        target: TargetSeries,
    ) -> list[tuple[date, float]]:
        out: list[tuple[date, float]] = []
        for d in dates:
            value = target.value_at(d)
            if value is None:
                continue
            if candidate.matches(feature_lookup, d):
                out.append((d, value))
        return out


__all__ = [
    "FoldResult",
    "WalkForwardResult",
    "WalkForwardValidator",
    "WalkForwardValidatorConfig",
    "chronological_split",
    "purge_and_embargo",
    "walk_forward_index_folds",
]
