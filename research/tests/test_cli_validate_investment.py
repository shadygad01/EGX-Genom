"""End-to-end test for `agx validate-investment`: the CLI entry point to
the Institutional Investment Validation framework. Self-contained (no
--data-dir/--universe-seed-dir setup needed, unlike `run`/`decide`) --
every scenario is built in memory.
"""

import json

from agx_research import cli


def test_validate_investment_writes_json_and_markdown_reports(tmp_path, capsys):
    json_out = tmp_path / "report.json"
    markdown_out = tmp_path / "report.md"

    exit_code = cli.main(
        ["validate-investment", "--out", str(json_out), "--markdown-out", str(markdown_out)]
    )

    assert exit_code in (0, 2)
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["results"]) == 10
    assert json.loads(json_out.read_text(encoding="utf-8")) == payload
    assert "# Institutional Investment Validation Report" in markdown_out.read_text(encoding="utf-8")


def test_validate_investment_exit_code_matches_overall_verdict(tmp_path, capsys):
    exit_code = cli.main(["validate-investment"])
    payload = json.loads(capsys.readouterr().out)
    if payload["overall_verdict"] == "fail":
        assert exit_code == 2
    else:
        assert exit_code == 0
