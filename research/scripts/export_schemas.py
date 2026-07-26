"""Emit JSON Schema for the pydantic models the API and dashboard artifacts serve.

`api/src/types.ts` and `web/src/types.ts` are hand-maintained TypeScript
mirrors of these models (see `docs/ARCHITECTURE_AUDIT.md` for why full
codegen isn't justified yet). This script is the cheap alternative: it
writes each Python schema to `contracts/`, and CI re-runs it and fails the
build if the committed files don't match — so a schema change that isn't
reflected in the committed contract is caught immediately, forcing the
TS mirrors to be updated in the same PR instead of drifting silently.

Covers every model both `ApiProvider` and `StaticJsonProvider` serve (see
docs/ARCHITECTURE.md's "Dashboard data providers" section) — this is what
"both providers use exactly the same versioned contracts" means
concretely: one schema file per resource, generated from the one pydantic
model that produces both the API response and the static JSON artifact.
`patterns.json` has no entry here: it has no schema because
`HistoricalPatternsAgent` isn't implemented yet (see
`agx_research.dashboard.export.export_patterns`) — it's always `[]`.

Run via `uv run python scripts/export_schemas.py` from `research/`.
"""

from __future__ import annotations

import json
from pathlib import Path

from agx_research.dashboard.schemas import DashboardSystemStatus
from agx_research.events.event import Event
from agx_research.knowledge.schema import KnowledgeObject
from agx_research.market_memory.state import MarketState
from agx_research.meta.decision_engine import Recommendation
from agx_research.runtime.engine import RunRecord
from agx_research.sources.spec import SourceSpec
from agx_research.universe.provider import UniverseArtifact

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"

MODELS = {
    "knowledge_object.schema.json": KnowledgeObject,
    "event.schema.json": Event,
    "recommendation.schema.json": Recommendation,
    "market_state.schema.json": MarketState,
    "universe.schema.json": UniverseArtifact,
    "run_record.schema.json": RunRecord,
    "source_spec.schema.json": SourceSpec,
    "dashboard_system_status.schema.json": DashboardSystemStatus,
}


def main() -> None:
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, model_cls in MODELS.items():
        schema = model_cls.model_json_schema()
        out_path = CONTRACTS_DIR / filename
        out_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
