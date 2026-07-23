from agx_research.acquisition_intelligence.domain_resolution import (
    HeuristicDomainResolver,
    ProbeResult,
)
from agx_research.acquisition_intelligence.target import TargetOrganization
from agx_research.sources.spec import SourceCategory


def make_target(**overrides) -> TargetOrganization:
    defaults = dict(id="t1", name="Test Org", category=SourceCategory.NEWS, country="EG")
    defaults.update(overrides)
    return TargetOrganization(**defaults)


def test_hints_are_tried_before_heuristic_guesses():
    target = make_target(domain_hints=["testorg.com"])
    resolver = HeuristicDomainResolver(prober=lambda url: ProbeResult(url=url, reachable=False))
    domains = [d for d, _ in resolver.candidate_domains(target)]
    assert domains == ["testorg.com"]


def test_no_hints_falls_back_to_name_derived_heuristic_guesses():
    target = make_target(name="Test Org", domain_hints=[], country="US")
    resolver = HeuristicDomainResolver(prober=lambda url: ProbeResult(url=url, reachable=False))
    domains = [d for d, origin in resolver.candidate_domains(target)]
    assert "testorg.com" in domains
    origins = {origin for _, origin in resolver.candidate_domains(target)}
    assert origins == {"heuristic"}


def test_egypt_country_adds_local_tld_guesses():
    target = make_target(name="Test Org", domain_hints=[], country="EG")
    resolver = HeuristicDomainResolver(prober=lambda url: ProbeResult(url=url, reachable=False))
    domains = [d for d, _ in resolver.candidate_domains(target)]
    assert "testorg.com.eg" in domains
    assert "testorg.gov.eg" in domains


def test_resolve_returns_first_reachable_domain_and_stops():
    calls = []

    def prober(url):
        calls.append(url)
        reachable = url == "https://testorg.gov.eg"
        return ProbeResult(url=url, reachable=reachable, status_code=200 if reachable else None)

    target = make_target(domain_hints=[], country="EG")
    resolver = HeuristicDomainResolver(prober)
    resolved = resolver.resolve(target)

    assert resolved is not None
    assert resolved.domain == "testorg.gov.eg"
    assert resolved.origin == "heuristic"
    # stops probing once it finds a reachable domain (doesn't exhaust all candidates)
    assert calls[-1] == "https://testorg.gov.eg"


def test_resolve_returns_none_when_nothing_reachable():
    resolver = HeuristicDomainResolver(prober=lambda url: ProbeResult(url=url, reachable=False))
    target = make_target(domain_hints=["testorg.com"])
    assert resolver.resolve(target) is None


def test_never_asserts_an_unprobed_domain_as_reachable():
    # a hint alone, with no probe ever succeeding, must not resolve
    probed = []

    def prober(url):
        probed.append(url)
        return ProbeResult(url=url, reachable=False, error="connection refused")

    target = make_target(domain_hints=["fake-domain-that-does-not-exist.example"])
    resolver = HeuristicDomainResolver(prober)
    assert resolver.resolve(target) is None
    assert "https://fake-domain-that-does-not-exist.example" in probed
