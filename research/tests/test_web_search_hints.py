import json
from pathlib import Path

from agx_research.discovery.web_search_hints import load_web_search_domain_hints


def test_missing_file_returns_empty_dict(tmp_path):
    assert load_web_search_domain_hints(tmp_path / "does_not_exist.json") == {}


def test_loads_hostname_per_ticker(tmp_path):
    path = tmp_path / "hints.json"
    path.write_text(
        json.dumps(
            {
                "hints": {
                    "COMI": {"hostname": "www.cibeg.com", "evidence": "web search result"},
                    "ETEL": {"hostname": "www.telecomegypt.eg", "evidence": "web search result"},
                }
            }
        )
    )
    assert load_web_search_domain_hints(path) == {
        "COMI": "www.cibeg.com",
        "ETEL": "www.telecomegypt.eg",
    }


def test_skips_entries_missing_hostname(tmp_path):
    path = tmp_path / "hints.json"
    path.write_text(json.dumps({"hints": {"XXXX": {"evidence": "no hostname found"}}}))
    assert load_web_search_domain_hints(path) == {}


def test_real_egx30_hints_file_loads_and_covers_expected_tickers():
    hints = load_web_search_domain_hints(
        Path(__file__).resolve().parent.parent
        / "data"
        / "universe"
        / "egx30_web_search_domain_hints.json"
    )
    assert hints["COMI"] == "www.cibeg.com"
    assert hints["ETEL"] == "www.telecomegypt.eg"
    # Deliberately unresolved tickers (see the file's own "unresolved_no_confident_hint")
    # must never appear as a fabricated hint.
    for unresolved in ("EGCH", "HELI", "MCQE", "OIH", "PHDC"):
        assert unresolved not in hints
