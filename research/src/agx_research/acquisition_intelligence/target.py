"""TargetOrganization: what the Acquisition Intelligence Engine is told
about an organization it should find a legal acquisition method for.

Deliberately *not* a URL. A `TargetOrganization` carries identity —
name, category, country, and (optionally) `domain_hints`: publicly-known
brand-to-domain associations (e.g. "most people know Reuters' site is
reuters.com") the same way a human researcher would start from public
knowledge of who an organization is, not from someone handing over the
exact acquisition endpoint. `domain_hints` are never trusted directly:
`domain_resolution.HeuristicDomainResolver` still independently probes
every hint (and every name-derived guess) for reachability before treating
it as a real domain, and everything downstream of that (which RSS feed,
which API, which PDF repository) is discovered by `discovery.DiscoveryEngine`
against the verified homepage, not asserted here.

Where a target already has a `SourceSpec` entry in the seed catalog
(`sources.catalog`), `existing_source_id` links them so the engine updates
that source rather than minting a duplicate.

`priority` mirrors the business-value ordering the project owner names
explicitly (EGX official first, then EGX30/EGX70 Investor Relations, then
the named regulators/aggregators, then everything else the engine finds on
its own) -- lower runs first. It governs processing order
(`AcquisitionIntelligenceEngine.run_catalog`), not trust: legality/
stability/historical-availability verification is identical regardless of
priority.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agx_research.sources.spec import SourceCategory

# Business-value processing order, per the project owner's explicit priority
# list. "Additional free public source discovered by the engine" (anything
# not named) defaults to the catch-all tier below the named sources.
PRIORITY_EGX_OFFICIAL = 1
PRIORITY_EGX30_IR = 2
PRIORITY_EGX70_IR = 3
PRIORITY_CBE = 4
PRIORITY_FRA = 5
PRIORITY_CAPMAS = 6
PRIORITY_ENTERPRISE = 7
PRIORITY_MUBASHER = 8
PRIORITY_ZAWYA = 9
PRIORITY_REUTERS = 10
PRIORITY_TRADING_ECONOMICS = 11
PRIORITY_ADDITIONAL_DISCOVERED = 12


class TargetOrganization(BaseModel):
    id: str
    name: str
    category: SourceCategory
    country: str = "EG"
    domain_hints: list[str] = Field(default_factory=list)
    per_constituent: bool = False  # True: one target per universe member, not one org
    existing_source_id: str | None = None
    priority: int = PRIORITY_ADDITIONAL_DISCOVERED
    company_ticker: str | None = None  # set on per-company IR targets; links back to the universe
    notes: str = ""


def seed_target_organizations() -> list[TargetOrganization]:
    return [
        TargetOrganization(
            id="egx_official", name="Egyptian Exchange (EGX)",
            category=SourceCategory.OFFICIAL, country="EG",
            domain_hints=["egx.com.eg", "www.egx.com.eg"],
            existing_source_id="egx_official", priority=PRIORITY_EGX_OFFICIAL,
            notes="Priority 1. Once reachable, also the intended source of the real EGX30/EGX70 "
            "constituent lists and each company's own homepage link (see "
            "discovery.discover_company_directory_links) -- not just an acquisition method itself.",
        ),
        TargetOrganization(
            id="company_ir", name="Company Investor Relations (per-constituent)",
            category=SourceCategory.COMPANY, country="EG",
            per_constituent=True, existing_source_id="company_ir", priority=PRIORITY_EGX30_IR,
            notes="Marker entry, not run directly. Real per-company targets come from "
            "target.generate_company_ir_targets(universe) -- one target per EGX30/EGX70 "
            "constituent, domain hints come from each company's own public disclosure or a "
            "company-directory hint discovered from an already-resolved exchange homepage, "
            "never guessed centrally.",
        ),
        TargetOrganization(
            id="cbe", name="Central Bank of Egypt", category=SourceCategory.OFFICIAL, country="EG",
            domain_hints=["cbe.org.eg", "www.cbe.org.eg"], existing_source_id="cbe",
            priority=PRIORITY_CBE,
        ),
        TargetOrganization(
            id="fra_egypt", name="Financial Regulatory Authority (FRA)",
            category=SourceCategory.OFFICIAL, country="EG",
            domain_hints=["fra.gov.eg", "www.fra.gov.eg"], existing_source_id="fra_egypt",
            priority=PRIORITY_FRA,
        ),
        TargetOrganization(
            id="capmas", name="CAPMAS", category=SourceCategory.OFFICIAL, country="EG",
            domain_hints=["capmas.gov.eg", "www.capmas.gov.eg"], existing_source_id="capmas",
            priority=PRIORITY_CAPMAS,
        ),
        TargetOrganization(
            id="enterprise_press", name="Enterprise", category=SourceCategory.NEWS, country="EG",
            domain_hints=["enterprise.press", "www.enterprise.press"],
            existing_source_id="enterprise_press", priority=PRIORITY_ENTERPRISE,
        ),
        TargetOrganization(
            id="mubasher", name="Mubasher", category=SourceCategory.NEWS, country="EG",
            domain_hints=["mubasher.info", "www.mubasher.info"], existing_source_id="mubasher",
            priority=PRIORITY_MUBASHER,
        ),
        TargetOrganization(
            id="zawya", name="Zawya", category=SourceCategory.NEWS, country="AE",
            domain_hints=["zawya.com", "www.zawya.com"], existing_source_id="zawya",
            priority=PRIORITY_ZAWYA,
        ),
        TargetOrganization(
            id="reuters", name="Reuters", category=SourceCategory.NEWS, country="GB",
            domain_hints=["reuters.com", "www.reuters.com"], existing_source_id="reuters",
            priority=PRIORITY_REUTERS,
        ),
        TargetOrganization(
            id="trading_economics", name="Trading Economics",
            category=SourceCategory.MACROECONOMIC, country="US",
            domain_hints=["tradingeconomics.com", "www.tradingeconomics.com"],
            existing_source_id="trading_economics", priority=PRIORITY_TRADING_ECONOMICS,
        ),
        TargetOrganization(
            id="asharq_business", name="Asharq Business", category=SourceCategory.NEWS, country="SA",
            domain_hints=["asharqbusiness.com", "www.asharqbusiness.com"],
            existing_source_id="asharq_business", priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="cnbc_arabia", name="CNBC Arabia", category=SourceCategory.ARABIC_NEWS, country="AE",
            domain_hints=["cnbcarabia.com", "www.cnbcarabia.com"],
            existing_source_id="cnbc_arabia", priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
    ]


def generate_company_ir_targets(
    companies: dict[str, str], *, priority: int = PRIORITY_EGX30_IR
) -> list[TargetOrganization]:
    """One `TargetOrganization` per company in `companies` (ticker -> display
    name) -- the real expansion of the `company_ir` marker entry above.

    Deliberately no `domain_hints`: unlike the brand-name organizations in
    `seed_target_organizations` (Reuters, CBE, ...), an individual listed
    company's domain is not something this codebase has verified or
    universally-known public knowledge of, and guessing ~10-100 corporate
    domains from training-data recall would be exactly the kind of
    fabrication the program's rules forbid. Two honest paths supply a real
    hint instead: the company's own public disclosure (a business input),
    or `discovery.discover_company_directory_links` finding the company's
    own homepage link on an already-resolved directory page (e.g. EGX's) --
    see `AcquisitionIntelligenceEngine.run_catalog`.

    `companies` is caller-supplied (e.g. `StaticUniverseProvider().
    constituents(...)`) rather than hardcoded here, so this scales
    automatically the moment a real, complete EGX30/EGX70 constituent list
    replaces today's placeholder -- no change to this function needed.
    """
    return [
        TargetOrganization(
            id=f"company_ir_{ticker.lower()}",
            name=f"{name} Investor Relations",
            category=SourceCategory.COMPANY,
            country="EG",
            priority=priority,
            company_ticker=ticker,
            notes=f"Investor Relations for {name} ({ticker}). No domain hint supplied by "
            "design -- see generate_company_ir_targets's docstring.",
        )
        for ticker, name in sorted(companies.items())
    ]
