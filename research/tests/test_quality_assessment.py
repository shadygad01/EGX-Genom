from datetime import date

from agx_research.collectors.base import CollectionBatch
from agx_research.collectors.quality import assess_quality
from agx_research.data.schemas import MacroObservation, NewsItem, PriceBar


def bar(trade_date=date(2026, 6, 1), **overrides):
    defaults = dict(
        ticker="COMI", trade_date=trade_date, open=10.0, high=11.0, low=9.0, close=10.5, volume=100
    )
    defaults.update(overrides)
    return PriceBar(**defaults)


def test_full_coverage_no_warnings_yields_high_confidence():
    batch = CollectionBatch(
        source_id="stooq", raw_document_id="rawdoc_x", price_bars=[bar(), bar(date(2026, 6, 2))]
    )
    assessment = assess_quality(batch, expected_records=2, source_reliability=0.9, freshness_score=1.0)
    assert assessment.coverage_score == 1.0
    assert assessment.completeness_score == 1.0
    assert assessment.validation_score == 1.0
    assert assessment.consistency_score is None
    assert assessment.confidence_score == (1.0 + 1.0 + 0.9 + 1.0 + 1.0) / 5


def test_partial_coverage_scores_below_one():
    batch = CollectionBatch(source_id="stooq", raw_document_id="rawdoc_x", price_bars=[bar()])
    assessment = assess_quality(batch, expected_records=4, source_reliability=0.9)
    assert assessment.coverage_score == 0.25


def test_parse_warnings_reduce_completeness_score():
    batch = CollectionBatch(
        source_id="stooq",
        raw_document_id="rawdoc_x",
        price_bars=[bar()],
        parse_warnings=["line 2: unparseable"],
    )
    assessment = assess_quality(batch, expected_records=2, source_reliability=0.9)
    assert assessment.completeness_score == 1 / 2


def test_invalid_price_bars_reduce_validation_score():
    batch = CollectionBatch(
        source_id="stooq",
        raw_document_id="rawdoc_x",
        # negative volume is the only rule this second bar breaks -> exactly one ERROR
        price_bars=[bar(), bar(date(2026, 6, 2), volume=-1)],
    )
    assessment = assess_quality(batch, expected_records=2, source_reliability=0.9)
    assert assessment.validation_score == 0.5


def test_consistency_score_included_only_when_provided():
    batch = CollectionBatch(source_id="stooq", raw_document_id="rawdoc_x", price_bars=[bar()])
    without = assess_quality(batch, expected_records=1, source_reliability=0.9)
    with_consistency = assess_quality(
        batch, expected_records=1, source_reliability=0.9, consistency_score=0.6
    )
    assert without.consistency_score is None
    assert with_consistency.consistency_score == 0.6
    assert with_consistency.confidence_score != without.confidence_score


def test_empty_batch_no_warnings_scores_full_completeness():
    batch = CollectionBatch(source_id="rss_generic", raw_document_id="rawdoc_x")
    assessment = assess_quality(batch, expected_records=0, source_reliability=0.5)
    assert assessment.completeness_score == 1.0
    assert assessment.validation_score == 1.0


def test_macro_and_news_records_count_toward_coverage():
    batch = CollectionBatch(
        source_id="fred",
        raw_document_id="rawdoc_x",
        macro_observations=[MacroObservation(series_id="X", observation_date=date(2026, 6, 1), value=1.0)],
        news_items=[NewsItem(published_at=date(2026, 6, 1), source="rss", headline="h")],
    )
    assessment = assess_quality(batch, expected_records=2, source_reliability=0.5)
    assert assessment.coverage_score == 1.0
