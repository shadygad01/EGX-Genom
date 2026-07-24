"""AcquisitionIntelligenceEngine: the orchestrator.

For a `TargetOrganization`, end to end:

    resolve a reachable domain (never a supplied URL)
        -> discover acquisition-method candidates on its homepage
            -> assess legality (gate), stability, historical availability
                -> rank the candidates that clear the legality gate
                    -> select the best
                        -> auto-generate a SourceSpec (PLANNED, never
                           IMPLEMENTED -- see config_generation.py)
                            -> register it in the SourceRegistry
                                -> record an initial reachability run and
                                   begin the qualification pipeline

Every network-touching step is an injected callable (`prober`, `fetch_text`,
`robots_checker`, and an optional `WaybackAvailabilityClient`), so this
class has no import of `urllib`/`http` at all and is fully testable with
fakes. A live deployment backs these with `collectors.fetcher.HttpFetcher`
and a real `WaybackAvailabilityClient`.

Nothing here ever asserts a source is collectable: `run_for_target` can
only ever produce a `PLANNED` `SourceSpec` at `LifecycleState.CANDIDATE`,
however well the discovered method scores -- becoming `IMPLEMENTED` still
requires an engineer to write and test the concrete collector, exactly as
every other source in this platform.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlsplit

from agx_research.acquisition_intelligence.config_generation import generate_source_spec
from agx_research.acquisition_intelligence.domain_resolution import (
    HeuristicDomainResolver,
    Prober,
    ResolvedDomain,
)
from agx_research.acquisition_intelligence.historical import (
    HistoricalAvailabilityAssessment,
    WaybackAvailabilityClient,
    assess_historical_availability,
    parse_cdx_timestamps,
    parse_closest_snapshot,
)
from agx_research.acquisition_intelligence.legality import assess_legality
from agx_research.acquisition_intelligence.ranking import RankedMethod, rank_methods, select_best
from agx_research.acquisition_intelligence.stability import assess_stability
from agx_research.acquisition_intelligence.target import TargetOrganization
from agx_research.discovery.candidate import SourceCandidate
from agx_research.discovery.engine import (
    DiscoveryEngine,
    discover_company_directory_links,
    discover_sitemap_urls,
    is_sitemap_index,
)
from agx_research.sources.qualification import apply_promotion, evaluate_promotion
from agx_research.sources.registry import SourceRegistry
from agx_research.sources.reputation import SourceMetricsRepository
from agx_research.sources.spec import SourceSpec

RobotsChecker = Callable[[str], bool | None]
FetchText = Callable[[str], str | None]

# The sitemaps.org protocol's own declared-location convention: robots.txt
# MAY name its sitemap(s) via a `Sitemap:` directive. Reading that directive
# (and, failing that, trying the conventional `/sitemap.xml` root path) is
# not a guess about any specific site -- it is the published, standardized
# way a site is supposed to advertise its sitemap.
_ROBOTS_SITEMAP_DIRECTIVE = re.compile(r"(?im)^\s*Sitemap:\s*(\S+)\s*$")


def _sitemap_fallback_candidates(
    fetch_text: FetchText, discovery_engine: DiscoveryEngine, homepage_url: str
) -> list[SourceCandidate]:
    """Standards-based fallback for when a homepage's own markup carries no
    discoverable feed/API/dataset link at all (`scan_page` returns nothing --
    e.g. a news site whose homepage is plain HTML with no RSS autodiscovery
    tag). Tries robots.txt's declared `Sitemap:` directive first, then the
    conventional `/sitemap.xml` root path; both are real, verifying fetches
    through the same injected `fetch_text` already used everywhere else in
    this engine (which enforces robots.txt via the caller's `HttpFetcher`) --
    never a fabricated or hardcoded feed URL. A sitemap-index is followed one
    level (per docs/TECHNICAL_DEBT.md TD-18), since many sites publish an
    index of per-section sitemaps rather than one flat file.
    """
    parsed = urlsplit(homepage_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    sitemap_urls: list[str] = []
    robots_text = fetch_text(f"{root}/robots.txt")
    if robots_text:
        for match in _ROBOTS_SITEMAP_DIRECTIVE.findall(robots_text):
            if match not in sitemap_urls:
                sitemap_urls.append(match)
    default_sitemap = f"{root}/sitemap.xml"
    if default_sitemap not in sitemap_urls:
        sitemap_urls.append(default_sitemap)

    for sitemap_url in sitemap_urls:
        sitemap_text = fetch_text(sitemap_url)
        if not sitemap_text:
            continue
        if is_sitemap_index(sitemap_text):
            candidates: list[SourceCandidate] = []
            seen: set[str] = set()
            for entry in discover_sitemap_urls(sitemap_text, sitemap_url):
                nested_text = fetch_text(entry.discovered_url)
                if not nested_text:
                    continue
                for candidate in discovery_engine.scan_sitemap(nested_text, entry.discovered_url):
                    if candidate.fingerprint() not in seen:
                        seen.add(candidate.fingerprint())
                        candidates.append(candidate)
            if candidates:
                return candidates
            continue
        candidates = discovery_engine.scan_sitemap(sitemap_text, sitemap_url)
        if candidates:
            return candidates
    return []


@dataclass
class AcquisitionResult:
    target_id: str
    resolved_domain: ResolvedDomain | None
    ranked_methods: list[RankedMethod] = field(default_factory=list)
    selected: RankedMethod | None = None
    generated_spec: SourceSpec | None = None
    registered: bool = False
    reason: str = ""


class AcquisitionIntelligenceEngine:
    def __init__(
        self,
        *,
        prober: Prober,
        fetch_text: FetchText,
        robots_checker: RobotsChecker,
        registry: SourceRegistry,
        metrics: SourceMetricsRepository | None = None,
        wayback: WaybackAvailabilityClient | None = None,
        domain_resolver: HeuristicDomainResolver | None = None,
        discovery_engine: DiscoveryEngine | None = None,
    ):
        self.prober = prober
        self.fetch_text = fetch_text
        self.robots_checker = robots_checker
        self.registry = registry
        self.metrics = metrics or SourceMetricsRepository()
        self.wayback = wayback
        self.domain_resolver = domain_resolver or HeuristicDomainResolver(prober)
        self.discovery_engine = discovery_engine or DiscoveryEngine()

    def run_for_target(
        self, target: TargetOrganization, *, exclude_urls: set[str] | None = None
    ) -> AcquisitionResult:
        exclude_urls = exclude_urls or set()

        resolved = self.domain_resolver.resolve(target)
        if resolved is None:
            return AcquisitionResult(
                target_id=target.id, resolved_domain=None,
                reason="No reachable domain found from public brand hints or name-derived guesses.",
            )

        page_text = self.fetch_text(resolved.homepage_url)
        if not page_text:
            return AcquisitionResult(
                target_id=target.id, resolved_domain=resolved,
                reason="Homepage reachable but its content could not be fetched for discovery.",
            )

        candidates = [
            c for c in self.discovery_engine.scan_page(page_text, resolved.homepage_url)
            if c.discovered_url not in exclude_urls
        ]
        if not candidates:
            # The homepage's own markup had nothing discoverable -- fall back
            # to the standards-based sitemap protocol before giving up (see
            # `_sitemap_fallback_candidates`; closes docs/TECHNICAL_DEBT.md
            # TD-18's "homepage = data source" gap).
            candidates = [
                c for c in _sitemap_fallback_candidates(
                    self.fetch_text, self.discovery_engine, resolved.homepage_url
                )
                if c.discovered_url not in exclude_urls
            ]
        if not candidates:
            return AcquisitionResult(
                target_id=target.id, resolved_domain=resolved,
                reason="No acquisition-method candidates discovered on the homepage or its sitemap.",
            )

        entries = []
        for candidate in candidates:
            robots_allows = self.robots_checker(candidate.discovered_url)
            legality = assess_legality(
                access_method=candidate.access_method_guess,
                robots_allows=robots_allows, page_text=page_text,
            )
            probe = self.prober(candidate.discovered_url)
            stability = assess_stability(candidate.discovered_url, [probe])
            historical = self._assess_historical(candidate.discovered_url)
            entries.append((candidate, legality, stability, historical))

        ranked = rank_methods(entries)
        selected = select_best(ranked)
        if selected is None:
            return AcquisitionResult(
                target_id=target.id, resolved_domain=resolved, ranked_methods=ranked,
                reason="No discovered candidate cleared the legality gate.",
            )

        spec = generate_source_spec(target, selected)
        existing = self.registry.latest(spec.id)
        if existing is not None:
            spec = spec.model_copy(update={"version": existing.version + 1})
        self.registry.add(spec)

        # "Begin qualification": a confirmed-reachable homepage is a real,
        # honest first data point -- record it and let the qualification
        # pipeline decide whether it justifies leaving Candidate.
        metrics = self.metrics.record_run(
            spec.id, succeeded=True, records_expected=0, records_produced=0,
        )
        decision = evaluate_promotion(spec, metrics)
        promoted = apply_promotion(self.registry, decision)
        final_spec = promoted or spec

        return AcquisitionResult(
            target_id=target.id, resolved_domain=resolved, ranked_methods=ranked,
            selected=selected, generated_spec=final_spec, registered=True,
            reason=f"Registered at lifecycle_state={final_spec.lifecycle_state.value}; "
            f"{decision.reason}",
        )

    def run_catalog(
        self, targets: list[TargetOrganization], *, companies: dict[str, str] | None = None
    ) -> list[AcquisitionResult]:
        """Run every target in business-value priority order (lowest
        `priority` first). If a target's homepage resolves and `companies`
        is supplied, scan that homepage for company-directory links
        (`discovery.discover_company_directory_links`) and feed any matches
        as `domain_hints` into not-yet-run targets for those same companies
        (matched by `company_ticker`) -- letting an exchange's or
        regulator's own listed-company directory supply real per-company
        Investor Relations hints instead of guessing them centrally. A
        target that already carries its own `domain_hints` is never
        overridden by a discovered one.

        This is what makes Priority 1 (the exchange) mechanically enable
        Priority 2/3 (company Investor Relations) rather than that
        dependency being documentation-only: whichever named/official
        target resolves first in priority order gets a real chance to
        supply hints before the per-company targets run.

        Only the discovered link's hostname is kept as a hint (not the full
        path) -- `domain_hints` is homepage-level by design everywhere else
        in this package. If a directory links to a company's own external
        site, this is a genuinely useful hint; if it links to an internal
        profile page on the directory's own domain, the hint is harmlessly
        redundant (resolves back to the directory itself, not a fabrication
        either way).
        """
        ordered = sorted(targets, key=lambda t: t.priority)
        hints_by_ticker: dict[str, str] = {}
        results: list[AcquisitionResult] = []

        for target in ordered:
            if (
                target.company_ticker
                and not target.domain_hints
                and target.company_ticker in hints_by_ticker
            ):
                target = target.model_copy(
                    update={"domain_hints": [hints_by_ticker[target.company_ticker]]}
                )

            result = self.run_for_target(target)
            results.append(result)

            if companies and result.resolved_domain is not None:
                page_text = self.fetch_text(result.resolved_domain.homepage_url)
                if page_text:
                    discovered = discover_company_directory_links(
                        page_text, result.resolved_domain.homepage_url, companies
                    )
                    for ticker, url in discovered.items():
                        hostname = urlsplit(url).netloc
                        if hostname:
                            hints_by_ticker.setdefault(ticker, hostname)

        return results

    def _assess_historical(self, url: str) -> HistoricalAvailabilityAssessment:
        if self.wayback is None:
            return HistoricalAvailabilityAssessment(
                score=0.0, has_any_snapshot=False,
                evidence="No Wayback Machine client configured for this run.",
            )
        closest = None
        timestamps: list = []
        try:
            availability_payload = self.wayback.check_availability(url)
            if isinstance(availability_payload, dict):
                closest = parse_closest_snapshot(availability_payload)
        except Exception:
            closest = None
        try:
            cdx_payload = self.wayback.cdx_snapshots(url)
            if isinstance(cdx_payload, list):
                timestamps = parse_cdx_timestamps(cdx_payload)
        except Exception:
            timestamps = []
        return assess_historical_availability(closest_snapshot=closest, cdx_timestamps=timestamps)
