"""reconcile_discovery_news(): the only path that promotes a DISCOVERY-tier
news candidate (news_discovery.csv) into news.csv/evidence, and only once
a PRIMARY source independently reported the same ticker nearby in time.
"""

from datetime import date

from agx_research.collectors.discovery_reconciliation import reconcile_discovery_news
from agx_research.collectors.service import append_discovery_news, append_news
from agx_research.data.schemas import NewsItem


def test_empty_discovery_pool_is_a_noop(tmp_path):
    result = reconcile_discovery_news(tmp_path)
    assert result == reconcile_discovery_news(tmp_path)  # deterministic, no crash
    assert result.candidates_checked == 0
    assert result.promoted == 0
    assert result.still_pending == 0


def test_candidate_promoted_when_a_primary_source_reports_the_same_ticker_nearby(tmp_path):
    append_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 2), source="enterprise_press", headline="COMI results", tickers=["COMI"])],
    )
    append_discovery_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 1), source="gdelt", headline="COMI mentioned abroad", tickers=["COMI"])],
    )

    result = reconcile_discovery_news(tmp_path, window_days=2)

    assert result.candidates_checked == 1
    assert result.promoted == 1
    assert result.still_pending == 0
    news_csv = (tmp_path / "news.csv").read_text(encoding="utf-8")
    assert "COMI mentioned abroad" in news_csv
    assert not (tmp_path / "news_discovery.csv").read_text(encoding="utf-8").count("COMI mentioned abroad")


def test_candidate_stays_pending_when_no_primary_source_ever_mentions_the_ticker(tmp_path):
    append_discovery_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 1), source="gdelt", headline="MFPC mentioned abroad", tickers=["MFPC"])],
    )

    result = reconcile_discovery_news(tmp_path, window_days=2)

    assert result.candidates_checked == 1
    assert result.promoted == 0
    assert result.still_pending == 1
    assert not (tmp_path / "news.csv").exists()
    assert "MFPC mentioned abroad" in (tmp_path / "news_discovery.csv").read_text(encoding="utf-8")


def test_candidate_stays_pending_when_primary_report_is_outside_the_window(tmp_path):
    append_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 10), source="enterprise_press", headline="COMI results", tickers=["COMI"])],
    )
    append_discovery_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 1), source="gdelt", headline="COMI mentioned abroad", tickers=["COMI"])],
    )

    result = reconcile_discovery_news(tmp_path, window_days=2)

    assert result.promoted == 0
    assert result.still_pending == 1


def test_candidate_with_no_resolved_ticker_is_never_promoted(tmp_path):
    append_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 1), source="enterprise_press", headline="COMI results", tickers=["COMI"])],
    )
    append_discovery_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 1), source="gdelt", headline="Unresolved mention", tickers=[])],
    )

    result = reconcile_discovery_news(tmp_path, window_days=2)

    assert result.promoted == 0
    assert result.still_pending == 1


def test_promoted_rows_are_not_reprocessed_on_a_second_run(tmp_path):
    append_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 2), source="enterprise_press", headline="COMI results", tickers=["COMI"])],
    )
    append_discovery_news(
        tmp_path,
        [NewsItem(published_at=date(2026, 6, 1), source="gdelt", headline="COMI mentioned abroad", tickers=["COMI"])],
    )

    first = reconcile_discovery_news(tmp_path, window_days=2)
    second = reconcile_discovery_news(tmp_path, window_days=2)

    assert first.promoted == 1
    assert second.candidates_checked == 0
    assert second.promoted == 0
