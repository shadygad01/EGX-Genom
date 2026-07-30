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
# Co-equal with PRIORITY_EGX_OFFICIAL on purpose (not a new numeric tier):
# any third-party company-directory candidate needs to run in `run_catalog`
# before the per-company `company_ir_*` targets it might supply hints for
# (PRIORITY_EGX30_IR below), same as egx_official itself -- Python's stable
# sort keeps declaration order among equal priorities, so listing these
# right after egx_official in `seed_target_organizations` is sufficient.
PRIORITY_COMPANY_DIRECTORY = PRIORITY_EGX_OFFICIAL
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
            id="egx_official",
            name="Egyptian Exchange (EGX)",
            category=SourceCategory.OFFICIAL,
            country="EG",
            domain_hints=["egx.com.eg", "www.egx.com.eg"],
            existing_source_id="egx_official",
            priority=PRIORITY_EGX_OFFICIAL,
            notes="Priority 1. Once reachable, also the intended source of the real EGX30/EGX70 "
            "constituent lists and each company's own homepage link (see "
            "discovery.discover_company_directory_links) -- not just an acquisition method itself.",
        ),
        TargetOrganization(
            id="company_ir",
            name="Company Investor Relations (per-constituent)",
            category=SourceCategory.COMPANY,
            country="EG",
            per_constituent=True,
            existing_source_id="company_ir",
            priority=PRIORITY_EGX30_IR,
            notes="Marker entry, not run directly. Real per-company targets come from "
            "target.generate_company_ir_targets(universe) -- one target per EGX30/EGX70 "
            "constituent, domain hints come from each company's own public disclosure or a "
            "company-directory hint discovered from an already-resolved exchange homepage, "
            "never guessed centrally.",
        ),
        # Coverage-expansion mission: a free, independent third-party EGX
        # listed-companies directory (its own real URL found via public web
        # search, not asserted or guessed), added specifically as a second
        # candidate source of real company-directory links for the
        # `company_ir` chain -- alongside egx_official and
        # `discovery.wikidata_lookup`, never replacing either (AD-33).
        TargetOrganization(
            id="african_markets_egx",
            name="African Markets -- EGX Listed Companies",
            category=SourceCategory.MARKET_DATA,
            country="ZA",
            domain_hints=["african-markets.com", "www.african-markets.com"],
            existing_source_id="african_markets_egx",
            priority=PRIORITY_COMPANY_DIRECTORY,
            notes="Third-party directory of EGX-listed companies; candidate company-directory "
            "hint source for company_ir, independent of egx_official's own reachability.",
        ),
        TargetOrganization(
            id="cbe",
            name="Central Bank of Egypt",
            category=SourceCategory.OFFICIAL,
            country="EG",
            domain_hints=["cbe.org.eg", "www.cbe.org.eg"],
            existing_source_id="cbe",
            priority=PRIORITY_CBE,
        ),
        TargetOrganization(
            id="fra_egypt",
            name="Financial Regulatory Authority (FRA)",
            category=SourceCategory.OFFICIAL,
            country="EG",
            domain_hints=["fra.gov.eg", "www.fra.gov.eg"],
            existing_source_id="fra_egypt",
            priority=PRIORITY_FRA,
        ),
        TargetOrganization(
            id="capmas",
            name="CAPMAS",
            category=SourceCategory.OFFICIAL,
            country="EG",
            domain_hints=["capmas.gov.eg", "www.capmas.gov.eg"],
            existing_source_id="capmas",
            priority=PRIORITY_CAPMAS,
        ),
        TargetOrganization(
            id="enterprise_press",
            name="Enterprise",
            category=SourceCategory.NEWS,
            country="EG",
            domain_hints=["enterprise.press", "www.enterprise.press"],
            existing_source_id="enterprise_press",
            priority=PRIORITY_ENTERPRISE,
        ),
        TargetOrganization(
            id="mubasher",
            name="Mubasher",
            category=SourceCategory.NEWS,
            country="EG",
            domain_hints=["mubasher.info", "www.mubasher.info"],
            existing_source_id="mubasher",
            priority=PRIORITY_MUBASHER,
        ),
        TargetOrganization(
            id="zawya",
            name="Zawya",
            category=SourceCategory.NEWS,
            country="AE",
            domain_hints=["zawya.com", "www.zawya.com"],
            existing_source_id="zawya",
            priority=PRIORITY_ZAWYA,
        ),
        TargetOrganization(
            id="reuters",
            name="Reuters",
            category=SourceCategory.NEWS,
            country="GB",
            domain_hints=["reuters.com", "www.reuters.com"],
            existing_source_id="reuters",
            priority=PRIORITY_REUTERS,
        ),
        TargetOrganization(
            id="trading_economics",
            name="Trading Economics",
            category=SourceCategory.MACROECONOMIC,
            country="US",
            domain_hints=["tradingeconomics.com", "www.tradingeconomics.com"],
            existing_source_id="trading_economics",
            priority=PRIORITY_TRADING_ECONOMICS,
        ),
        TargetOrganization(
            id="asharq_business",
            name="Asharq Business",
            category=SourceCategory.NEWS,
            country="SA",
            domain_hints=["asharqbusiness.com", "www.asharqbusiness.com"],
            existing_source_id="asharq_business",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="cnbc_arabia",
            name="CNBC Arabia",
            category=SourceCategory.ARABIC_NEWS,
            country="AE",
            domain_hints=["cnbcarabia.com", "www.cnbcarabia.com"],
            existing_source_id="cnbc_arabia",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        # ---- Coverage-expansion mission: nine outlets already catalogued in
        # sources/catalog.py (status=PLANNED) but never given a
        # TargetOrganization entry, so the engine had never actually attempted
        # discovery against them -- a real, closeable gap distinct from a
        # target that was tried and failed. Domain hints below are each
        # outlet's own publicly-known brand domain (same category of public
        # knowledge as "reuters.com" above), independently re-verified for
        # reachability by HeuristicDomainResolver before anything is trusted;
        # nothing here is asserted as a working endpoint.
        TargetOrganization(
            id="alarabiya_business",
            name="Al Arabiya Business",
            category=SourceCategory.NEWS,
            country="AE",
            domain_hints=["alarabiya.net", "www.alarabiya.net"],
            existing_source_id="alarabiya_business",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="marketscreener",
            name="MarketScreener",
            category=SourceCategory.NEWS,
            country="FR",
            domain_hints=["marketscreener.com", "www.marketscreener.com"],
            existing_source_id="marketscreener",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="investing_news",
            name="Investing.com News",
            category=SourceCategory.NEWS,
            country="US",
            domain_hints=["investing.com", "www.investing.com"],
            existing_source_id="investing_news",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="almal",
            name="Al Mal",
            category=SourceCategory.ARABIC_NEWS,
            country="EG",
            domain_hints=["almalnews.com", "www.almalnews.com"],
            existing_source_id="almal",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="alborsa",
            name="Al Borsa News",
            category=SourceCategory.ARABIC_NEWS,
            country="EG",
            domain_hints=["alborsanews.com", "www.alborsanews.com"],
            existing_source_id="alborsa",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="masrawy_economy",
            name="Masrawy Economy",
            category=SourceCategory.ARABIC_NEWS,
            country="EG",
            domain_hints=["masrawy.com", "www.masrawy.com"],
            existing_source_id="masrawy_economy",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="youm7_economy",
            name="Youm7 Economy",
            category=SourceCategory.ARABIC_NEWS,
            country="EG",
            domain_hints=["youm7.com", "www.youm7.com"],
            existing_source_id="youm7_economy",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="skynews_arabia_economy",
            name="Sky News Arabia Economy",
            category=SourceCategory.ARABIC_NEWS,
            country="AE",
            domain_hints=["skynewsarabia.com", "www.skynewsarabia.com"],
            existing_source_id="skynews_arabia_economy",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="asharq_economy",
            name="Asharq Economy",
            category=SourceCategory.ARABIC_NEWS,
            country="SA",
            domain_hints=["asharq.com", "www.asharq.com"],
            existing_source_id="asharq_economy",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        # ---- Coverage-expansion mission: the first real, live `agx
        # discover-planned-report` run (2026-07-27, see
        # docs/DATA_ACQUISITION.md's "Discovery workflow" section) reported
        # 20 catalogued `PLANNED` sources as `not_targeted` -- correctly, since
        # the engine had nothing to resolve/probe for them. Of those, these 14
        # have a single, unambiguous, publicly-known organization domain (the
        # same category of public knowledge already used for every target
        # above -- Reuters is reuters.com, CBE is cbe.org.eg -- independently
        # re-verified for reachability by HeuristicDomainResolver before
        # anything is trusted, never asserted here). The remaining 6
        # (`github_releases`, `company_social_official`, `public_telegram`,
        # `patents`, `hiring_signals`, plus `company_ir`'s own per-constituent
        # marker) stay untargeted on purpose: each names more than one
        # candidate organization or is inherently per-company/per-channel
        # (which specific EPO vs. WIPO, which Telegram channel, which
        # company's own career page), and picking one for the catalog would be
        # exactly the kind of guess this program's own rules forbid.
        TargetOrganization(
            id="imf",
            name="International Monetary Fund",
            category=SourceCategory.MACROECONOMIC,
            country="US",
            domain_hints=["imf.org", "www.imf.org"],
            existing_source_id="imf",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="oecd",
            name="OECD",
            category=SourceCategory.MACROECONOMIC,
            country="FR",
            domain_hints=["oecd.org", "www.oecd.org"],
            existing_source_id="oecd",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="mof_egypt",
            name="Ministry of Finance (Egypt)",
            category=SourceCategory.OFFICIAL,
            country="EG",
            domain_hints=["mof.gov.eg", "www.mof.gov.eg"],
            existing_source_id="mof_egypt",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="egypt_open_data",
            name="Government Open Data (Egypt)",
            category=SourceCategory.OFFICIAL,
            country="EG",
            domain_hints=["data.gov.eg", "www.data.gov.eg"],
            existing_source_id="egypt_open_data",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="suez_canal_stats",
            name="Suez Canal Authority",
            category=SourceCategory.GLOBAL_MARKETS,
            country="EG",
            domain_hints=["suezcanal.gov.eg", "www.suezcanal.gov.eg"],
            existing_source_id="suez_canal_stats",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        # investing_com/tradingview/google_trends/wikipedia_pageviews
        # targets removed alongside their SourceSpec entries (Decision-
        # Centric Gap Audit / Architecture Adversarial Review): zero
        # capability mapping, zero agent consumer, no credible decision
        # path -- see sources/catalog.py's removal note.
        TargetOrganization(
            id="arxiv",
            name="arXiv",
            category=SourceCategory.RESEARCH,
            country="US",
            domain_hints=["arxiv.org", "www.arxiv.org"],
            existing_source_id="arxiv",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="ssrn",
            name="SSRN",
            category=SourceCategory.RESEARCH,
            country="US",
            domain_hints=["ssrn.com", "www.ssrn.com"],
            existing_source_id="ssrn",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="nber",
            name="National Bureau of Economic Research",
            category=SourceCategory.RESEARCH,
            country="US",
            domain_hints=["nber.org", "www.nber.org"],
            existing_source_id="nber",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        # google_scholar/researchgate targets removed alongside their
        # SourceSpec entries -- redundant with arxiv/ssrn/nber above.
        #
        # ---- Architecture Adversarial Review (2026-07-30): new Sovereign
        # & Credit Context targets feeding the merged Country & Macro Risk
        # severity classification's crisis rung (R3/R8). Public brand
        # domains only, independently re-verified for reachability like
        # every target above -- nothing here is asserted as a working feed.
        TargetOrganization(
            id="moodys_ratings",
            name="Moody's Ratings",
            category=SourceCategory.MACROECONOMIC,
            country="US",
            domain_hints=["moodys.com", "www.moodys.com"],
            existing_source_id="moodys_ratings",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="sp_global_ratings",
            name="S&P Global Ratings",
            category=SourceCategory.MACROECONOMIC,
            country="US",
            domain_hints=["spglobal.com", "www.spglobal.com"],
            existing_source_id="sp_global_ratings",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="fitch_ratings",
            name="Fitch Ratings",
            category=SourceCategory.MACROECONOMIC,
            country="US",
            domain_hints=["fitchratings.com", "www.fitchratings.com"],
            existing_source_id="fitch_ratings",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
        ),
        TargetOrganization(
            id="amwal_alghad",
            name="Amwal Al Ghad",
            category=SourceCategory.ARABIC_NEWS,
            country="EG",
            domain_hints=["amwalalghad.com", "www.amwalalghad.com"],
            existing_source_id="amwal_alghad",
            priority=PRIORITY_ADDITIONAL_DISCOVERED,
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

    `companies` is caller-supplied from `UniverseProvider.constituents(as_of)`
    rather than hardcoded here, so this scales automatically with a real,
    complete EGX30/EGX70 constituent list.
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
