"""Emit JSON Schema for the pydantic models the API serves over HTTP.

`api/src/types.ts` and `web/src/types.ts` are hand-maintained TypeScript
mirrors of `KnowledgeObject` (see `docs/ARCHITECTURE_AUDIT.md` for why full
codegen isn't justified yet). This script is the cheap alternative: it
writes the Python schema to `contracts/`, and CI re-runs it and fails the
build if the committed file doesn't match — so a schema change that isn't
reflected in the committed contract is caught immediately, forcing the
TS mirrors to be updated in the same PR instead of drifting silently.

Run via `uv run python scripts/export_schemas.py` from `research/`.
"""

from __future__ import annotations

import json
from pathlib import Path

from agx_research.knowledge.schema import KnowledgeObject

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"


def main() -> None:
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    schema = KnowledgeObject.model_json_schema()
    out_path = CONTRACTS_DIR / "knowledge_object.schema.json"
    out_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
