from agx_research.acquisition_intelligence.legality import LegalityVerdict, assess_legality
from agx_research.sources.spec import AccessMethod


def test_robots_disallow_always_blocks_regardless_of_page_text():
    result = assess_legality(
        access_method=AccessMethod.RSS_FEED, robots_allows=False,
        page_text="Free RSS feed and open API access for everyone.",
    )
    assert result.verdict == LegalityVerdict.BLOCKED
    assert result.robots_allows is False


def test_clean_structured_method_with_permissive_robots_is_allowed():
    result = assess_legality(
        access_method=AccessMethod.RSS_FEED, robots_allows=True,
        page_text="Subscribe to our RSS feed for the latest news.",
    )
    assert result.verdict == LegalityVerdict.ALLOWED


def test_red_flag_terms_with_no_green_offset_blocks():
    result = assess_legality(
        access_method=AccessMethod.JSON_API, robots_allows=True,
        terms_of_use_text="Automated queries are prohibited without prior written permission.",
    )
    assert result.verdict == LegalityVerdict.BLOCKED
    assert result.red_flags_found


def test_red_flag_terms_offset_by_green_flag_is_ambiguous_not_allowed():
    result = assess_legality(
        access_method=AccessMethod.JSON_API, robots_allows=True,
        terms_of_use_text="No automated access except via our official public API access program.",
    )
    assert result.verdict == LegalityVerdict.AMBIGUOUS


def test_html_scrape_never_auto_clears_even_with_clean_signals():
    result = assess_legality(
        access_method=AccessMethod.HTML_SCRAPE, robots_allows=True, page_text="Welcome to our site.",
    )
    assert result.verdict == LegalityVerdict.AMBIGUOUS


def test_unknown_robots_status_is_ambiguous_not_allowed():
    result = assess_legality(
        access_method=AccessMethod.CSV_DOWNLOAD, robots_allows=None, page_text="Download our data.",
    )
    assert result.verdict == LegalityVerdict.AMBIGUOUS
