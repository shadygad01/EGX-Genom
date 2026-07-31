from agx_research.collectors.corporate_event_classifier import classify_corporate_event_type


def test_classifies_dividend():
    assert classify_corporate_event_type("COMI board declares cash dividend") == "DIVIDEND"


def test_classifies_stock_split_before_looser_terms():
    assert classify_corporate_event_type("MFPC announces 2-for-1 stock split") == "STOCK_SPLIT"


def test_classifies_earnings():
    assert classify_corporate_event_type("ETEL reports quarterly results") == "EARNINGS"
    assert classify_corporate_event_type("أبو قير تعلن مؤشرات نتائج الأعمال") == "EARNINGS"


def test_classifies_capital_increase():
    assert classify_corporate_event_type("Company approves capital increase via rights issue") == "CAPITAL_INCREASE"


def test_classifies_merger_and_acquisition_distinctly():
    assert classify_corporate_event_type("Company A to merge with Company B") == "MERGER"
    assert classify_corporate_event_type("Company A to acquire Company B") == "ACQUISITION"


def test_classifies_buyback():
    assert classify_corporate_event_type("Board approves share buyback program") == "BUYBACK"


def test_classifies_delisting():
    assert classify_corporate_event_type("Company announces voluntary delisting") == "DELISTING"


def test_classifies_management_change():
    assert classify_corporate_event_type("Board appoints new chairman") == "MANAGEMENT_CHANGE"


def test_classifies_guidance():
    assert classify_corporate_event_type("Company raises full-year guidance") == "GUIDANCE"


def test_case_insensitive():
    assert classify_corporate_event_type("COMPANY DECLARES DIVIDEND") == "DIVIDEND"


def test_returns_none_for_unrelated_headline():
    assert classify_corporate_event_type("Egypt central bank holds interest rates steady") is None


def test_returns_none_for_empty_string():
    assert classify_corporate_event_type("") is None
