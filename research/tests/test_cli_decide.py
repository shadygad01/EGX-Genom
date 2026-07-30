"""End-to-end test for `agx decide`: the CLI entry point closing the last
mile of the Decision-Centric Redesign's data flow (source -> collected
data -> knowledge -> Recommendation -> position-aware six-way decision).
"""

import json
from pathlib import Path

from agx_research import cli

MOCK_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock"
UNIVERSE_SEED = Path(__file__).resolve().parents[1] / "data" / "universe"


def test_decide_with_no_knowledge_and_no_positions_returns_empty_list(tmp_path, capsys):
    exit_code = cli.main(
        [
            "--data-dir", str(tmp_path),
            "--universe-seed-dir", str(UNIVERSE_SEED),
            "run", "--mode", "mock", "--date", "2026-06-01", "--end-date", "2026-06-14",
        ]
    )
    assert exit_code == 0
    capsys.readouterr()  # discard the `run` command's own stdout

    exit_code = cli.main(
        [
            "--data-dir", str(tmp_path),
            "--universe-seed-dir", str(UNIVERSE_SEED),
            "decide", "--date", "2026-06-14",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == []


def test_decide_with_a_held_position_and_no_fresh_evidence_abstains_to_hold(tmp_path, capsys):
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
            "decide", "--date", "2026-06-14", "--positions", str(positions_path),
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    decision = payload[0]
    assert decision["ticker"] == "COMI"
    assert decision["action"] == "hold"
    assert decision["abstained"] is True
    assert decision["target_weight"] == 0.0
    assert decision["current_weight"] == 0.05
    assert decision["explanation"]["why_this_stock"]
    assert decision["provenance"]["produced_by"] == "decision_service@1.0.0"
