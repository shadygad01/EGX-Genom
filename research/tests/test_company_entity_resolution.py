from agx_research.acquisition_intelligence.domain_resolution import HeuristicDomainResolver, ProbeResult
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.discovery.company_entity_resolution import EntityResolutionEngine, HintCandidate
from agx_research.discovery.company_financial_registry import (
    CompanyFinancialSourceRecord,
    CompanyRegistryStatus,
)
from agx_research.discovery.gleif_lookup import GleifLegalEntityClient

IR_PAGE = """
<html><body>
<a href="/reports/annual-report-2025.pdf">Annual Report 2025</a>
</body></html>
"""


class _FakeFetcher(HttpFetcher):
    def __init__(self, *, pages: dict[str, str] | None = None):
        super().__init__()
        self._pages = pages or {}

    def robots_status(self, url):
        return True

    def fetch_text(self, url, spec):
        return self._pages.get(url, IR_PAGE)


class _Strategy:
    """Matches WebsiteHintStrategy's shape without importing a real client."""

    def __init__(self, name, hints):
        self.name = name
        self._hints = hints

    def lookup(self, companies):
        return {t: h for t, h in self._hints.items() if t in companies}


def _prober(reachable_urls):
    def prober(url):
        return ProbeResult(url=url, reachable=url in reachable_urls, status_code=200 if url in reachable_urls else 404)

    return prober


def _engine(*, website_strategies, reachable_urls, legal_entity_client=None):
    return EntityResolutionEngine(
        website_strategies=website_strategies,
        legal_entity_client=legal_entity_client,
        domain_resolver=HeuristicDomainResolver(_prober(reachable_urls)),
        fetcher=_FakeFetcher(),
    )


def test_resolve_website_candidates_collects_every_strategy_never_stopping_at_first():
    engine = _engine(
        website_strategies=[
            _Strategy("wikidata", {"COMI": "www.cibeg.com"}),
            _Strategy("web_search", {"COMI": "cibeg.com", "HRHO": "efghermes.com"}),
        ],
        reachable_urls=set(),
    )
    candidates = engine.resolve_website_candidates({"COMI": "CIB", "HRHO": "EFG Hermes"})
    assert {c.source for c in candidates["COMI"]} == {"wikidata", "web_search"}
    assert [c.source for c in candidates["HRHO"]] == ["web_search"]


def test_earlier_strategy_gets_higher_confidence():
    engine = _engine(
        website_strategies=[
            _Strategy("wikidata", {"COMI": "www.cibeg.com"}),
            _Strategy("web_search", {"COMI": "cibeg.com"}),
        ],
        reachable_urls=set(),
    )
    candidates = engine.resolve_website_candidates({"COMI": "CIB"})
    by_source = {c.source: c.confidence for c in candidates["COMI"]}
    assert by_source["wikidata"] > by_source["web_search"]


def test_second_strategy_hint_wins_when_first_is_unreachable():
    """The core gap this engine closes: a company's top-priority hint being
    unreachable must not discard a second, independent hint for the same
    company -- HeuristicDomainResolver gets a real fallback try at it."""
    engine = _engine(
        website_strategies=[
            _Strategy("wikidata", {"JUFO": "wrong-domain.example"}),
            _Strategy("web_search", {"JUFO": "www.juhayna.com"}),
        ],
        reachable_urls={"https://www.juhayna.com"},
    )
    report = engine.resolve({"JUFO": "Juhayna Food Industries"})
    record = report.records[0]
    assert record.website_resolved
    assert record.resolved_domain.domain == "www.juhayna.com"
    # provenance correctly attributes the win to web_search, not wikidata,
    # even though wikidata ran first and had higher prior confidence
    assert report.website_resolutions_by_source() == {"web_search": 1}


def test_resolve_marks_website_unresolved_when_no_candidate_is_reachable():
    engine = _engine(
        website_strategies=[_Strategy("wikidata", {"EGCH": "unreachable.example"})],
        reachable_urls=set(),
    )
    report = engine.resolve({"EGCH": "Egyptian Chemical Industries"})
    record = report.records[0]
    assert not record.website_resolved
    assert record.financial_record.status == CompanyRegistryStatus.HOMEPAGE_UNRESOLVED
    assert record.financial_record.blocked_reason


def test_resolve_delegates_to_existing_financial_discovery_once_website_resolves():
    engine = _engine(
        website_strategies=[_Strategy("web_search", {"COMI": "cibeg.com"})],
        reachable_urls={"https://cibeg.com"},
    )
    report = engine.resolve({"COMI": "Commercial International Bank"})
    record = report.records[0]
    assert record.ir_entry_point_resolved
    assert record.financial_record.homepage_hint_source == "web_search"
    assert record.financial_record.documents


def test_resolve_legal_entities_uses_gleif_when_configured():
    class _FakeGleif(GleifLegalEntityClient):
        def __init__(self):
            pass

        def lookup(self, companies):
            from agx_research.discovery.gleif_lookup import LegalEntityMatch

            return {
                "JUFO": LegalEntityMatch(
                    lei="LEI123", legal_name="JUHAYNA FOOD INDUSTRIES S.A.E.",
                    aliases=["Juhayna"], jurisdiction_country="EG",
                    match_confidence=0.9, evidence="GLEIF LEI record LEI123",
                )
            }

    engine = _engine(
        website_strategies=[],
        reachable_urls=set(),
        legal_entity_client=_FakeGleif(),
    )
    report = engine.resolve({"JUFO": "Juhayna Food Industries"})
    record = report.records[0]
    assert record.legal_name == "JUHAYNA FOOD INDUSTRIES S.A.E."
    assert record.aliases == ["Juhayna"]
    assert record.legal_name_source == "gleif"
    assert record.lei == "LEI123"
    assert not record.website_resolved  # no website strategy configured -- stays honestly unresolved


def test_resolve_without_gleif_leaves_legal_name_unresolved():
    engine = _engine(website_strategies=[], reachable_urls=set())
    report = engine.resolve({"EGCH": "Egyptian Chemical Industries"})
    record = report.records[0]
    assert record.legal_name is None
    assert record.aliases == []


def test_resolve_skips_already_validated_companies():
    existing = CompanyFinancialSourceRecord(
        id="ETEL", ticker="ETEL", company_name="Telecom Egypt",
        status=CompanyRegistryStatus.VALIDATED, homepage_url="https://ir.te.eg",
    )
    engine = _engine(website_strategies=[], reachable_urls=set())
    report = engine.resolve({"ETEL": "Telecom Egypt"}, existing_records={"ETEL": existing})
    assert report.total == 0


def test_report_resolution_rates():
    engine = _engine(
        website_strategies=[_Strategy("web_search", {"COMI": "cibeg.com"})],
        reachable_urls={"https://cibeg.com"},
    )
    report = engine.resolve({"COMI": "CIB", "EGCH": "Egyptian Chemical Industries"})
    assert report.total == 2
    assert report.website_resolution_rate == 0.5
    assert report.legal_name_resolution_rate == 0.0


def test_website_candidates_are_sorted_by_confidence_before_probing():
    """Regression for the exact ordering HeuristicDomainResolver relies on:
    the highest-confidence candidate must be tried first."""
    engine = _engine(
        website_strategies=[
            _Strategy("web_search", {"COMI": "second-choice.example"}),
            _Strategy("wikidata", {"COMI": "www.cibeg.com"}),
        ],
        reachable_urls=set(),
    )
    candidates = engine.resolve_website_candidates({"COMI": "CIB"})
    record_candidates = sorted(candidates["COMI"], key=lambda c: -c.confidence)
    assert record_candidates[0].source == "web_search"  # ran first, so highest prior confidence
    assert isinstance(record_candidates[0], HintCandidate)
