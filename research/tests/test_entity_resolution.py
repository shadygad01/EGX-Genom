from agx_research.universe.entity_resolution import resolve_ticker_mentions


def test_matches_exact_ticker_word():
    companies = {"COMI": "Commercial International Bank-Egypt (CIB)"}
    assert resolve_ticker_mentions("COMI reports strong Q2 net income growth", companies) == ["COMI"]


def test_does_not_match_ticker_as_substring_of_a_longer_word():
    # The real near-miss the project owner's plan named: VLMR must not
    # match inside VLMRA.
    companies = {"VLMR": "Al Volcano Marble"}
    assert resolve_ticker_mentions("VLMRA reports quarterly results", companies) == []


def test_matches_company_name_when_every_significant_token_present():
    companies = {"MFPC": "Misr Fertilizers Production Co. (MOPCO)"}
    # "misr"/"fertilizers"/"mopco" are the significant tokens ("co" and
    # "production" are declared stopwords) -- all three must appear:
    assert resolve_ticker_mentions("MOPCO board declares dividend", companies) == []
    assert resolve_ticker_mentions("Misr Fertilizers reports strong MOPCO earnings", companies) == ["MFPC"]


def test_partial_company_name_does_not_match():
    companies = {"MFPC": "Misr Fertilizers Production Co. (MOPCO)"}
    assert resolve_ticker_mentions("Misr reports earnings", companies) == []


def test_empty_company_name_only_matches_by_ticker():
    companies = {"XYZ": ""}
    assert resolve_ticker_mentions("Some unrelated headline about xyz", companies) == ["XYZ"]
    assert resolve_ticker_mentions("Some unrelated headline", companies) == []


def test_multiple_companies_can_match_one_headline():
    companies = {
        "COMI": "Commercial International Bank-Egypt (CIB)",
        "MFPC": "Misr Fertilizers Production Co. (MOPCO)",
    }
    matched = resolve_ticker_mentions("COMI and MFPC both report earnings", companies)
    assert set(matched) == {"COMI", "MFPC"}
