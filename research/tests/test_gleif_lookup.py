from agx_research.discovery.gleif_lookup import (
    GleifLegalEntityClient,
    build_fuzzy_completions_url,
    build_lei_record_url,
    parse_fuzzy_completions,
    parse_lei_record,
)

_FUZZY_RESPONSE_JUFO = {
    "data": [
        {
            "type": "fuzzycompletions",
            "attributes": {"value": "JUHAYNA FOOD INDUSTRIES S.A.E."},
            "relationships": {"lei-records": {"data": {"type": "lei-records", "id": "LEI123456789JUFO0"}}},
        },
        {
            "type": "fuzzycompletions",
            "attributes": {"value": "Some Unrelated Dairy Company"},
            "relationships": {"lei-records": {"data": {"type": "lei-records", "id": "LEI000000000UNREL"}}},
        },
    ]
}

_RECORD_RESPONSE_JUFO = {
    "data": {
        "type": "lei-records",
        "id": "LEI123456789JUFO0",
        "attributes": {
            "lei": "LEI123456789JUFO0",
            "entity": {
                "legalName": {"name": "JUHAYNA FOOD INDUSTRIES S.A.E.", "language": "en"},
                "otherNames": [{"name": "Juhayna", "type": "TRADING_OR_OPERATING_NAME", "language": "en"}],
                "transliteratedOtherNames": [
                    {"name": "جهينة لصناعة الأغذية", "type": "TRADING_OR_OPERATING_NAME", "language": "ar"}
                ],
                "legalAddress": {"country": "EG"},
            },
            "registration": {"status": "ISSUED"},
        },
    }
}


def test_parse_fuzzy_completions_reads_real_entries():
    results = parse_fuzzy_completions(_FUZZY_RESPONSE_JUFO)
    assert results == [
        ("LEI123456789JUFO0", "JUHAYNA FOOD INDUSTRIES S.A.E."),
        ("LEI000000000UNREL", "Some Unrelated Dairy Company"),
    ]


def test_parse_fuzzy_completions_empty_response():
    assert parse_fuzzy_completions({"data": []}) == []
    assert parse_fuzzy_completions({}) == []


def test_parse_fuzzy_completions_skips_entry_missing_lei_relationship():
    payload = {"data": [{"attributes": {"value": "No LEI Here"}, "relationships": {}}]}
    assert parse_fuzzy_completions(payload) == []


def test_parse_lei_record_reads_real_record():
    match = parse_lei_record(_RECORD_RESPONSE_JUFO)
    assert match is not None
    assert match.lei == "LEI123456789JUFO0"
    assert match.legal_name == "JUHAYNA FOOD INDUSTRIES S.A.E."
    assert match.aliases == ["Juhayna", "جهينة لصناعة الأغذية"]
    assert match.jurisdiction_country == "EG"
    assert match.registration_status == "ISSUED"


def test_parse_lei_record_missing_entity_returns_none():
    assert parse_lei_record({"data": {"attributes": {}}}) is None
    assert parse_lei_record({}) is None


def test_build_fuzzy_completions_url_encodes_the_company_name():
    url = build_fuzzy_completions_url("Juhayna Food Industries")
    assert url.startswith("https://api.gleif.org/api/v1/fuzzycompletions")
    assert "field=entity.legalName" in url
    assert "q=Juhayna%20Food%20Industries" in url


def test_build_lei_record_url_targets_the_lei():
    url = build_lei_record_url("LEI123456789JUFO0")
    assert url == "https://api.gleif.org/api/v1/lei-records/LEI123456789JUFO0"


def test_client_lookup_matches_fuzzy_result_and_reads_its_record():
    calls = []

    def fetch_json(url):
        calls.append(url)
        if "fuzzycompletions" in url:
            return _FUZZY_RESPONSE_JUFO
        return _RECORD_RESPONSE_JUFO

    client = GleifLegalEntityClient(fetch_json)
    result = client.lookup({"JUFO": "Juhayna Food Industries"})

    assert "JUFO" in result
    match = result["JUFO"]
    assert match.legal_name == "JUHAYNA FOOD INDUSTRIES S.A.E."
    assert match.aliases == ["Juhayna", "جهينة لصناعة الأغذية"]
    assert match.match_confidence > 0
    assert len(calls) == 2
    assert "fuzzycompletions" in calls[0]
    assert "LEI123456789JUFO0" in calls[1]


def test_client_lookup_skips_a_company_with_no_token_overlap_match():
    def fetch_json(url):
        return {"data": [{"attributes": {"value": "Completely Unrelated Corp"},
                           "relationships": {"lei-records": {"data": {"id": "LEIXXXX"}}}}]}

    client = GleifLegalEntityClient(fetch_json)
    assert client.lookup({"HRHO": "EFG Hermes Holding"}) == {}


def test_client_lookup_skips_a_company_whose_matched_lei_record_fetch_fails():
    def fetch_json(url):
        if "fuzzycompletions" in url:
            return _FUZZY_RESPONSE_JUFO
        return {}

    client = GleifLegalEntityClient(fetch_json)
    assert client.lookup({"JUFO": "Juhayna Food Industries"}) == {}


def test_client_lookup_one_company_failing_does_not_block_the_rest():
    def fetch_json(url):
        if "q=Bad" in url:
            return None  # simulates an unreachable/malformed response
        if "fuzzycompletions" in url:
            return _FUZZY_RESPONSE_JUFO
        return _RECORD_RESPONSE_JUFO

    client = GleifLegalEntityClient(fetch_json)
    result = client.lookup({
        "BAD": "Bad Company",
        "JUFO": "Juhayna Food Industries",
    })
    assert set(result.keys()) == {"JUFO"}


def test_client_lookup_empty_companies():
    calls = []
    client = GleifLegalEntityClient(lambda url: calls.append(url))
    assert client.lookup({}) == {}
    assert calls == []
