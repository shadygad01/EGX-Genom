from agx_research.acquisition_intelligence.config_generation import (
    generate_source_spec,
    suggest_collector,
)
from agx_research.acquisition_intelligence.continuity import AcquisitionContinuityMonitor
from agx_research.acquisition_intelligence.domain_resolution import (
    HeuristicDomainResolver,
    ProbeResult,
    ResolvedDomain,
)
from agx_research.acquisition_intelligence.engine import AcquisitionIntelligenceEngine, AcquisitionResult
from agx_research.acquisition_intelligence.historical import (
    HistoricalAvailabilityAssessment,
    WaybackAvailabilityClient,
    assess_historical_availability,
    parse_cdx_timestamps,
    parse_closest_snapshot,
)
from agx_research.acquisition_intelligence.live import (
    build_live_fetch_text,
    build_live_prober,
    build_live_robots_checker,
    build_live_wayback_client,
)
from agx_research.acquisition_intelligence.legality import (
    LegalityAssessment,
    LegalityVerdict,
    assess_legality,
)
from agx_research.acquisition_intelligence.ranking import RankedMethod, rank_methods, select_best
from agx_research.acquisition_intelligence.stability import StabilityAssessment, assess_stability
from agx_research.acquisition_intelligence.target import (
    TargetOrganization,
    generate_company_ir_targets,
    seed_target_organizations,
)

__all__ = [
    "TargetOrganization",
    "seed_target_organizations",
    "generate_company_ir_targets",
    "ProbeResult",
    "ResolvedDomain",
    "HeuristicDomainResolver",
    "LegalityVerdict",
    "LegalityAssessment",
    "assess_legality",
    "StabilityAssessment",
    "assess_stability",
    "HistoricalAvailabilityAssessment",
    "WaybackAvailabilityClient",
    "parse_closest_snapshot",
    "parse_cdx_timestamps",
    "assess_historical_availability",
    "RankedMethod",
    "rank_methods",
    "select_best",
    "suggest_collector",
    "generate_source_spec",
    "AcquisitionIntelligenceEngine",
    "AcquisitionResult",
    "AcquisitionContinuityMonitor",
    "build_live_prober",
    "build_live_fetch_text",
    "build_live_robots_checker",
    "build_live_wayback_client",
]
