# Collector Template Taxonomy

This document answers a scalability question, not a data-availability one:
`docs/DATA_ACQUISITION.md`/`docs/ACQUISITION_STRATEGY.md` already established
*that* free company-level financial data exists to be found; the Financial
Data Coverage investigation (see `CHANGELOG.md`'s "Settings dashboard audit"
entry) confirmed the real bottleneck is no longer "is there a free source" —
it is "one hand-written collector per company does not scale to 101
tickers." `telecom_egypt_financials.py`/`orascom_financials.py` prove the
pattern works; they do not prove it scales. This document asks: do EGX
company Investor Relations sites cluster into a small number of *reusable
structural templates*, so a handful of generic collectors can cover most of
the universe, the same way `RssNewsCollector` already serves eleven
different news outlets from one class?

**Scope discipline, per instruction:** this is taxonomy and a roadmap only.
No production collector is added here. Every family below is a *candidate*
sized from real, already-collected evidence — none of it re-verified by a
fresh live fetch this session (this environment's egress is restricted to
package registries, same constraint noted in TD-38/TD-39). Implementation
should start only after the highest-value family is spot-checked against a
handful of real page fetches (a maintainer/CI step, not a guess).

## Data basis

Source: `research/data/registry/company_financial_sources.json` on the
`discovery/latest` branch — 101 `CompanyFinancialSourceRecord`s, produced by
`scripts/build_financial_source_registry.py` running with **real network
egress on a GitHub Actions runner** (`discovery.yml`, most recently
2026-07-31), not a sandbox guess. Status distribution:

| Status | Count | Meaning |
|---|---|---|
| `homepage_unresolved` | 75 | No evidenced company homepage yet — a domain-resolution gap (TD-38), out of scope for template design until closed |
| `discovered` | 21 | Homepage fetched; ≥1 real financial/IR document link found |
| `blocked` | 5 | Homepage known but fetch/parse found nothing usable |
| `validated` | 0 | Nothing has been human-confirmed yet (see `company_financial_registry.py`'s deliberately-manual `VALIDATED` gate) |

Everything below is drawn from the 21 `discovered` + 5 `blocked` records —
the only 26 with real fetched evidence to classify. Two generic gaps in the
*discovery* pipeline itself (not the target companies) were found while
doing this and are called out separately in the Roadmap, because closing
either one will reclassify several companies below and should happen before
committing engineering time to any one template.

## Two prerequisite infrastructure gaps (found while building this taxonomy)

These aren't collectors and aren't specific to any company — fixing them
changes the denominator this taxonomy is built on, so they're listed first.

**Gap 1 — discovery only crawls one page deep.**
`discovery.company_financial_discovery.discover_company_financial_sources()`
fetches exactly one page (the homepage) and classifies the links found on
it (`discovery.engine.discover_financial_documents`). It never fetches the
`investor_relations_home` link it just found and classifies *its* links.
Real, direct evidence this matters: 8 of the 21 `discovered` companies
(ADIB, ARCC, BTFH, EMFD, JUFO, ORHD, ORWE, TMGH) currently show only an
`investor_relations_home` (± a `disclosure`/`press-releases` link) with no
`financial_statements`/`annual_report` entry at all — not because the data
isn't there, but because the crawl never went one click further. The other
9 (ABUK, AMOC, COMI, FWRY, GBCO, HRHO, RAYA, plus CCAP/ORAS via a different
route) *do* show a direct `financial_statements`/`annual_report` link only
because their homepage happened to link it directly. This is very likely
undercounting Family A (below) substantially.

**Gap 2 — the document classifier has zero Arabic keywords.**
`discovery.financial_document.classify_financial_document()`'s keyword list
is English-only (`"investor relations"`, `"financial statement"`, ...).
EAST (Eastern Company) only matched a `disclosure` link because its page
happened to expose an English URL slug (`/disclosures_ar/`) — its anchor
text (`الإفصاحات`) would never have matched. EGAL (Egypt Aluminum) is
recorded `blocked` with reason *"Homepage fetched successfully but no
financial-document links matched"* — a real candidate for the same failure
mode, not necessarily a company with no IR content at all. Given most EGX
company sites are Arabic-first or bilingual, this plausibly affects some
share of the 75 still-`homepage_unresolved` records too, once their
homepages resolve.

Both are one-time, generic fixes to shared discovery code — not templates,
not collectors — and both make every family below larger, so they belong
before Family A/B implementation, not after.

## Template families

### Family A — Standard `/investor-relations/` path convention (HTML crawl + classify)

**Members (14):** ABUK, ADIB, AMOC, ARCC, BTFH, COMI, EMFD, FWRY, GBCO,
HRHO, JUFO, ORHD, ORWE, TMGH (RAYA is a close structural cousin — see note).

**Signature:** the company's own main domain exposes a predictable
IR-section path (`/investor-relations/`, `/en/investor-relations`,
`/investor-home`, `/en/investor/...`), and — where the crawl reached deep
enough (Gap 1) — that section's own subpages follow the same predictable
slugs across companies: `.../financial-statements`, `.../annual-report(s)`,
`.../disclosures`, `.../press-releases`. This is exactly the shape
`discovery.financial_document.classify_financial_document()` already
recognizes; the gap is depth, not classification.

**Reusable template:** a generic two-level IR crawler, configured (not
coded) per company with only a homepage URL: fetch homepage → follow the
`investor_relations_home` link already recorded in the registry → fetch
*that* page → classify every link on it with the existing classifier →
hand off `financial_statements`/`annual_report` targets to whichever of
Family B (if the target is a PDF) or an HTML-table extractor (if the
content is rendered inline) applies. This is config-driven fan-out, not
1-collector-per-company code.

**Confidence:** structural pattern is real (13/21 real, fetched records
share it) but the actual page markup at the second level (HTML table vs.
PDF list vs. something else) is unconfirmed for most of these until Gap 1
is closed and the resulting pages are actually fetched — expect this family
to split into A-into-B and A-into-(new HTML table extractor) once that
evidence exists, not stay one monolithic template.

**RAYA note:** same slug convention (`/financial-statements/`,
`/annual-report/`, `/disclosures/`) but at domain root rather than nested
under `/investor-relations/` — likely the same underlying site-builder
convention without an IR parent page. Counted separately above but should
reuse the same crawler template with a configurable root path.

### Family B — PDF report repository

**Confirmed members (1):** CCAP (`Qalaa-Holdings-Annual-Report-2023...pdf`,
a corporate-presentation `.pdf`).

**Likely members pending Gap 1 (unconfirmed):** GBCO's `Annual-Reports`
page, and the `financial_statements`/`annual_report` pages for HRHO, AMOC,
COMI, FWRY, ABUK — Family A membership does not by itself say whether the
numbers live in an HTML table or a linked PDF; only a real fetch of each
page resolves this.

**Reusable template:** `collectors.pdf.PdfDocumentCollector` already
provides the fetch/archive/`extract_text()` machinery (shared by every PDF
source in this codebase, including the currently-unbuilt MoF/Suez Canal
PLANNED sources) — only `parse()` is company-specific today. The template
opportunity is a **generic label-driven figure extractor** over
`extract_text()`'s output (regex/keyword search for "Revenue", "Net Profit
for the Period", "Total Assets", etc., same fails-closed-on-no-explicit-
label discipline `telecom_egypt_financials.py` already applies to HTML) —
parameterized by currency/unit rather than reimplemented per company. Real,
named risk: some Egyptian corporate annual reports are scanned images
(OCR-only) — explicitly out of scope, same posture the existing collectors
already declare for Telecom Egypt.

**Confidence:** highest *strategic* value of any family (audited annual
report PDFs are close to a universal artifact for a listed company,
unlike any one HTML template), but lowest *current* evidence (only one real
member confirmed) — the top candidate for a small, real spot-check (fetch
3-5 real `financial_statements`/`annual_report` PDFs, confirm the label
extractor's assumptions) before committing to build it.

### Family C — IR "highlights" press release (already proven twice in production)

**Members (4):** ETEL and ORAS already run this pattern in production
(`TelecomEgyptFinancialHighlightsCollector`, `OrascomFinancialHighlightsCollector`
— an article/press-release whose text contains an explicit, labelled
revenue/EBITDA/net-profit figure). Two new real candidates show the
identical shape: CCAP (`/en/newsroom/Qalaa's-consolidated-revenues-...`)
and RAYA (`/raya-holding-reports-record-breaking-results-for-q3-and-9m-2025/`,
plus a second dated article).

**Reusable template:** this is presently *two* near-duplicate classes
differing only in currency/unit and regex label set. The real template
opportunity is **generalizing the existing pair into one parameterized
`IrHighlightsCollector(ticker, currency, feed_or_page_url)`** rather than
writing a third and fourth bespoke class for CCAP/RAYA — a refactor, not
just new coverage.

**Confidence:** highest of all four families — the pattern is not
hypothetical, it is live, tested, production code today for 2 companies
already. Lowest engineering risk of the four.

### Family D — Dedicated IR subdomain (possible shared third-party platform)

**Members (7 distinct companies, 8 records):** CCAP (`ir.qalaaholdings.com`),
GBCO (`ir.gb-corporation.com`), RMDA (`ramedapharma-ir.com`), VLMR/VLMRA
(`ir.valmore.com` — one domain, two share classes of the same company), and
three currently `blocked` with HTTP 403 on the exact same convention: EFID
(`ir.edita.com.eg`), EFIH (`investors.efinanceinvestment.com`), ISPH
(`ir.ibnsina-pharma.com`).

**Why this matters more than the other families:** a dedicated `ir.*`/
`investors.*` subdomain is a well-known signature of hosting the IR site on
a third-party investor-relations platform rather than the company's own
CMS. *If* two or more of these seven are hosted by the same vendor, one
parser could cover all of that vendor's tenants regardless of which company
they are — a fan-out ratio no other family here can match. This is
genuinely unconfirmed without fetching the pages (shared JS bundle names,
a "powered by" footer credit, identical DOM structure) — flagged as the
single highest-leverage thing to check first, not asserted.

**The three HTTP 403s as a group are also a real, separate signal:** 3 of
these 7 companies' dedicated IR subdomains reject `collectors.fetcher
.HttpFetcher`'s single, hardcoded `AGX-Research/1.0` user agent
(`fetcher.py`'s `_USER_AGENT`) identically. That is consistent with (a) a
shared vendor's WAF blocking this exact user agent/pattern across all its
tenants at once — in which case one fix could plausibly unblock all three
simultaneously — or (b) three independent, unrelated blocks. No alternate,
already-honest fetch path exists in this codebase today to test that
hypothesis (`collectors.browser.BrowserAutomationCollector` is a
deliberate, documented `NotImplementedError` stub, not a usable fallback —
see its own docstring); resolving this would need either a second declared
`HttpFetcher` identity or real browser automation, both real engineering
decisions outside this taxonomy's scope. Named here so the group pattern
isn't mistaken for three unrelated dead ends, not as a solved problem.

**Confidence:** highest *potential* leverage, lowest current certainty —
this is the family most worth a small number of real, careful fetches
before any implementation decision, precisely because a positive result
here changes the whole roadmap's shape.

### Not a template — genuinely one-off (for now)

EAST and EGAL currently show no reusable structural pattern (see Gap 2 —
both may simply be Arabic-classification failures, not real one-offs; this
should be re-evaluated after Gap 2 is fixed rather than answered now).

## Roadmap (ordered to maximize coverage per collector, not collector count)

1. **Close Gap 1 (crawl depth) and Gap 2 (Arabic keywords) in the shared
   discovery pipeline.** Zero new collectors; both fixes apply to every
   family and to the 75 still-`homepage_unresolved` companies once their
   own homepages resolve. Re-run `build_financial_source_registry.py` with
   real egress afterward — the family sizes above should be treated as a
   floor, not a ceiling, until this happens.
2. **Spot-check Family D's shared-vendor hypothesis** with a handful of
   real fetches (CCAP, GBCO, RMDA, one of the three 403s with a corrected
   fetch config). This is the one check most likely to change the whole
   plan's priority order, so it should happen before, not after, committing
   to Family A/B engineering.
3. **Generalize Family C** (ETEL/ORAS → one parameterized
   `IrHighlightsCollector`) and wire CCAP/RAYA through it. Lowest risk,
   already twice-proven, immediately actionable — the natural first real
   implementation once this taxonomy is reviewed.
4. **Build one generic Family B label-extractor** on top of the existing
   `PdfDocumentCollector` base, after confirming its assumptions against a
   handful of real annual-report PDFs (start with CCAP's, which is already
   a confirmed real link).
5. **Build the Family A two-level crawler** last, once Gap 1's re-run shows
   which of its 13 members actually resolve to an HTML table (needs its own
   extractor) vs. a PDF (folds into Family B's template) — building this
   before that split is known risks building the wrong extractor twice.
6. Only companies that survive all of the above as genuine one-offs should
   get a hand-written, ETEL/ORAS-style bespoke collector — the fallback,
   not the default.

## What this document is not

Not a promotion, not a collector, not a claim that any family is confirmed
beyond what's cited above. `SourceStatus` for every company here stays
whatever the registry already honestly records; nothing changes in
`sources/catalog.py` or `CAPABILITY_STRATEGIES` as a result of this
document. Implementation of any family above should follow the existing
`AD-16`/`Collector.__init__` discipline — a collector only becomes
`IMPLEMENTED` after being built and tested against real, fetched content,
never on structural-pattern evidence alone (the same lesson
`skynews_arabia_economy`'s catalog history already recorded once).
