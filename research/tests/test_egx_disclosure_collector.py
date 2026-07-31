from datetime import date

from agx_research.collectors.egx_disclosures import EgxDisclosureCollector
from agx_research.production.collector_plan import build_live_collector
from agx_research.sources.catalog import seed_sources

HTML = """
<div class="card-body"><div class="row g-0">
  <div><h5 class="card-title">ابوقير للاسمدة والصناعات الكيماوية (ABUK.CA) - قرارات مجلس إدارة الشركة</h5>
  <p class="card-text">اسم الشركة: ابوقير للاسمدة والصناعات الكيماوية<br />كود رويترز: ABUK.CA<br />
  قرارات مجلس الإدارة والمتضمن مؤشرات نتائج الأعمال غير المدققة عن الفترة المنتهية في 30/06/2026.
  <a href="http://www.egx.com.eg/downloads/Bulletins/341926_1.pdf">المرفق</a></p></div>
  <div><p class="card-text mb-1"><small class="text-muted">2026-07-30 08:25 </small></p></div>
</div></div>
<div class="card-body"><div class="row g-0">
  <div><h5 class="card-title">شركة خارج الكون (XXXX.CA) تعلن نتائج الأعمال</h5>
  <p class="card-text">كود رويترز: XXXX.CA</p></div>
  <div><p class="card-text mb-1"><small class="text-muted">2026-07-30 08:20 </small></p></div>
</div></div>
"""


class FakeFetcher:
    def fetch_text(self, url, spec):
        return HTML


def disclosure_spec():
    return next(spec for spec in seed_sources() if spec.id == "eac_egx_disclosures")


def test_market_disclosure_is_attributed_and_classified_as_earnings():
    collector = EgxDisclosureCollector(
        disclosure_spec(), tickers=["ABUK"], pages=1, fetcher=FakeFetcher()
    )
    [document] = collector.fetch()
    batch = collector.parse(document)

    assert len(batch.news_items) == 1
    assert batch.news_items[0].tickers == ["ABUK"]
    assert batch.news_items[0].published_at == date(2026, 7, 30)
    assert batch.news_items[0].body == "http://www.egx.com.eg/downloads/Bulletins/341926_1.pdf"
    assert len(batch.corporate_events) == 1
    assert batch.corporate_events[0].ticker == "ABUK"
    assert batch.corporate_events[0].event_type == "EARNINGS"


def test_live_factory_wires_market_disclosure_collector():
    collector = build_live_collector(
        "eac_egx_disclosures",
        disclosure_spec(),
        fetcher=FakeFetcher(),
        tickers=["ABUK"],
    )
    assert isinstance(collector, EgxDisclosureCollector)
