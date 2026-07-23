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
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agx_research.sources.spec import SourceCategory


class TargetOrganization(BaseModel):
    id: str
    name: str
    category: SourceCategory
    country: str = "EG"
    domain_hints: list[str] = Field(default_factory=list)
    per_constituent: bool = False  # True: one target per universe member, not one org
    existing_source_id: str | None = None
    notes: str = ""


def seed_target_organizations() -> list[TargetOrganization]:
    return [
        TargetOrganization(
            id="egx_official", name="Egyptian Exchange (EGX)",
            category=SourceCategory.OFFICIAL, country="EG",
            domain_hints=["egx.com.eg", "www.egx.com.eg"],
            existing_source_id="egx_official",
        ),
        TargetOrganization(
            id="company_ir", name="Company Investor Relations (per-constituent)",
            category=SourceCategory.COMPANY, country="EG",
            per_constituent=True, existing_source_id="company_ir",
            notes="One target per EGX universe member's own IR domain, not a single org -- "
            "domain hints come from each company's own public disclosure, not guessed centrally.",
        ),
        TargetOrganization(
            id="reuters", name="Reuters", category=SourceCategory.NEWS, country="GB",
            domain_hints=["reuters.com", "www.reuters.com"], existing_source_id="reuters",
        ),
        TargetOrganization(
            id="mubasher", name="Mubasher", category=SourceCategory.NEWS, country="EG",
            domain_hints=["mubasher.info", "www.mubasher.info"], existing_source_id="mubasher",
        ),
        TargetOrganization(
            id="zawya", name="Zawya", category=SourceCategory.NEWS, country="AE",
            domain_hints=["zawya.com", "www.zawya.com"], existing_source_id="zawya",
        ),
        TargetOrganization(
            id="enterprise_press", name="Enterprise", category=SourceCategory.NEWS, country="EG",
            domain_hints=["enterprise.press", "www.enterprise.press"],
            existing_source_id="enterprise_press",
        ),
        TargetOrganization(
            id="asharq_business", name="Asharq Business", category=SourceCategory.NEWS, country="SA",
            domain_hints=["asharqbusiness.com", "www.asharqbusiness.com"],
            existing_source_id="asharq_business",
        ),
        TargetOrganization(
            id="cnbc_arabia", name="CNBC Arabia", category=SourceCategory.ARABIC_NEWS, country="AE",
            domain_hints=["cnbcarabia.com", "www.cnbcarabia.com"],
            existing_source_id="cnbc_arabia",
        ),
        TargetOrganization(
            id="cbe", name="Central Bank of Egypt", category=SourceCategory.OFFICIAL, country="EG",
            domain_hints=["cbe.org.eg", "www.cbe.org.eg"], existing_source_id="cbe",
        ),
        TargetOrganization(
            id="fra_egypt", name="Financial Regulatory Authority (FRA)",
            category=SourceCategory.OFFICIAL, country="EG",
            domain_hints=["fra.gov.eg", "www.fra.gov.eg"], existing_source_id="fra_egypt",
        ),
        TargetOrganization(
            id="capmas", name="CAPMAS", category=SourceCategory.OFFICIAL, country="EG",
            domain_hints=["capmas.gov.eg", "www.capmas.gov.eg"], existing_source_id="capmas",
        ),
        TargetOrganization(
            id="trading_economics", name="Trading Economics",
            category=SourceCategory.MACROECONOMIC, country="US",
            domain_hints=["tradingeconomics.com", "www.tradingeconomics.com"],
            existing_source_id="trading_economics",
        ),
    ]
