"""Declared source-to-decision routes, enforced for every active source.

An IMPLEMENTED source is not considered integrated merely because it can be
downloaded.  It must have a canonical record path and a named decision
consumer.  This registry deliberately fails closed when a future source is
promoted without declaring that path.
"""

from __future__ import annotations

from typing import Any

from agx_research.sources.registry import SourceRegistry

DECISION_ROUTES: dict[str, dict[str, Any]] = {
    "stooq": {
        "records": ["price_bars"],
        "consumers": [
            "market_structure_agent",
            "liquidity_agent",
            "technical_structure_agent",
            "validation",
            "meta_decision_engine",
        ],
    },
    "fred": {
        "records": ["macro_observations"],
        "consumers": ["macro_agent", "validation", "meta_decision_engine"],
    },
    "worldbank": {
        "records": ["macro_observations"],
        "consumers": ["macro_agent", "validation", "meta_decision_engine"],
    },
    "rss_generic": {
        "records": ["news_items", "events"],
        "consumers": ["event_risk_overlay", "meta_decision_engine"],
    },
    "enterprise_press": {
        "records": ["news_items", "corporate_events", "events"],
        "consumers": ["corporate_events_agent", "event_risk_overlay", "meta_decision_engine"],
    },
    "fra_egypt": {
        "records": ["news_items", "corporate_events", "events"],
        "consumers": ["corporate_events_agent", "event_risk_overlay", "meta_decision_engine"],
    },
    "gdelt": {
        "records": ["news_items", "events"],
        "consumers": ["event_risk_overlay", "meta_decision_engine"],
    },
    # Coverage alias: actual observations arrive through its two named providers.
    "global_benchmarks": {
        "records": ["price_bars", "macro_observations"],
        "delegates_to": ["stooq", "fred"],
        "consumers": ["market_agents", "macro_agent", "meta_decision_engine"],
    },
}


def export_decision_routes(registry: SourceRegistry) -> list[dict[str, Any]]:
    implemented_ids = {source.id for source in registry.collectable()}
    missing = sorted(implemented_ids - DECISION_ROUTES.keys())
    if missing:
        raise ValueError(
            "IMPLEMENTED source(s) lack a declared decision route: " + ", ".join(missing)
        )
    return [
        {"source_id": source_id, **DECISION_ROUTES[source_id]}
        for source_id in sorted(implemented_ids)
    ]
