"""The post-promotion knowledge lifecycle: Promotion -> Monitoring -> Retirement.

Birth and Validation happen at the hypothesis stage (see the configurable
gate pipeline in `agx_research.hypotheses.pipeline`) and end at its final
gate (`PEER_VALIDATION` by default). Once a hypothesis is promoted it
becomes a KnowledgeObject and enters this lifecycle instead.
"""

from __future__ import annotations

from enum import Enum


class KnowledgeStatus(str, Enum):
    PROMOTED = "promoted"
    MONITORING = "monitoring"
    RETIRED = "retired"


_ALLOWED_TRANSITIONS: dict[KnowledgeStatus, set[KnowledgeStatus]] = {
    KnowledgeStatus.PROMOTED: {KnowledgeStatus.MONITORING, KnowledgeStatus.RETIRED},
    KnowledgeStatus.MONITORING: {KnowledgeStatus.RETIRED},
    KnowledgeStatus.RETIRED: set(),
}


def can_transition(current: KnowledgeStatus, target: KnowledgeStatus) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]
