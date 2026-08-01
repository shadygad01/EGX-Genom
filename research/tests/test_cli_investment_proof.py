"""End-to-end test for `agx investment-proof`: the CLI entry point to the
Investment Proof Framework (Capital Trust Report). Self-contained, like
`agx validate-investment` -- every scenario is built in memory.
"""

import json

from agx_research import cli


def test_investment_proof_writes_json_and_markdown_reports(tmp_path, capsys):
    json_out = tmp_path / "report.json"
    markdown_out = tmp_path / "report.md"

    exit_code = cli.main(
        [
            "investment-proof",
            "--ticker-limit",
            "6",
            "--out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert exit_code in (0, 2)
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["dimensions"]) == 8
    assert payload["overall_verdict"] in {"yes", "no", "partially"}
    assert json.loads(json_out.read_text(encoding="utf-8")) == payload
    assert "# Capital Trust Report" in markdown_out.read_text(encoding="utf-8")


def test_investment_proof_exit_code_matches_dimension_verdicts(capsys):
    exit_code = cli.main(["investment-proof", "--ticker-limit", "6"])
    payload = json.loads(capsys.readouterr().out)
    has_fail = any(d["verdict"] == "fail" for d in payload["dimensions"])
    assert exit_code == (2 if has_fail else 0)
