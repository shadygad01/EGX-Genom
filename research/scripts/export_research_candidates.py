from __future__ import annotations

import json
import sys
from pathlib import Path

from agx_research.meta.readiness import DecisionReadiness
from agx_research.meta.research_candidates import build_research_candidates


def main() -> None:
    directory = Path(sys.argv[1])
    rows = [DecisionReadiness.model_validate(row) for row in json.loads((directory / "decision_readiness.json").read_text())]
    output = [candidate.model_dump(mode="json") for candidate in build_research_candidates(rows)]
    (directory / "research_candidates.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(output)} research candidates to {directory / 'research_candidates.json'}")


if __name__ == "__main__":
    main()
