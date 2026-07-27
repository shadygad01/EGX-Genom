from agx_research.discovery.wikidata_lookup import (
    WikidataOfficialWebsiteClient,
    build_wikidata_query_url,
    match_wikidata_websites_to_companies,
    parse_wikidata_company_websites,
)

_SPARQL_RESPONSE = {
    "results": {
        "bindings": [
            {
                "companyLabel": {"type": "literal", "value": "Commercial International Bank"},
                "website": {"type": "uri", "value": "https://www.cibeg.com/en"},
            },
            {
                "companyLabel": {"type": "literal", "value": "Telecom Egypt Co."},
                "website": {"type": "uri", "value": "https://www.telecomegypt.com.eg/"},
            },
            # No `website` binding at all -- P856 wasn't set for this hit;
            # must be skipped, not defaulted to something invented.
            {"companyLabel": {"type": "literal", "value": "Some Other Company"}},
        ]
    }
}

_COMPANIES = {
    "COMI": "Commercial International Bank",
    "ETEL": "Telecom Egypt",
    "HRHO": "EFG Hermes Holding",  # not in the response -- must not match anything
}


def test_parse_wikidata_company_websites_reads_real_bindings():
    result = parse_wikidata_company_websites(_SPARQL_RESPONSE)
    assert result == {
        "Commercial International Bank": "https://www.cibeg.com/en",
        "Telecom Egypt Co.": "https://www.telecomegypt.com.eg/",
    }


def test_parse_wikidata_company_websites_empty_response():
    assert parse_wikidata_company_websites({"results": {"bindings": []}}) == {}
    assert parse_wikidata_company_websites({}) == {}


def test_match_wikidata_websites_to_companies_matches_by_name_token_overlap():
    labels_to_websites = parse_wikidata_company_websites(_SPARQL_RESPONSE)
    found = match_wikidata_websites_to_companies(labels_to_websites, _COMPANIES)
    assert found["COMI"] == "www.cibeg.com"
    assert found["ETEL"] == "www.telecomegypt.com.eg"


def test_match_wikidata_websites_to_companies_never_matches_a_company_not_in_the_response():
    labels_to_websites = parse_wikidata_company_websites(_SPARQL_RESPONSE)
    found = match_wikidata_websites_to_companies(labels_to_websites, _COMPANIES)
    assert "HRHO" not in found


def test_match_wikidata_websites_to_companies_ignores_a_website_with_no_hostname():
    found = match_wikidata_websites_to_companies(
        {"Commercial International Bank": "not-a-url"}, _COMPANIES
    )
    assert found == {}


def test_build_wikidata_query_url_targets_the_real_sparql_endpoint_with_json_format():
    url = build_wikidata_query_url()
    assert url.startswith("https://query.wikidata.org/sparql?query=")
    assert url.endswith("&format=json")


def test_client_lookup_returns_ticker_to_hostname():
    calls = []

    def fetch_json(url):
        calls.append(url)
        return _SPARQL_RESPONSE

    client = WikidataOfficialWebsiteClient(fetch_json)
    result = client.lookup(_COMPANIES)

    assert result == {"COMI": "www.cibeg.com", "ETEL": "www.telecomegypt.com.eg"}
    assert len(calls) == 1
    assert "query.wikidata.org/sparql" in calls[0]


def test_client_lookup_degrades_to_empty_on_unreachable_endpoint():
    client = WikidataOfficialWebsiteClient(lambda url: {})
    assert client.lookup(_COMPANIES) == {}


def test_client_lookup_degrades_to_empty_on_malformed_non_dict_response():
    client = WikidataOfficialWebsiteClient(lambda url: None)
    assert client.lookup(_COMPANIES) == {}
