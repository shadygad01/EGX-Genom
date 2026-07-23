"""The validation pipeline a hypothesis moves through, as data rather than code.

`StageName` gives a default, readable vocabulary matching the scientific
method described in the vision document, but `GateSpec.name` accepts any
string. A hypothesis can be constructed against a custom pipeline — e.g. a
lighter-weight track for Micro Alpha screening, or an extra
"REGIME_ROBUSTNESS" gate for Investment Alpha — without touching this
module or `hypothesis.py`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class StageName(str, Enum):
    OBSERVATION = "OBSERVATION"
    HYPOTHESIS = "HYPOTHESIS"
    DATA_COLLECTION = "DATA_COLLECTION"
    EXPERIMENT = "EXPERIMENT"
    STATISTICAL_VALIDATION = "STATISTICAL_VALIDATION"
    STRESS_TEST = "STRESS_TEST"
    BACKTEST = "BACKTEST"
    PEER_VALIDATION = "PEER_VALIDATION"


class GateSpec(BaseModel):
    """One named gate in a validation pipeline, in a fixed order."""

    name: str
    order: int


DEFAULT_PIPELINE: list[GateSpec] = [
    GateSpec(name=stage.value, order=i) for i, stage in enumerate(StageName)
]
