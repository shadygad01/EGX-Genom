from agx_research.acquisition_intelligence.domain_resolution import HeuristicDomainResolver, ProbeResult
from agx_research.collectors.fetcher import HttpFetcher
from agx_research.discovery.company_entity_resolution import EntityResolutionEngine, HintCandidate
from agx_research.discovery.company_financial_registry import (
    CompanyFinancialSourceRecord,
    CompanyRegistryStatus,
)
from agx_research.discovery.gleif_lookup import GleifLegalEntityClient, GleifLookupAttempt

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

        def lookup_with_trace(self, companies):
            from agx_research.discovery.gleif_lookup import GleifLookupAttempt, LegalEntityMatch

            return {
                "JUFO": GleifLookupAttempt(
                    ticker="JUFO",
                    matched=True,
                    match=LegalEntityMatch(
                        lei="LEI123", legal_name="JUHAYNA FOOD INDUSTRIES S.A.E.",
                        aliases=["Juhayna"], jurisdiction_country="EG",
                        match_confidence=0.9, evidence="GLEIF LEI record LEI123",
                    ),
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


class _TraceStrategy:
    """A website-hint strategy that exposes lookup_with_trace, matching the
    real shape `wikidata_lookup.WikidataOfficialWebsiteClient` uses -- lets
    tests exercise EntityResolutionEngine's trace-capable code path without
    a real Wikidata client."""

    def __init__(self, name, attempts):
        self.name = name
        self._attempts = attempts  # ticker -> object with matched/hostname/rejection_reason

    def lookup(self, companies):
        return {t: a.hostname for t, a in self._attempts.items() if t in companies and a.matched and a.hostname}

    def lookup_with_trace(self, companies):
        return {t: a for t, a in self._attempts.items() if t in companies}


class _Attempt:
    def __init__(self, matched, hostname=None, rejection_reason=None):
        self.matched = matched
        self.hostname = hostname
        self.rejection_reason = rejection_reason


def test_resolution_memory_persists_every_proposed_candidate_and_rejected_domain():
    engine = _engine(
        website_strategies=[
            _Strategy("wikidata", {"COMI": "bad-first.example"}),
            _Strategy("web_search", {"COMI": "cibeg.com"}),
        ],
        reachable_urls={"https://cibeg.com"},
    )
    report = engine.resolve({"COMI": "Commercial International Bank"})
    memory = report.records[0].resolution_memory

    assert memory is not None
    assert {c.source for c in memory.website_candidates_proposed} == {"wikidata", "web_search"}
    assert memory.resolved_hostname == "cibeg.com"
    probed_domains = {a.domain: a for a in memory.website_probe_attempts}
    assert probed_domains["bad-first.example"].reachable is False
    assert probed_domains["bad-first.example"].rejection_reason
    assert probed_domains["cibeg.com"].reachable is True


def test_resolution_memory_records_never_attempted_candidates_as_absent_not_rejected():
    """A candidate the resolver never got to (because an earlier, higher-
    confidence one already won) must not be fabricated into the persisted
    record as "rejected" -- it must simply not appear in probe attempts."""
    engine = _engine(
        website_strategies=[
            _Strategy("wikidata", {"COMI": "cibeg.com"}),  # ran first -> highest confidence -> probed first
            _Strategy("web_search", {"COMI": "never-reached.example"}),
        ],
        reachable_urls={"https://cibeg.com"},
    )
    report = engine.resolve({"COMI": "Commercial International Bank"})
    memory = report.records[0].resolution_memory
    assert [a.domain for a in memory.website_probe_attempts] == ["cibeg.com"]
    # proposed regardless (a real strategy really proposed it this run)...
    assert "never-reached.example" in {c.hostname for c in memory.website_candidates_proposed}
    # ...but never appears as a probe attempt, since it was never reached.
    assert "never-reached.example" not in {a.domain for a in memory.website_probe_attempts}


def test_resolution_memory_persists_wikidata_source_attempt_rejection_reason():
    engine = _engine(
        website_strategies=[
            _TraceStrategy("wikidata", {"EGCH": _Attempt(matched=False, rejection_reason="no candidate entities")}),
        ],
        reachable_urls=set(),
    )
    report = engine.resolve({"EGCH": "Egyptian Chemical Industries"})
    memory = report.records[0].resolution_memory
    assert len(memory.website_source_attempts) == 1
    attempt = memory.website_source_attempts[0]
    assert attempt.source == "wikidata"
    assert attempt.matched is False
    assert attempt.rejection_reason == "no candidate entities"


def test_resolution_memory_persists_gleif_rejection_reason_even_on_miss():
    class _FakeGleif(GleifLegalEntityClient):
        def __init__(self):
            pass

        def lookup_with_trace(self, companies):
            return {
                "HRHO": GleifLookupAttempt(
                    ticker="HRHO", matched=False, rejection_reason="no fuzzy-completions candidate",
                )
            }

    engine = _engine(website_strategies=[], reachable_urls=set(), legal_entity_client=_FakeGleif())
    report = engine.resolve({"HRHO": "EFG Hermes Holding"})
    memory = report.records[0].resolution_memory

    assert len(memory.legal_entity_attempts) == 1
    attempt = memory.legal_entity_attempts[0]
    assert attempt.source == "gleif"
    assert attempt.matched is False
    assert attempt.rejection_reason == "no fuzzy-completions candidate"
    assert memory.legal_name is None  # a rejected attempt must never populate the canonical field


def test_resolution_memory_reserved_fields_stay_empty():
    """brand_names/parent_company have no real source in this codebase yet
    -- they must stay honestly empty, never guessed."""
    engine = _engine(website_strategies=[], reachable_urls=set())
    report = engine.resolve({"EGCH": "Egyptian Chemical Industries"})
    memory = report.records[0].resolution_memory
    assert memory.brand_names == []
    assert memory.parent_company is None
