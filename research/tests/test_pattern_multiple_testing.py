"""Multiple-testing accounting for `patterns.multiple_testing`."""

from __future__ import annotations

from datetime import date

from agx_research.patterns.multiple_testing import (
    TestingLedger,
    TestingLedgerRepository,
    benjamini_hochberg,
    complexity_penalty,
)


def test_benjamini_hochberg_accepts_nothing_when_all_p_values_are_large():
    accept = benjamini_hochberg([0.9, 0.8, 0.95, 0.99], fdr_alpha=0.10)
    assert accept == [False, False, False, False]


def test_benjamini_hochberg_accepts_all_when_every_p_value_is_tiny():
    accept = benjamini_hochberg([0.0001, 0.0002, 0.0003], fdr_alpha=0.10)
    assert accept == [True, True, True]


def test_benjamini_hochberg_preserves_original_order():
    # A large pool of noise (p~uniform) plus one genuinely tiny p-value:
    # only the tiny one (and possibly a few near it) should survive, and
    # its position in the returned list must match its input position.
    p_values = [0.5, 0.6, 0.0001, 0.7, 0.55, 0.65]
    accept = benjamini_hochberg(p_values, fdr_alpha=0.10)
    assert len(accept) == len(p_values)
    assert accept[2] is True  # the tiny p-value's own index
    assert accept.count(True) < len(p_values)  # not everything gets swept in


def test_benjamini_hochberg_empty_input():
    assert benjamini_hochberg([], fdr_alpha=0.10) == []


def test_complexity_penalty_scales_with_condition_count():
    assert complexity_penalty(0.01, 1) == 0.01
    assert complexity_penalty(0.01, 3) == 0.03
    assert complexity_penalty(0.5, 3) == 1.0  # capped at 1.0, never fabricated above certainty


def test_testing_ledger_repository_persists_and_reloads(tmp_path):
    path = tmp_path / "ledger.json"
    repo = TestingLedgerRepository(path)
    ledger = TestingLedger(
        id="testing_ledger_1", run_id="run_1", as_of=date(2026, 6, 14),
        hypotheses_tested=500, discovery_sample_size=100, validation_sample_size=40,
    )
    repo.add(ledger)
    assert path.exists()

    reloaded = TestingLedgerRepository(path)
    fetched = reloaded.latest("testing_ledger_1")
    assert fetched is not None
    assert fetched.hypotheses_tested == 500
    assert fetched.run_id == "run_1"
