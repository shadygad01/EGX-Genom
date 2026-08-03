from agx_research.discovery.resolution_memory import (
    Claim,
    ClaimAttribute,
    ClaimStatus,
    Observation,
    ObservationOutcome,
    ResolutionMemory,
    ResolutionMemoryRecord,
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
        observations=[
            Observation(attribute=ClaimAttribute.WEBSITE, source="heuristic_name_guess",
                        value="egch.com.eg", outcome=ObservationOutcome.REFUTED,
                        rejection_reason="connection refused"),
        ],
        claims=[
            Claim(attribute=ClaimAttribute.WEBSITE, value="egch.com.eg",
                  status=ClaimStatus.REFUTED, rejection_reason="connection refused",
                  supporting_observations=[0]),
        ],
    ))

    stored = memory.latest("EGCH")
    assert stored is not None
    assert stored.resolved_hostname is None
    assert stored.observations[0].outcome == ObservationOutcome.REFUTED
    assert stored.claims[0].status == ClaimStatus.REFUTED
    assert stored.claims[0].rejection_reason == "connection refused"


def test_record_auto_increments_version_and_keeps_full_history():
    """Every run's attempt is a new revision, never an overwrite -- a
    rejected domain from an earlier run stays readable via history()."""
    memory = ResolutionMemory()
    memory.record(_record(
        observations=[Observation(attribute=ClaimAttribute.WEBSITE, source="heuristic_name_guess",
                                   value="wrong-guess.com", outcome=ObservationOutcome.REFUTED)],
    ))
    memory.record(_record(
        resolved_hostname="egch.com.eg",
        observations=[Observation(attribute=ClaimAttribute.WEBSITE, source="web_search",
                                   value="egch.com.eg", outcome=ObservationOutcome.VERIFIED)],
    ))

    history = memory.history("EGCH")
    assert [r.version for r in history] == [1, 2]
    assert history[0].observations[0].value == "wrong-guess.com"
    assert memory.latest("EGCH").resolved_hostname == "egch.com.eg"


def test_record_persists_legal_entity_claim_even_when_unmatched():
    memory = ResolutionMemory()
    memory.record(_record(
        observations=[Observation(attribute=ClaimAttribute.LEGAL_NAME, source="gleif",
                                   outcome=ObservationOutcome.ABSENT, rejection_reason="no candidates")],
        claims=[Claim(attribute=ClaimAttribute.LEGAL_NAME, status=ClaimStatus.NOT_FOUND,
                      rejection_reason="no candidates", supporting_observations=[0])],
    ))
    stored = memory.latest("EGCH")
    assert stored.claims[0].status == ClaimStatus.NOT_FOUND
    assert stored.legal_name is None


def test_claim_traces_back_to_its_supporting_observations():
    """A claim's synthesis must be traceable to real, immutable evidence --
    never asserted independently of it."""
    observations = [
        Observation(attribute=ClaimAttribute.WEBSITE, source="web_search",
                    value="cibeg.com", outcome=ObservationOutcome.PROPOSED),
        Observation(attribute=ClaimAttribute.WEBSITE, source="web_search",
                    value="cibeg.com", outcome=ObservationOutcome.VERIFIED, evidence="HTTP 200"),
    ]
    claim = Claim(attribute=ClaimAttribute.WEBSITE, value="cibeg.com",
                  status=ClaimStatus.CONFIRMED, supporting_observations=[0, 1])
    record = _record(ticker="COMI", observations=observations, claims=[claim])

    referenced = [record.observations[i] for i in record.claims[0].supporting_observations]
    assert referenced[0].outcome == ObservationOutcome.PROPOSED
    assert referenced[1].outcome == ObservationOutcome.VERIFIED
    assert referenced[1].evidence == "HTTP 200"


def test_persists_and_reloads_from_disk(tmp_path):
    path = tmp_path / "resolution_memory.json"
    memory = ResolutionMemory(path)
    memory.record(_record(
        observations=[Observation(attribute=ClaimAttribute.WEBSITE, source="wikidata",
                                   value="egch.com.eg", outcome=ObservationOutcome.PROPOSED)],
    ))

    reloaded = ResolutionMemory(path)
    stored = reloaded.latest("EGCH")
    assert stored is not None
    assert stored.observations[0].value == "egch.com.eg"


def test_reserved_fields_default_empty_never_fabricated():
    record = _record()
    assert record.brand_names == []
    assert record.parent_company is None
    assert record.observations == []
    assert record.claims == []
