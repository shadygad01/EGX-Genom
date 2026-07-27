from agx_research.agents.news_sentiment import classify_headline_sentiment


def test_classifies_positive_phrase():
    assert classify_headline_sentiment("CIB reports strong Q2 net income growth") == "positive"


def test_classifies_negative_phrase():
    assert classify_headline_sentiment("Company reports net loss for the quarter") == "negative"


def test_returns_none_for_unmatched_headline():
    assert classify_headline_sentiment("EGX30 index closes flat in quiet trading") is None


def test_negative_checked_before_positive_on_mixed_headline():
    # Contains both a negative ("profit decline") and a positive ("special
    # dividend") signal; negative is checked first so this doesn't
    # silently read as good news.
    assert classify_headline_sentiment("Company reports profit decline despite special dividend") == "negative"


def test_case_insensitive():
    assert classify_headline_sentiment("STRONG GROWTH REPORTED") == "positive"
