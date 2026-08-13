from agx_research.collectors.rss import RssNewsCollector
from agx_research.production.collector_plan import build_live_collector, live_wired_source_ids
from agx_research.sources.catalog import seed_registry


class _UnusedFetcher:
    pass


def test_verified_planned_rss_source_is_promoted_and_generically_wired():
    spec = seed_registry().latest("alborsa")

    assert spec is not None
    assert spec.status.value == "implemented"
    assert spec.base_url == "https://www.alborsaanews.com/feed"

    collector = build_live_collector(
        "alborsa", spec, fetcher=_UnusedFetcher(), tickers=["COMI", "MFPC"]
    )

    assert isinstance(collector, RssNewsCollector)
    assert collector.feed_url == spec.base_url
    assert collector.classify_corporate_events is True


def test_masrawy_economy_is_promoted_and_uses_the_same_generic_wiring():
    spec = seed_registry().latest("masrawy_economy")

    assert spec is not None
    assert spec.status.value == "implemented"
    assert "/rss/feed/206/" in spec.base_url
    assert isinstance(
        build_live_collector(
            "masrawy_economy", spec, fetcher=_UnusedFetcher(), tickers=["COMI"]
        ),
        RssNewsCollector,
    )


def test_live_wiring_topology_excludes_retired_stooq_and_keeps_verified_price_source():
    wired = live_wired_source_ids(seed_registry())

    assert "egx_price_composite" in wired
    assert "stooq" not in wired
    assert "rss_generic" not in wired
