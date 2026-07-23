"""Stability verification: is this acquisition method likely to keep
working, as opposed to a session-bound or generated link that rots?

Two independent signals, both honestly partial (this is a proxy assessed
*before* any run history exists -- true stability is what
`sources.reputation`'s `schema_stability`/`availability` dimensions measure
over time once a source is actually collecting):

- URL shape: a canonical structured-file path (`.csv`/`.json`/`.rss`/`.pdf`)
  scores higher; a session/auth token or a long opaque generated-looking
  identifier in the URL scores lower.
- Repeated-probe consistency: if the caller supplies more than one probe of
  the same URL (taken at different times), agreement across their status
  codes raises the score. A single probe is honestly flagged
  `insufficient_data` rather than assigned a confident score.
"""

from __future__ import annotations

import re
from collections import Counter

from pydantic import BaseModel, Field

from agx_research.acquisition_intelligence.domain_resolution import ProbeResult

_SESSION_TOKEN_MARKERS = ["sessionid", "sid=", "token=", "jsessionid", "phpsessid", "authtoken"]
_STABLE_EXTENSIONS = (".csv", ".xml", ".json", ".rss", ".pdf", ".atom", ".xlsx")
_OPAQUE_ID_PATTERN = re.compile(r"[0-9a-f]{24,}")


class StabilityAssessment(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    insufficient_data: bool = False


def _url_shape_score(url: str) -> tuple[float, list[str]]:
    lower = url.lower()
    score = 0.5
    evidence: list[str] = []
    if any(marker in lower for marker in _SESSION_TOKEN_MARKERS):
        score -= 0.4
        evidence.append("URL appears to carry a session/auth token; unlikely to remain stable.")
    if any(ext in lower for ext in _STABLE_EXTENSIONS):
        score += 0.3
        evidence.append("URL has a canonical structured-file extension.")
    if _OPAQUE_ID_PATTERN.search(lower):
        score -= 0.2
        evidence.append("URL contains a long opaque identifier, suggesting a generated/temporary link.")
    return max(0.0, min(1.0, score)), evidence


def assess_stability(url: str, probes: list[ProbeResult] | None = None) -> StabilityAssessment:
    probes = probes or []
    shape_score, evidence = _url_shape_score(url)

    if not probes:
        return StabilityAssessment(score=shape_score, evidence=evidence, insufficient_data=True)

    status_codes = [p.status_code for p in probes if p.reachable and p.status_code is not None]
    if not status_codes:
        return StabilityAssessment(
            score=0.0, evidence=[*evidence, "No successful probe among those supplied."],
        )

    counts = Counter(status_codes)
    mode_count = counts.most_common(1)[0][1]
    consistency = mode_count / len(status_codes)
    evidence.append(f"{mode_count}/{len(status_codes)} probes returned the same status code.")

    return StabilityAssessment(
        score=(shape_score + consistency) / 2,
        evidence=evidence,
        insufficient_data=len(probes) < 2,
    )
