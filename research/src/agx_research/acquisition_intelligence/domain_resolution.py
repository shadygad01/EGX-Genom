"""Domain resolution: turn a `TargetOrganization` identity into a verified,
reachable homepage -- never a manually-supplied or assumed URL.

`HeuristicDomainResolver` never *asserts* a domain is real: every candidate
(whether from `TargetOrganization.domain_hints` -- public brand knowledge,
not a hand-picked acquisition endpoint -- or generated from the org's name)
is checked with an injected `Prober` callable, and only a domain that
actually answers becomes a `ResolvedDomain`. In a real deployment the
prober is backed by `collectors.fetcher.HttpFetcher`; in tests it's a fake
dict lookup, so this module has no network dependency of its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from agx_research.acquisition_intelligence.target import TargetOrganization


@dataclass
class ProbeResult:
    url: str
    reachable: bool
    status_code: int | None = None
    latency_seconds: float | None = None
    content_type: str | None = None
    body: str | None = None  # only populated by callers that also want the page text
    error: str | None = None


Prober = Callable[[str], ProbeResult]


@dataclass
class ResolvedDomain:
    domain: str
    homepage_url: str
    probe: ProbeResult
    origin: str  # "hint" | "heuristic" -- was this a known brand hint or a generated guess


def _normalize_name(name: str) -> str:
    stripped = re.sub(r"\(.*?\)", "", name)  # drop parenthetical acronyms/qualifiers
    return re.sub(r"[^a-z0-9]", "", stripped.lower())


class HeuristicDomainResolver:
    def __init__(self, prober: Prober, *, fallback_tlds: list[str] | None = None):
        self.prober = prober
        self.fallback_tlds = fallback_tlds or [".com", ".org", ".net"]

    def candidate_domains(self, target: TargetOrganization) -> list[tuple[str, str]]:
        """Returns (domain, origin) pairs, hints first (public knowledge of the
        org's brand), then name-derived guesses only if no hints exist.
        """
        candidates: list[tuple[str, str]] = [(d, "hint") for d in target.domain_hints]
        if not candidates:
            normalized = _normalize_name(target.name)
            tlds = ([".com.eg", ".gov.eg"] if target.country == "EG" else []) + self.fallback_tlds
            for tld in tlds:
                candidates.append((f"{normalized}{tld}", "heuristic"))

        seen: set[str] = set()
        unique = []
        for domain, origin in candidates:
            if domain not in seen:
                seen.add(domain)
                unique.append((domain, origin))
        return unique

    def resolve(self, target: TargetOrganization) -> ResolvedDomain | None:
        for domain, origin in self.candidate_domains(target):
            url = f"https://{domain}"
            result = self.prober(url)
            if result.reachable:
                return ResolvedDomain(domain=domain, homepage_url=url, probe=result, origin=origin)
        return None
