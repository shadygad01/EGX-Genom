import pytest

from agx_research.collectors.browser import BrowserAutomationCollector
from agx_research.sources.spec import AccessMethod, SourceCategory, SourceSpec, SourceStatus


def make_spec(**overrides) -> SourceSpec:
    defaults = dict(
        id="browser_source", name="Browser Source", category=SourceCategory.MARKET_DATA,
        access_method=AccessMethod.HTML_SCRAPE, status=SourceStatus.IMPLEMENTED,
        reliability_score=0.5, freshness_score=0.5,
    )
    defaults.update(overrides)
    return SourceSpec(**defaults)


def test_fetch_raises_not_implemented_honestly():
    collector = BrowserAutomationCollector(make_spec())
    with pytest.raises(NotImplementedError):
        collector.fetch()


def test_parse_raises_not_implemented_honestly():
    collector = BrowserAutomationCollector(make_spec())
    with pytest.raises(NotImplementedError):
        collector.parse(None)
