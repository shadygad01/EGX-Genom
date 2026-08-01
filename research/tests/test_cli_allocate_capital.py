"""End-to-end test for `agx allocate-capital`: the Capital Allocation
Intelligence mission's CLI entry point, composing the same real evidence
`agx decide` uses (see `cli.build_position_aware_decisions`).
"""

import json
from pathlib import Path

from agx_research import cli

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"
UNIVERSE_SEED = Path(__file__).resolve().parents[1] / "data" / "universe"


def test_allocate_capital_with_no_knowledge_and_no_positions_returns_an_honest_empty_plan(tmp_path, capsys):
    exit_code = cli.main(
        [
            "--data-dir", str(tmp_path),
            "--universe-seed-dir", str(UNIVERSE_SEED),
            "run", "--mode", "mock", "--date", "2026-06-01", "--end-date", "2026-06-14",
        ]
    )
    assert exit_code == 0
    capsys.readouterr()

    exit_code = cli.main(
        [
            "--data-dir", str(tmp_path),
            "--universe-seed-dir", str(UNIVERSE_SEED),
            "allocate-capital", "--date", "2026-06-14",
        ]
    )
    assert exit_code == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["ranking"] == []
    assert plan["queue"] == []
    assert plan["capital_released_today"] == []
    assert plan["capital_recycled"] == []
    assert plan["cash_waiting"]["idle_cash_before"] == 1.0
    assert plan["cash_waiting"]["idle_cash_after"] == 1.0
    assert plan["provenance"]["produced_by"] == "capital_allocation_engine@1.0.0"


def test_allocate_capital_ranks_a_held_no_evidence_position_alongside_everything_else(tmp_path, capsys):
    cli.main(
        [
            "--data-dir", str(tmp_path),
            "--universe-seed-dir", str(UNIVERSE_SEED),
            "run", "--mode", "mock", "--date", "2026-06-01", "--end-date", "2026-06-14",
        ]
    )
    capsys.readouterr()

    positions_path = tmp_path / "positions.json"
    positions_path.write_text(
        json.dumps({"COMI": {"held": True, "current_weight": 0.05, "average_cost": 65.0}}),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "--data-dir", str(tmp_path),
            "--universe-seed-dir", str(UNIVERSE_SEED),
            "allocate-capital", "--date", "2026-06-14", "--positions", str(positions_path),
        ]
    )
    assert exit_code == 0
    plan = json.loads(capsys.readouterr().out)
    assert len(plan["ranking"]) == 1
    assert plan["ranking"][0]["ticker"] == "COMI"
    assert plan["ranking"][0]["opportunity_score"] == 0.0
    # No fresh evidence -> abstains to hold -> nothing to fund, nothing released.
    assert plan["queue"] == []
    assert plan["capital_released_today"] == []
    assert plan["explanation"]["why_this_stock"]
