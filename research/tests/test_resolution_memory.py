from agx_research.discovery.resolution_memory import (
    LegalEntityAttempt,
    ProposedWebsiteCandidate,
    ResolutionMemory,
    ResolutionMemoryRecord,
    WebsiteProbeAttempt,
)


def _record(ticker="EGCH", **overrides) -> ResolutionMemoryRecord:
    defaults = dict(id=ticker, ticker=ticker, company_name="Egyptian Chemical Industries")
    defaults.update(overrides)
    return ResolutionMemoryRecord(**defaults)


def test_record_persists_a_failed_attempt_as_permanent_knowledge():
    """A run that resolves nothing must still leave a permanent trace --
    the whole point of this store."""
    memory = ResolutionMemory()
    memory.record(_record(
        website_probe_attempts=[
            WebsiteProbeAttempt(domain="egch.com.eg", origin="heuristic", reachable=False,
                                 rejection_reason="connection refused"),
        ],
    ))

    stored = memory.latest("EGCH")
    assert stored is not None
    assert stored.resolved_hostname is None
    assert stored.website_probe_attempts[0].rejection_reason == "connection refused"


def test_record_auto_increments_version_and_keeps_full_history():
    """Every run's attempt is a new revision, never an overwrite -- a
    rejected domain from an earlier run stays readable via history()."""
    memory = ResolutionMemory()
    memory.record(_record(website_probe_attempts=[
        WebsiteProbeAttempt(domain="wrong-guess.com", origin="heuristic", reachable=False),
    ]))
    memory.record(_record(resolved_hostname="egch.com.eg", website_probe_attempts=[
        WebsiteProbeAttempt(domain="egch.com.eg", origin="hint", reachable=True, status_code=200),
    ]))

    history = memory.history("EGCH")
    assert [r.version for r in history] == [1, 2]
    assert history[0].website_probe_attempts[0].domain == "wrong-guess.com"
    assert memory.latest("EGCH").resolved_hostname == "egch.com.eg"


def test_record_persists_legal_entity_attempt_even_when_unmatched():
    memory = ResolutionMemory()
    memory.record(_record(legal_entity_attempts=[
        LegalEntityAttempt(source="gleif", matched=False, rejection_reason="no candidates"),
    ]))
    stored = memory.latest("EGCH")
    assert stored.legal_entity_attempts[0].matched is False
    assert stored.legal_name is None


def test_persists_and_reloads_from_disk(tmp_path):
    path = tmp_path / "resolution_memory.json"
    memory = ResolutionMemory(path)
    memory.record(_record(
        website_candidates_proposed=[ProposedWebsiteCandidate(hostname="egch.com.eg", source="wikidata", confidence=1.0)],
    ))

    reloaded = ResolutionMemory(path)
    stored = reloaded.latest("EGCH")
    assert stored is not None
    assert stored.website_candidates_proposed[0].hostname == "egch.com.eg"


def test_reserved_fields_default_empty_never_fabricated():
    record = _record()
    assert record.brand_names == []
    assert record.parent_company is None
    assert record.parent_company_source is None
    assert record.parent_company_evidence is None
