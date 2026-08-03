"""Tests for collectors.company_earnings_table using REAL extracted PDF
text -- not synthetic fixtures. `fixtures/rmda_1q26_earnings_real_extract.txt`
and `fixtures/tmgh_1q26_earnings_real_extract.txt` are the actual `pypdf`
`extract_text()` output from Rameda's and TMG Holding's real, public 1Q26
earnings-release PDFs, fetched live via GitHub Actions run `30810863486`
(2026-08-03, real network egress -- research/scripts/probe_pdf_text.py).
Truncated to ~4000 chars each, matching what the probe actually captured.
"""

from pathlib import Path

import pytest

from agx_research.collectors.company_earnings_table import parse_earnings_summary_table

FIXTURES = Path(__file__).parent / "fixtures"
RMDA_TEXT = (FIXTURES / "rmda_1q26_earnings_real_extract.txt").read_text(encoding="utf-8")
TMGH_TEXT = (FIXTURES / "tmgh_1q26_earnings_real_extract.txt").read_text(encoding="utf-8")


def test_parses_real_rmda_summary_table():
    items, warnings = parse_earnings_summary_table(RMDA_TEXT, "RMDA")
    by_item = {item.line_item: item for item in items}

    assert warnings == []
    assert by_item["revenue"].value == pytest.approx(1_066_800_000.0)
    assert by_item["gross_profit"].value == pytest.approx(526_700_000.0)
    assert by_item["ebitda"].value == pytest.approx(303_100_000.0)
    assert by_item["operating_income"].value == pytest.approx(278_900_000.0)
    assert by_item["net_income"].value == pytest.approx(103_200_000.0)
    assert by_item["recurring_net_income"].value == pytest.approx(109_400_000.0)
    for item in items:
        assert item.ticker == "RMDA"
        assert item.period_end_date.isoformat() == "2026-03-31"
        assert item.period_type == "QUARTERLY"
        assert item.currency == "EGP"


def test_parses_real_tmgh_summary_table():
    items, warnings = parse_earnings_summary_table(TMGH_TEXT, "TMGH")
    by_item = {item.line_item: item for item in items}

    assert warnings == []
    assert by_item["revenue"].value == pytest.approx(13_070_900_000.0)
    assert by_item["gross_profit"].value == pytest.approx(4_630_400_000.0)
    assert by_item["operating_income"].value == pytest.approx(7_140_700_000.0)
    assert by_item["net_income"].value == pytest.approx(5_488_000_000.0)
    for item in items:
        assert item.period_end_date.isoformat() == "2026-03-31"


def test_never_materializes_unrelated_table_rows_with_the_same_shape():
    """RMDA's real document also has a per-channel Sales/Volumes Sold
    breakdown table with the identical <label> <num> <num> <pct> shape --
    this must never be mistaken for the income-statement summary."""
    items, _ = parse_earnings_summary_table(RMDA_TEXT, "RMDA")
    line_items = {item.line_item for item in items}
    assert "sales" not in line_items
    assert "volumes_sold" not in line_items
    assert len(items) == len(set(items_by_key := [i.line_item for i in items]))
    assert len(items_by_key) == 6


def test_returns_empty_with_warning_when_no_summary_table_header_exists():
    items, warnings = parse_earnings_summary_table("Just some prose, no table here.", "XXXX")
    assert items == []
    assert warnings != []


def test_returns_empty_with_warning_when_header_exists_but_no_known_labels_match():
    text = "EGP mn 1Q25 1Q26 YoY Change\nSomething Unmapped 1.0 2.0 100%"
    items, warnings = parse_earnings_summary_table(text, "XXXX")
    assert items == []
    assert warnings != []
