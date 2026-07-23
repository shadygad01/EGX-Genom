"""AcquisitionContinuityMonitor: "continue researching alternative
acquisition methods whenever one becomes unavailable."

Watches the `SourceRegistry` for sources whose `health_status` has gone
`DOWN` (as maintained by `sources.health.HealthMonitor` during real
collection runs) that map back to a known `TargetOrganization`, and
re-invokes the `AcquisitionIntelligenceEngine` for that organization,
excluding the failed method's URL -- letting discovery + ranking find the
next-best alternative rather than leaving the source permanently broken.
A target with no alternative left simply reports why, same as any other
`AcquisitionResult` with `registered=False`; this monitor never fabricates
a replacement that doesn't exist.
"""

from __future__ import annotations

from agx_research.acquisition_intelligence.engine import AcquisitionIntelligenceEngine, AcquisitionResult
from agx_research.acquisition_intelligence.target import TargetOrganization
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.spec import HealthStatus


class AcquisitionContinuityMonitor:
    def __init__(self, engine: AcquisitionIntelligenceEngine, targets: list[TargetOrganization]):
        self.engine = engine
        self.targets_by_source_id = {
            (t.existing_source_id or t.id): t for t in targets
        }

    def check_and_recover(self, registry: SourceRegistry) -> list[AcquisitionResult]:
        results = []
        for spec in registry.by_health_status(HealthStatus.DOWN):
            target = self.targets_by_source_id.get(spec.id)
            if target is None or target.per_constituent:
                continue
            exclude = {spec.base_url} if spec.base_url else set()
            results.append(self.engine.run_for_target(target, exclude_urls=exclude))
        return results
