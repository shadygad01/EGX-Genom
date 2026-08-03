from agx_research.discovery.wikidata_lookup import (
    WikidataOfficialWebsiteClient,
    build_wikidata_claims_url,
    build_wikidata_search_url,
    parse_wikidata_official_website,
    parse_wikidata_search_results,
)

_SEARCH_RESPONSE_COMI = {
    "search": [
        {"id": "Q1163037", "label": "Commercial International Bank", "description": "bank in Egypt"},
        {"id": "Q999999", "label": "Some Other Bank", "description": "unrelated"},
    ]
}

_CLAIMS_RESPONSE_WITH_WEBSITE = {
    "claims": {
        "P856": [
            {
                "mainsnak": {
                    "property": "P856",
                    "datavalue": {"value": "https://www.cibeg.com/en", "type": "string"},
                    "datatype": "url",
                },
                "type": "statement",
                "rank": "normal",
            }
        ]
    }
}


def test_parse_wikidata_search_results_reads_real_entries():
    results = parse_wikidata_search_results(_SEARCH_RESPONSE_COMI)
    assert results == [
        ("Q1163037", "Commercial International Bank"),
        ("Q999999", "Some Other Bank"),
    ]


def test_parse_wikidata_search_results_empty_response():
    assert parse_wikidata_search_results({"search": []}) == []
    assert parse_wikidata_search_results({}) == []


def test_parse_wikidata_search_results_skips_entry_missing_label():
    payload = {"search": [{"id": "Q1"}, {"id": "Q2", "label": "Real Label"}]}
    assert parse_wikidata_search_results(payload) == [("Q2", "Real Label")]


def test_parse_wikidata_official_website_reads_real_claim():
    assert parse_wikidata_official_website(_CLAIMS_RESPONSE_WITH_WEBSITE) == "https://www.cibeg.com/en"


def test_parse_wikidata_official_website_no_claim():
    assert parse_wikidata_official_website({"claims": {}}) is None
    assert parse_wikidata_official_website({}) is None


def test_parse_wikidata_official_website_ignores_novalue_snak():
    payload = {"claims": {"P856": [{"mainsnak": {"snaktype": "novalue"}}]}}
    assert parse_wikidata_official_website(payload) is None


def test_build_wikidata_search_url_encodes_the_company_name():
    url = build_wikidata_search_url("Commercial International Bank")
    assert url.startswith("https://www.wikidata.org/w/api.php?action=wbsearchentities")
    assert "search=Commercial%20International%20Bank" in url
    assert "format=json" in url


def test_build_wikidata_claims_url_targets_the_entity_and_p856():
    url = build_wikidata_claims_url("Q1163037")
    assert url.startswith("https://www.wikidata.org/w/api.php?action=wbgetclaims")
    assert "entity=Q1163037" in url
    assert "property=P856" in url


def test_client_lookup_matches_search_result_and_reads_its_claim():
    calls = []

    def fetch_json(url):
        calls.append(url)
        if "wbsearchentities" in url:
            return _SEARCH_RESPONSE_COMI
        return _CLAIMS_RESPONSE_WITH_WEBSITE

    client = WikidataOfficialWebsiteClient(fetch_json)
    result = client.lookup({"COMI": "Commercial International Bank"})

    assert result == {"COMI": "www.cibeg.com"}
    assert len(calls) == 2
    assert "wbsearchentities" in calls[0]
    assert "wbgetclaims" in calls[1] and "Q1163037" in calls[1]


def test_client_lookup_skips_a_company_with_no_matching_search_result():
    def fetch_json(url):
        return {"search": [{"id": "Q1", "label": "Completely Unrelated Company"}]}

    client = WikidataOfficialWebsiteClient(fetch_json)
    assert client.lookup({"HRHO": "EFG Hermes Holding"}) == {}


def test_client_lookup_skips_a_company_whose_matched_entity_has_no_website_claim():
    def fetch_json(url):
        if "wbsearchentities" in url:
            return _SEARCH_RESPONSE_COMI
        return {"claims": {}}

    client = WikidataOfficialWebsiteClient(fetch_json)
    assert client.lookup({"COMI": "Commercial International Bank"}) == {}


def test_client_lookup_one_company_failing_does_not_block_the_rest():
    def fetch_json(url):
        if "search=Bad" in url:
            return None  # simulates an unreachable/malformed response
        if "wbsearchentities" in url:
            return _SEARCH_RESPONSE_COMI
        return _CLAIMS_RESPONSE_WITH_WEBSITE

    client = WikidataOfficialWebsiteClient(fetch_json)
    result = client.lookup({
        "BAD": "Bad Company",
        "COMI": "Commercial International Bank",
    })
    assert result == {"COMI": "www.cibeg.com"}


def test_client_lookup_empty_companies():
    calls = []
    client = WikidataOfficialWebsiteClient(lambda url: calls.append(url))
    assert client.lookup({}) == {}
    assert calls == []


def test_lookup_with_trace_records_a_matched_attempt():
    def fetch_json(url):
        if "wbsearchentities" in url:
            return _SEARCH_RESPONSE_COMI
        return _CLAIMS_RESPONSE_WITH_WEBSITE

    client = WikidataOfficialWebsiteClient(fetch_json)
    trace = client.lookup_with_trace({"COMI": "Commercial International Bank"})

    attempt = trace["COMI"]
    assert attempt.matched is True
    assert attempt.hostname == "www.cibeg.com"
    assert attempt.matched_entity_id == "Q1163037"
    assert attempt.matched_label == "Commercial International Bank"
    assert attempt.rejection_reason is None


def test_lookup_with_trace_records_no_search_hit_reason():
    def fetch_json(url):
        return {"search": [{"id": "Q1", "label": "Completely Unrelated Company"}]}

    client = WikidataOfficialWebsiteClient(fetch_json)
    trace = client.lookup_with_trace({"HRHO": "EFG Hermes Holding"})

    attempt = trace["HRHO"]
    assert attempt.matched is False
    assert attempt.hostname is None
    assert "token" in attempt.rejection_reason.lower()


def test_lookup_with_trace_records_no_claim_reason():
    def fetch_json(url):
        if "wbsearchentities" in url:
            return _SEARCH_RESPONSE_COMI
        return {"claims": {}}

    client = WikidataOfficialWebsiteClient(fetch_json)
    trace = client.lookup_with_trace({"COMI": "Commercial International Bank"})

    attempt = trace["COMI"]
    assert attempt.matched is False
    assert attempt.matched_entity_id == "Q1163037"
    assert "P856" in attempt.rejection_reason


def test_lookup_with_trace_records_empty_search_reason():
    client = WikidataOfficialWebsiteClient(lambda url: {"search": []})
    trace = client.lookup_with_trace({"EGCH": "Egyptian Chemical Industries"})

    attempt = trace["EGCH"]
    assert attempt.matched is False
    assert "no candidate" in attempt.rejection_reason.lower()


def test_lookup_delegates_to_lookup_with_trace():
    """lookup() must still return exactly what it always did."""
    def fetch_json(url):
        if "wbsearchentities" in url:
            return _SEARCH_RESPONSE_COMI
        return _CLAIMS_RESPONSE_WITH_WEBSITE

    client = WikidataOfficialWebsiteClient(fetch_json)
    assert client.lookup({"COMI": "Commercial International Bank"}) == {"COMI": "www.cibeg.com"}
