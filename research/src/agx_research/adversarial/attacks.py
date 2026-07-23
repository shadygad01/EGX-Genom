"""What the Adversarial Scientist produces: one AttackResult per attack type."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from agx_research.domain.provenance import Provenance


class AttackType(str, Enum):
    RANDOM_COINCIDENCE = "random_coincidence"
    SMALL_SAMPLE_BIAS = "small_sample_bias"
    TIME_LEAKAGE = "time_leakage"
    LOOK_AHEAD_BIAS = "look_ahead_bias"
    OVERFITTING = "overfitting"
    PARAMETER_INSTABILITY = "parameter_instability"
    REGIME_DEPENDENCY = "regime_dependency"
    OUT_OF_SAMPLE_DEGRADATION = "out_of_sample_degradation"
    WEAK_ECONOMIC_RATIONALE = "weak_economic_rationale"


class AttackResult(BaseModel):
    attack_type: AttackType
    attempted: bool
    succeeded: bool  # True = the attack found a real problem; confidence should drop
    confidence_delta: float
    notes: str = ""
    provenance: Provenance
