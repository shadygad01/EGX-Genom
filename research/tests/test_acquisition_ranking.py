from agx_research.acquisition_intelligence.historical import HistoricalAvailabilityAssessment
from agx_research.acquisition_intelligence.legality import LegalityAssessment, LegalityVerdict
from agx_research.acquisition_intelligence.ranking import rank_methods, select_best
from agx_research.acquisition_intelligence.stability import StabilityAssessment
from agx_research.discovery.candidate import DiscoveryMethod, SourceCandidate
from agx_research.sources.spec import AccessMethod


def candidate(url="https://example.com/feed.xml"):
    return SourceCandidate(
        discovered_url=url, origin_page_url="https://example.com",
        discovery_method=DiscoveryMethod.RSS_AUTODISCOVERY,
        access_method_guess=AccessMethod.RSS_FEED,
    )


def test_blocked_and_ambiguous_methods_excluded_from_ranking():
    entries = [
        (
            candidate("https://a"),
            LegalityAssessment(verdict=LegalityVerdict.BLOCKED),
            StabilityAssessment(score=1.0),
            HistoricalAvailabilityAssessment(score=1.0, has_any_snapshot=True),
        ),
        (
            candidate("https://b"),
            LegalityAssessment(verdict=LegalityVerdict.AMBIGUOUS),
            StabilityAssessment(score=1.0),
            HistoricalAvailabilityAssessment(score=1.0, has_any_snapshot=True),
        ),
    ]
    assert rank_methods(entries) == []


def test_allowed_methods_ranked_by_composite_score_descending():
    entries = [
        (
            candidate("https://low"),
            LegalityAssessment(verdict=LegalityVerdict.ALLOWED),
            StabilityAssessment(score=0.2),
            HistoricalAvailabilityAssessment(score=0.2, has_any_snapshot=True),
        ),
        (
            candidate("https://high"),
            LegalityAssessment(verdict=LegalityVerdict.ALLOWED),
            StabilityAssessment(score=0.9),
            HistoricalAvailabilityAssessment(score=0.9, has_any_snapshot=True),
        ),
    ]
    ranked = rank_methods(entries)
    assert [r.candidate.discovered_url for r in ranked] == ["https://high", "https://low"]


def test_select_best_returns_top_ranked_or_none():
    assert select_best([]) is None
    entries = [
        (
            candidate(),
            LegalityAssessment(verdict=LegalityVerdict.ALLOWED),
            StabilityAssessment(score=0.5),
            HistoricalAvailabilityAssessment(score=0.5, has_any_snapshot=True),
        ),
    ]
    ranked = rank_methods(entries)
    best = select_best(ranked)
    assert best is ranked[0]
