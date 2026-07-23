from datetime import date
from io import BytesIO

import pytest
from openpyxl import Workbook

from agx_research.collectors.archive import RawArchive
from agx_research.collectors.excel import ExcelSeriesCollector
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="excel_source", name="Excel Source", category=SourceCategory.OFFICIAL,
        access_method=AccessMethod.CSV_DOWNLOAD, status=SourceStatus.IMPLEMENTED,
        reliability_score=0.9, freshness_score=0.5,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


def _build_workbook(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


class FakeFetcher:
    def __init__(self, content: bytes):
        self.content = content

    def fetch_bytes(self, url, spec):
        return self.content


def test_parse_produces_macro_observations_from_mapped_columns(tmp_path):
    content = _build_workbook(
        [
            ["Date", "CPI", "Unemployment"],
            ["2026-06-01", 24.4, 7.1],
            ["2026-05-01", 23.9, 7.3],
        ]
    )
    fetcher = FakeFetcher(content)
    archive = RawArchive(tmp_path)
    collector = ExcelSeriesCollector(
        make_spec(), "https://example.com/bulletin.xlsx",
        date_column="Date", value_columns={"CPI": "egypt_cpi", "Unemployment": "egypt_unemployment"},
        archive=archive, fetcher=fetcher,
    )

    [document] = collector.fetch()
    batch = collector.parse(document)

    assert len(batch.macro_observations) == 4
    by_series = {}
    for obs in batch.macro_observations:
        by_series.setdefault(obs.series_id, []).append(obs)
    assert by_series["egypt_cpi"][0].observation_date == date(2026, 6, 1)
    assert by_series["egypt_cpi"][0].value == 24.4
    assert by_series["egypt_unemployment"][1].value == 7.3


def test_parse_skips_blank_rows_and_records_bad_values_as_warnings(tmp_path):
    content = _build_workbook(
        [
            ["Date", "CPI"],
            ["2026-06-01", "not-a-number"],
            [None, None],
            ["2026-05-01", 23.9],
        ]
    )
    fetcher = FakeFetcher(content)
    archive = RawArchive(tmp_path)
    collector = ExcelSeriesCollector(
        make_spec(), "https://example.com/bulletin.xlsx",
        date_column="Date", value_columns={"CPI": "egypt_cpi"},
        archive=archive, fetcher=fetcher,
    )

    [document] = collector.fetch()
    batch = collector.parse(document)

    assert len(batch.macro_observations) == 1
    assert batch.macro_observations[0].value == 23.9
    assert any("Unparseable value" in w for w in batch.parse_warnings)


def test_parse_unexpected_header_recorded_as_warning(tmp_path):
    content = _build_workbook([["Foo", "Bar"], [1, 2]])
    fetcher = FakeFetcher(content)
    archive = RawArchive(tmp_path)
    collector = ExcelSeriesCollector(
        make_spec(), "https://example.com/bulletin.xlsx",
        date_column="Date", value_columns={"CPI": "egypt_cpi"},
        archive=archive, fetcher=fetcher,
    )

    [document] = collector.fetch()
    batch = collector.parse(document)
    assert batch.macro_observations == []
    assert "Unexpected header" in batch.parse_warnings[0]


def test_collector_rejects_non_implemented_source(tmp_path):
    spec = make_spec(status=SourceStatus.PLANNED)
    with pytest.raises(ValueError):
        ExcelSeriesCollector(
            spec, "https://x/y.xlsx", date_column="Date", value_columns={},
            archive=RawArchive(tmp_path),
        )
