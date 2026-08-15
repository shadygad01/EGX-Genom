"""Governance contract for production research modules."""

import json
from pathlib import Path


MANIFEST = Path(__file__).parents[2] / "docs" / "decision-system" / "research_module_manifest.json"
REQUIRED_FIELDS = {
    "id",
    "question",
    "output",
    "uncertainty",
    "validation_status",
    "downstream_consumer",
    "freshness",
    "failure_mode",
}


def test_core_research_modules_declare_decision_governance() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1"
    modules = payload["modules"]
    assert modules
    ids = [module["id"] for module in modules]
    assert len(ids) == len(set(ids))
    for module in modules:
        assert REQUIRED_FIELDS <= set(module)
        assert all(str(module[field]).strip() for field in REQUIRED_FIELDS)
