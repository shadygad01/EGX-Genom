"""Positive/negative control suite for the pattern discovery engine
(mission Phase 8): proves the FULL `discover -> validate -> final_holdout`
pipeline can recover a real, planted relationship (positive controls) and
does not *consistently* manufacture a VALIDATED pattern from data that
carries no real relationship (negative controls).

Every control (except `regime_conditioned` -- see its own docstring for
why it is scoped to candidate generation only) runs through the exact
same `PatternDiscoveryEngine` any real panel would, with the engine's own
real, shipped safety gates (`run_robustness=True`,
`require_beats_baseline=True`) -- disabling either for speed would defeat
the entire purpose of a control suite whose job is to test whether the
AS-SHIPPED pipeline is honest, not a weakened stand-in for it.

A negative control's false-positive rate is reported honestly, whatever
it is -- this module makes no attempt to tune constructions or thresholds
until a control "passes"; see `docs/PATTERN_DISCOVERY_CONTROL_SUITE.md`
for the persisted results of an actual run, including a disclosed
limitation this suite itself discovered (`independent_random_predictor`
occasionally leaks false VALIDATED lead/lag patterns -- see TD-72).
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from agx_research.patterns.candidates import CandidateGeneratorConfig
from agx_research.patterns.engine import PatternDiscoveryEngine, PatternDiscoveryEngineConfig
from agx_research.patterns.multiple_testing import TestingLedgerRepository
from agx_research.patterns.panel import ResearchPanel, TickerSeries
from agx_research.patterns.registry import PatternRegistry, PatternStatus
from agx_research.patterns.validation import WalkForwardValidatorConfig

CONTROL_SUITE_VERSION = "1.0.0"


def _trading_dates(start: date, n: int) -> list[date]:
    dates: list[date] = []
    current = start
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _bars(ticker: str, dates: list[date], closes: list[float], volume: list[int], sector: str) -> TickerSeries:
    return TickerSeries(
        ticker=ticker,
        dates=dates,
        open=[closes[0], *closes[:-1]],
        high=[c * 1.002 for c in closes],
        low=[c * 0.998 for c in closes],
        close=closes,
        adjusted_close=list(closes),
        volume=volume,
        sector=sector,
    )


def _volume(n_days: int, seed: int, base: int = 100_000) -> list[int]:
    rng = random.Random(seed)
    return [base + rng.randint(-5_000, 5_000) for _ in range(n_days)]


def _block_momentum_closes(
    n_days: int, seed: int, *, block_length: int, daily_drift: float, noise_stdev: float
) -> list[float]:
    """The same construction `pattern_test_helpers.make_deterministic_ticker_series`
    uses -- alternating up/down blocks -- reimplemented here (not imported
    from `tests/`) because this module is production code, not a test
    fixture: a control suite that ships as `agx research control-suite`
    must not depend on `tests/`."""
    rng = random.Random(seed)
    closes = [100.0]
    for i in range(1, n_days):
        block = (i // block_length) % 2
        drift = daily_drift if block == 0 else -daily_drift
        closes.append(closes[-1] * (1 + drift + rng.gauss(0, noise_stdev)))
    return closes


def _pure_noise_closes(n_days: int, seed: int, noise_stdev: float = 0.008) -> list[float]:
    rng = random.Random(seed)
    closes = [100.0]
    for _ in range(1, n_days):
        closes.append(closes[-1] * (1 + rng.gauss(0, noise_stdev)))
    return closes


def _daily_returns(closes: list[float]) -> list[float]:
    return [0.0] + [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]


def _closes_from_returns(returns: list[float]) -> list[float]:
    closes = [100.0]
    for r in returns[1:]:
        closes.append(closes[-1] * (1 + r))
    return closes


def _permute_returns(closes: list[float], seed: int) -> list[float]:
    """Full i.i.d. random permutation of the daily-return sequence -- the
    standard "scrambled returns" permutation-test negative control.
    Rebuilding prices from a shuffled RETURN sequence (not shuffled price
    LEVELS) keeps every daily move physically realistic; the exact same
    marginal return distribution survives, only the temporal order (and
    therefore any real autocorrelation/momentum structure) is destroyed."""
    rng = random.Random(seed)
    returns = _daily_returns(closes)
    tail = returns[1:]
    rng.shuffle(tail)
    return _closes_from_returns([0.0, *tail])


def _block_permute_returns(closes: list[float], seed: int, chunk_size: int) -> list[float]:
    """Shuffles fixed-size contiguous CHUNKS of the daily-return sequence
    rather than individual days -- a coarser, distinct "timestamp
    misalignment" negative control (data genuinely misfiled by a chunk of
    days, not scrambled to an arbitrary day). `chunk_size` must be kept
    smaller than the shortest target horizon under test, or within-chunk
    short-horizon structure survives the shuffle untouched and this stops
    being a clean negative control (verified empirically against the
    momentum construction's own 10-day block period -- see
    docs/PATTERN_DISCOVERY_CONTROL_SUITE.md)."""
    rng = random.Random(seed)
    returns = _daily_returns(closes)
    n = len(returns)
    chunks = [list(range(i, min(i + chunk_size, n))) for i in range(0, n, chunk_size)]
    rng.shuffle(chunks)
    idx = [i for chunk in chunks for i in chunk]
    reordered = [returns[i] for i in idx]
    return _closes_from_returns(reordered)


# ---- shared engine configuration ----
#
# "Own-ticker" controls (momentum, mean_reversion, pure_noise,
# shuffled_returns, shuffled_timestamps) reuse the exact configuration
# `test_pattern_engine.py`'s own momentum regression test already proved
# recovers a real relationship -- a declared, generous-but-real synthetic
# configuration (see that test's docstring), not tuned per control here.
_OWN_TICKER_CANDIDATE_CONFIG = CandidateGeneratorConfig(
    min_sample_size=15,
    correlation_prune_threshold=0.8,
    max_candidates_per_ticker=40,
    enable_three_feature=False,
    enable_regime_conditioning=False,
)
# Lead/lag controls (lead_lag, independent_random_predictor) disable
# two/three-feature interactions and use a tighter correlation-prune
# threshold to isolate lead/lag search from the ordinary same-ticker
# candidate pool, matching `test_pattern_lead_lag.py`'s own convention.
_LEAD_LAG_CANDIDATE_CONFIG = CandidateGeneratorConfig(
    min_sample_size=15,
    correlation_prune_threshold=0.999,
    max_candidates_per_ticker=60,
    enable_two_feature=False,
    enable_three_feature=False,
    enable_regime_conditioning=False,
)
_WALK_FORWARD_CONFIG = WalkForwardValidatorConfig(n_folds=3, min_train_size=40, min_oos_sample_size=8, embargo_days=2)


def _own_ticker_engine_config() -> PatternDiscoveryEngineConfig:
    return PatternDiscoveryEngineConfig(
        candidate_config=_OWN_TICKER_CANDIDATE_CONFIG,
        walk_forward_config=_WALK_FORWARD_CONFIG,
        fdr_alpha=0.10,
        run_robustness=True,
        require_beats_baseline=True,
        horizons=(5,),
        enable_barrier_targets=False,
        enable_lead_lag=True,
    )


def _lead_lag_engine_config() -> PatternDiscoveryEngineConfig:
    return PatternDiscoveryEngineConfig(
        candidate_config=_LEAD_LAG_CANDIDATE_CONFIG,
        walk_forward_config=_WALK_FORWARD_CONFIG,
        fdr_alpha=0.10,
        run_robustness=True,
        require_beats_baseline=True,
        horizons=(5,),
        enable_barrier_targets=False,
        enable_lead_lag=True,
    )


# ---- panel builders ----


def build_momentum_panel(seed: int) -> ResearchPanel:
    """Positive control: a real, planted, alternating-block momentum
    relationship -- yesterday's return sign genuinely predicts today's."""
    a = _bars(
        "A", _trading_dates(date(2020, 1, 2), 200),
        _block_momentum_closes(200, seed * 2 + 11, block_length=10, daily_drift=0.01, noise_stdev=0.0005),
        _volume(200, seed * 2 + 11), "Banks",
    )
    b = _bars(
        "B", _trading_dates(date(2020, 1, 2), 200),
        _block_momentum_closes(200, seed * 2 + 22, block_length=13, daily_drift=0.008, noise_stdev=0.0006),
        _volume(200, seed * 2 + 22), "Banks",
    )
    return ResearchPanel(as_of=a.dates[-1], tickers=["A", "B"], series={"A": a, "B": b}, sectors={"A": "Banks", "B": "Banks"})


def build_mean_reversion_panel(seed: int) -> ResearchPanel:
    """Positive control: block_length=1 flips the momentum construction's
    own drift sign every single day -- a real, planted day-to-day
    reversal (today's return anti-predicts tomorrow's)."""
    a = _bars(
        "A", _trading_dates(date(2020, 1, 2), 200),
        _block_momentum_closes(200, seed * 2 + 11, block_length=1, daily_drift=0.01, noise_stdev=0.0005),
        _volume(200, seed * 2 + 11), "Banks",
    )
    b = _bars(
        "B", _trading_dates(date(2020, 1, 2), 200),
        _block_momentum_closes(200, seed * 2 + 22, block_length=1, daily_drift=0.008, noise_stdev=0.0006),
        _volume(200, seed * 2 + 22), "Banks",
    )
    return ResearchPanel(as_of=a.dates[-1], tickers=["A", "B"], series={"A": a, "B": b}, sectors={"A": "Banks", "B": "Banks"})


def build_lead_lag_panel(seed: int) -> ResearchPanel:
    """Positive control: FOLLOWER's own daily return at day `i` is
    deliberately built to equal LEADER's daily return at day `i - lag`
    (plus tiny noise) -- a genuine, real, planted
    `LEADER.return_1d(t-lag) -> FOLLOWER's forward return` relationship.
    FOLLOWER's volume is kept well below LEADER's so LEADER is
    unambiguously the sector's volume leader (see `engine._sector_leaders`)."""
    n_days = 260
    lag = 3
    dates = _trading_dates(date(2020, 1, 2), n_days)
    leader_closes = _block_momentum_closes(
        n_days, seed * 2 + 3, block_length=10, daily_drift=0.012, noise_stdev=0.0003
    )
    leader_daily_returns = _daily_returns(leader_closes)
    rng = random.Random(seed * 2 + 101)
    follower_closes = [100.0]
    for i in range(1, n_days):
        driver = leader_daily_returns[i - lag] if i - lag >= 0 else 0.0
        follower_closes.append(follower_closes[-1] * (1 + driver + rng.gauss(0, 0.00005)))
    leader = _bars("LEADER", dates, leader_closes, _volume(n_days, seed * 2 + 3, base=200_000), "Banks")
    follower = _bars("FOLLOWER", dates, follower_closes, [50_000] * n_days, "Banks")
    return ResearchPanel(
        as_of=dates[-1], tickers=["LEADER", "FOLLOWER"], series={"LEADER": leader, "FOLLOWER": follower},
        sectors={"LEADER": "Banks", "FOLLOWER": "Banks"},
    )


def build_pure_noise_panel(seed: int) -> ResearchPanel:
    """Negative control: two independent zero-drift-in-expectation random
    walks -- no real relationship of any kind, own-ticker or cross-ticker."""
    n_days = 200
    a = _bars(
        "A", _trading_dates(date(2020, 1, 2), n_days), _pure_noise_closes(n_days, seed * 2 + 1),
        _volume(n_days, seed * 2 + 1), "Noise",
    )
    b = _bars(
        "B", _trading_dates(date(2020, 1, 2), n_days), _pure_noise_closes(n_days, seed * 2 + 2),
        _volume(n_days, seed * 2 + 2), "Noise",
    )
    return ResearchPanel(as_of=a.dates[-1], tickers=["A", "B"], series={"A": a, "B": b}, sectors={"A": "Noise", "B": "Noise"})


def build_shuffled_returns_panel(seed: int) -> ResearchPanel:
    """Negative control: the SAME real momentum-positive-control price
    series, with its daily-return sequence fully permuted before
    reconstructing prices -- same marginal return distribution (so
    buy-and-hold baseline is a fair, meaningful bar), momentum/
    autocorrelation structure destroyed."""
    n_days = 200
    a_real = _block_momentum_closes(n_days, 11, block_length=10, daily_drift=0.01, noise_stdev=0.0005)
    b_real = _block_momentum_closes(n_days, 22, block_length=13, daily_drift=0.008, noise_stdev=0.0006)
    a = _bars(
        "A", _trading_dates(date(2020, 1, 2), n_days), _permute_returns(a_real, seed * 2 + 1),
        _volume(n_days, seed * 2 + 1), "Banks",
    )
    b = _bars(
        "B", _trading_dates(date(2020, 1, 2), n_days), _permute_returns(b_real, seed * 2 + 2),
        _volume(n_days, seed * 2 + 2), "Banks",
    )
    return ResearchPanel(as_of=a.dates[-1], tickers=["A", "B"], series={"A": a, "B": b}, sectors={"A": "Banks", "B": "Banks"})


def build_shuffled_timestamps_panel(seed: int) -> ResearchPanel:
    """Negative control: the same real momentum series, chunk-shuffled at
    a 2-day granularity (smaller than the shortest target horizon under
    test) -- a coarser, distinct "records attributed to the wrong nearby
    date" corruption from `shuffled_returns`' full single-day permutation."""
    n_days = 200
    a_real = _block_momentum_closes(n_days, 11, block_length=10, daily_drift=0.01, noise_stdev=0.0005)
    b_real = _block_momentum_closes(n_days, 22, block_length=13, daily_drift=0.008, noise_stdev=0.0006)
    a = _bars(
        "A", _trading_dates(date(2020, 1, 2), n_days), _block_permute_returns(a_real, seed * 2 + 1, chunk_size=2),
        _volume(n_days, seed * 2 + 1), "Banks",
    )
    b = _bars(
        "B", _trading_dates(date(2020, 1, 2), n_days), _block_permute_returns(b_real, seed * 2 + 2, chunk_size=2),
        _volume(n_days, seed * 2 + 2), "Banks",
    )
    return ResearchPanel(as_of=a.dates[-1], tickers=["A", "B"], series={"A": a, "B": b}, sectors={"A": "Banks", "B": "Banks"})


def build_independent_random_predictor_panel(seed: int) -> ResearchPanel:
    """Negative control: two independent random-walk tickers in the SAME
    sector (so `engine._sector_leaders` designates one as the other's
    lead/lag predictor source) with no real cross-ticker relationship --
    exercises the exact lead/lag cross-ticker `feature_lookup` machinery
    the positive `lead_lag` control and the `final_holdout()` regression
    fix (`test_pattern_lead_lag.py`) both depend on, from the opposite
    direction."""
    n_days = 220
    dates = _trading_dates(date(2020, 1, 2), n_days)
    leader = _bars(
        "LEADER2", dates, _pure_noise_closes(n_days, seed * 2 + 41),
        [v + 20_000 for v in _volume(n_days, seed * 2 + 41)], "Retail",
    )
    follower = _bars("FOLLOWER2", dates, _pure_noise_closes(n_days, seed * 2 + 42), _volume(n_days, seed * 2 + 42), "Retail")
    return ResearchPanel(
        as_of=dates[-1], tickers=["LEADER2", "FOLLOWER2"], series={"LEADER2": leader, "FOLLOWER2": follower},
        sectors={"LEADER2": "Retail", "FOLLOWER2": "Retail"},
    )


class ControlKind(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class ControlSeedResult(BaseModel):
    seed: int
    candidates_generated: int
    patterns_discovered: int
    patterns_surviving_to_validating: int
    patterns_validated: int
    validated_definitions: list[str] = Field(default_factory=list)


class ControlSummary(BaseModel):
    control_name: str
    kind: ControlKind
    description: str
    seeds_run: int
    seeds_with_at_least_one_validated: int
    rate: float
    acceptance_rule: str
    passed: bool
    per_seed: list[ControlSeedResult]
    notes: list[str] = Field(default_factory=list)


class ControlSuiteReport(BaseModel):
    control_suite_version: str
    summaries: list[ControlSummary]


_ENGINE_BY_CONTROL = {
    "momentum": _own_ticker_engine_config,
    "mean_reversion": _own_ticker_engine_config,
    "pure_noise": _own_ticker_engine_config,
    "shuffled_returns": _own_ticker_engine_config,
    "shuffled_timestamps": _own_ticker_engine_config,
    "lead_lag": _lead_lag_engine_config,
    "independent_random_predictor": _lead_lag_engine_config,
}

_PANEL_BUILDER_BY_CONTROL = {
    "momentum": build_momentum_panel,
    "mean_reversion": build_mean_reversion_panel,
    "lead_lag": build_lead_lag_panel,
    "pure_noise": build_pure_noise_panel,
    "shuffled_returns": build_shuffled_returns_panel,
    "shuffled_timestamps": build_shuffled_timestamps_panel,
    "independent_random_predictor": build_independent_random_predictor_panel,
}


def run_control(name: str, kind: ControlKind, seeds: list[int], *, description: str) -> ControlSummary:
    panel_builder = _PANEL_BUILDER_BY_CONTROL[name]
    engine_config_factory = _ENGINE_BY_CONTROL[name]
    per_seed: list[ControlSeedResult] = []
    for seed in seeds:
        panel = panel_builder(seed)
        registry = PatternRegistry()
        engine = PatternDiscoveryEngine(
            pattern_registry=registry,
            testing_ledger_repository=TestingLedgerRepository(),
            config=engine_config_factory(),
        )
        discover_report = engine.discover(panel)
        validate_report = engine.validate(panel)
        holdout_report = engine.final_holdout(panel)
        validated = registry.by_status(PatternStatus.VALIDATED)
        per_seed.append(
            ControlSeedResult(
                seed=seed,
                candidates_generated=discover_report.candidates_generated,
                patterns_discovered=discover_report.patterns_discovered,
                patterns_surviving_to_validating=validate_report.patterns_surviving_to_validating,
                patterns_validated=holdout_report.patterns_validated,
                validated_definitions=[p.definition for p in validated],
            )
        )

    seeds_with_hit = sum(1 for r in per_seed if r.patterns_validated > 0)
    rate = seeds_with_hit / len(seeds) if seeds else 0.0
    if kind is ControlKind.POSITIVE:
        acceptance_rule = "recovered (>=1 VALIDATED pattern) in a majority (>50%) of seeds"
        passed = rate > 0.5
    else:
        acceptance_rule = "false VALIDATED rate <= 40% of seeds (declared, not measured-optimal -- see module docstring)"
        passed = rate <= 0.4

    return ControlSummary(
        control_name=name, kind=kind, description=description, seeds_run=len(seeds),
        seeds_with_at_least_one_validated=seeds_with_hit, rate=rate,
        acceptance_rule=acceptance_rule, passed=passed, per_seed=per_seed,
    )


_POSITIVE_CONTROLS = [
    ("momentum", "Alternating-block momentum: yesterday's return sign genuinely predicts today's."),
    ("mean_reversion", "Daily-alternating drift: today's return genuinely anti-predicts tomorrow's."),
    ("lead_lag", "FOLLOWER's return is literally LEADER's lagged return plus tiny noise."),
]

_NEGATIVE_CONTROLS = [
    ("pure_noise", "Two independent zero-drift-in-expectation random walks."),
    ("shuffled_returns", "The real momentum series with its daily returns fully permuted."),
    ("shuffled_timestamps", "The real momentum series, chunk-shuffled at 2-day granularity."),
    (
        "independent_random_predictor",
        "Two independent random-walk tickers sharing a sector -- no real lead/lag relationship.",
    ),
]


def run_suite(*, positive_seeds: list[int], negative_seeds: list[int]) -> ControlSuiteReport:
    summaries = [
        run_control(name, ControlKind.POSITIVE, positive_seeds, description=desc)
        for name, desc in _POSITIVE_CONTROLS
    ] + [
        run_control(name, ControlKind.NEGATIVE, negative_seeds, description=desc)
        for name, desc in _NEGATIVE_CONTROLS
    ]
    return ControlSuiteReport(control_suite_version=CONTROL_SUITE_VERSION, summaries=summaries)


__all__ = [
    "CONTROL_SUITE_VERSION",
    "ControlKind",
    "ControlSeedResult",
    "ControlSummary",
    "ControlSuiteReport",
    "build_independent_random_predictor_panel",
    "build_lead_lag_panel",
    "build_mean_reversion_panel",
    "build_momentum_panel",
    "build_pure_noise_panel",
    "build_shuffled_returns_panel",
    "build_shuffled_timestamps_panel",
    "run_control",
    "run_suite",
]
