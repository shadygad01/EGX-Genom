# Collector Template Taxonomy

**Status: REGENERATED against fixed discovery code (2026-08-03).** The
first version of this document was built from a discovery run with two
known, real limitations: crawl depth capped at the homepage (Gap 1) and an
English-only document classifier (Gap 2). Both are now fixed in code
(`discovery.company_financial_discovery`'s one-level IR traversal;
`discovery.financial_document`'s Arabic keyword vocabulary) and a fresh,
live `discovery.yml` run (GitHub Actions run `30790732373`, real network
egress, not a sandbox guess) regenerated
`research/data/registry/company_financial_sources.json` with them applied.
This version reflects that fresh data and is diffed against the prior one
throughout. See "What changed vs. the provisional version" below for the
full comparison before reading the families themselves.

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
sized from real, live-fetched evidence. Implementation should start only
after the highest-value family is spot-checked against a handful of real
document fetches (a maintainer/CI step, not a guess) — the family sizing
below is real, but "how to parse it" for a new family is not yet confirmed
just because a URL was discovered.

## Data basis

Source: `research/data/registry/company_financial_sources.json` on the
`discovery/latest` branch, commit `237129e` — 101 `CompanyFinancialSourceRecord`s,
produced by `scripts/build_financial_source_registry.py` running with real
network egress on a GitHub Actions runner (`discovery.yml`, run
`30790732373`, 2026-08-03), using the fixed one-level-traversal +
Arabic-vocabulary code. Status distribution (unchanged from the prior
version — the two fixes add *documents to already-`discovered`/`blocked`
companies*, they do not resolve new homepages, which is the separate TD-38
gap):

| Status | Count | Meaning |
|---|---|---|
| `homepage_unresolved` | 75 | No evidenced company homepage yet — a domain-resolution gap (TD-38), out of scope for template design until closed |
| `discovered` | 21 | Homepage fetched; ≥1 real financial/IR document link found |
| `blocked` | 5 | Homepage known but fetch/parse found nothing usable |
| `validated` | 0 | Nothing has been human-confirmed yet (see `company_financial_registry.py`'s deliberately-manual `VALIDATED` gate) |

**Documents discovered total: 174** (was 61 before the fix — a real 2.85x
increase, confirmed by the workflow run's own summary output, not
estimated).

## What changed vs. the provisional version

Per-company diff, old vs. new (only companies whose document set actually
changed are listed; the other 16 `discovered`/`blocked` companies are
byte-identical):

| Ticker | Docs before | Docs after | What grew |
|---|---|---|---|
| TMGH | 1 | 71 | Massive real PDF archive surfaced one level deep — 64 distinct PDF files across financial statements, quarterly earnings releases, presentations, and disclosures |
| EAST | 1 | 9 | Entirely from **Gap 2** (Arabic keywords) — its real Arabic-language financial-statements/quarterly-report/disclosure links were already there, just unrecognized before |
| JUFO | 2 | 9 | 6 new PDFs one level deep, including a run of quarterly "Earnings Release" PDFs |
| ORWE | 3 | 9 | 6 new PDFs one level deep (quarterly earnings release, consolidated financial statement, investor presentation) |
| RMDA | 1 | 9 | 6 new PDFs one level deep on its dedicated `ramedapharma-ir.com` subdomain |
| HRHO | 6 | 10 | Duplicate `/en/investor-relations/...` and `/investor-relations/...` (no `/en/`) link sets — same pages in two URL forms, not new content (see Family A note) |
| COMI | 5 | 9 | New `financial_statements`/`disclosure`/`annual_report`/`presentation` links one level deep, plus 2 fragment-only duplicates of already-seen IR-home links (`#tab-mega-...` variants) — a distinct, narrower dedup gap than HRHO's, see Family A note |
| FWRY | 4 | 5 | One additional disclosures sub-page found one level deep |
| GBCO | 2 | 3 | One additional presentation-filings page on its `ir.gb-corporation.com` subdomain |
| ORHD | 2 | 3 | One additional presentation PDF — notably hosted on third-party cloud object storage (`odh-space.fra1.digitaloceanspaces.com`), not ORHD's own domain, a real reminder that Family B's PDF collector must not assume the PDF lives on the company's own site |
| ADIB | 1 | 4 | 3 new documents one level deep, including a real annual-report PDF |

**EGAL was re-checked and is still genuinely blocked** with the identical
reason ("no financial-document links matched") even with Arabic keywords
now active — this is real evidence EGAL's homepage truly has no
IR-labelled link in either language, not a classifier gap. The hedge in
the provisional version ("should be re-evaluated after Gap 2 is fixed") is
now resolved: EGAL stays in the genuine-one-off bucket.

**ARCC and BTFH did not grow** despite having a real, navigable
`investor_relations_home` URL — the one-level follow-up fetch was
attempted (per the code) but evidently did not surface further
keyword-matched links this run (either the fetch failed, or that specific
sub-page genuinely has no deeper links the classifier recognizes). This is
the honest limit of a *one*-level traversal, exactly as scoped — going
further would be a second, separate decision, not a bug in this fix.

## Template families

### Family A — Standard `/investor-relations/` path convention (HTML crawl + classify)

**Members (14, unchanged):** ABUK, ADIB, AMOC, ARCC, BTFH, COMI, EMFD,
FWRY, GBCO, HRHO, JUFO, ORHD, ORWE, TMGH (RAYA is a close structural
cousin — see note in the prior version).

**Resolved split (this is the real news from the regenerated data):** Gap
1's fix now shows *which* of these 14 actually resolve to a PDF vs. an
HTML page one level deep:

- **Fold into Family B (PDF confirmed):** ADIB, JUFO, ORHD, ORWE, TMGH (5) —
  their `financial_statements`/`annual_report`/`quarterly_report` links are
  real `.pdf` files, not HTML tables.
- **Still HTML, needs its own extractor (9):** ABUK, AMOC, ARCC, BTFH,
  COMI, EMFD, FWRY, GBCO, HRHO — either the content renders directly on an
  HTML page, or (ARCC, BTFH) no deeper content was found this run at all.

**Reusable template (revised):** a generic two-level IR crawler, now
proven to actually surface real content (not hypothetical): fetch
homepage → follow `investor_relations_home` (already implemented in
`discover_company_financial_sources`) → classify links on that page. What
was unconfirmed before — HTML table vs. PDF list — is now split by real
evidence per company above; an HTML-table/text extractor is still needed
for the 9-company HTML branch, distinct from Family B's PDF extractor for
the 5-company PDF branch.

**Two distinct dedup caveats found in the fresh data, both real, both
different:**

- **HRHO** shows the same four categories (`presentation`, `disclosure`,
  `financial_statements`, `annual_report`) twice each — once under
  `/en/investor-relations/...` and once under `/investor-relations/...`
  without the `/en/` prefix. Same pages in two locale/URL forms, not eight
  distinct documents.
- **COMI** shows a narrower issue: two of its `investor_relations_home`
  entries are fragment-only variants of already-listed URLs
  (`https://www.cibeg.com#tab-mega-...` and
  `https://www.cibeg.com/en/investor-relations#tab-mega-...`, differing
  from the fragment-free URLs only by a `#tab-mega-...` anchor).
  `discovery.candidate.SourceCandidate.fingerprint()` normalizes trailing
  slash and case but does not strip URL fragments, so these count as
  distinct candidates today.

Neither is a taxonomy-level problem — both are real, specific dedup
refinements (locale-prefix normalization; fragment-stripping in
`fingerprint()`) to carry into Family A's eventual crawler implementation,
not evidence against the family's structural pattern itself.

### Family B — PDF report repository

**Confirmed members: 8** (was 1) — ADIB, CCAP, EAST, JUFO, ORHD, ORWE,
RMDA, TMGH all now show ≥1 real, live-discovered `.pdf` URL. This is the
single biggest change from closing Gap 1: the provisional taxonomy could
only confirm this family from CCAP; every other member was "likely,
pending crawl depth." They are no longer pending.

**New, more specific sub-pattern — Quarterly Earnings Release PDF:** JUFO,
RMDA, ORWE, and TMGH all publish a predictably-named PDF per quarter (e.g.
`ER-1Q26-ENG-1.pdf`, `Rameda-1Q26-Earnings-Release.pdf`,
`1Q-2026-Earnings-Release.pdf`, `TMG Holding 1Q26 ER - EN.pdf`) — same
document *type* and a consistent ticker/quarter/"ER"-or-"Earnings Release"
naming convention across four unrelated companies. This is a narrower,
higher-confidence starting target than "every PDF on the page": a single
extractor tuned for a quarterly earnings-release PDF's typical structure
(headline figures near the top, not a full audited statement's line-item
depth) is a smaller, more tractable first build than a fully general
annual-report parser, and already has 4 real, named files to test against
today (no further discovery needed to start).

**TMGH is a real outlier in scale, not just presence:** 64 of its 71
documents are distinct PDFs (financial statements, quarterly reports,
presentations, and disclosures going back several years) — a genuine,
large PDF archive, not a fluke. Worth using as the primary structural test
case once a PDF extractor is built, precisely because its volume will
surface edge cases (different report years' formatting, EN vs. AR
filenames) a single-document spot-check would miss.

**Reusable template (unchanged in design, now much better evidenced):**
`collectors.pdf.PdfDocumentCollector` already provides the
fetch/archive/`extract_text()` machinery — only `parse()` is
company-specific today. The template opportunity is a **generic
label-driven figure extractor** over `extract_text()`'s output
(regex/keyword search for "Revenue", "Net Profit for the Period", "Total
Assets", etc., same fails-closed-on-no-explicit-label discipline
`telecom_egypt_financials.py` already applies to HTML), parameterized by
currency/unit rather than reimplemented per company. Real, named risk
unchanged: some Egyptian corporate annual reports may be scanned images
(OCR-only) — explicitly out of scope, same posture the existing
collectors already declare for Telecom Egypt; this has not yet been
checked against any of the 8 real PDFs above (`extract_text()`'s real
output on a real file is the next honest check, not assumed either way).

**Confidence: upgraded from "highest strategic value, lowest current
evidence" to highest on both axes.** 8 real member companies with real,
named PDF URLs ready to fetch and inspect — no further discovery needed to
begin a real spot-check.

### Family C — IR "highlights" press release (already proven twice in production)

**Members (4, unchanged):** ETEL and ORAS already run this pattern in
production (`TelecomEgyptFinancialHighlightsCollector`,
`OrascomFinancialHighlightsCollector` — an HTML article/press-release
whose *body text* contains an explicit, labelled revenue/EBITDA/net-profit
figure). CCAP and RAYA show the identical HTML-article shape.

**Distinguish from Family B's new "Quarterly Earnings Release PDF"
sub-pattern above — same business intent, different document shape:**
Family C is an HTML news/press-release *page* whose prose contains a
labelled figure sentence; the new PDF sub-pattern (JUFO/RMDA/ORWE/TMGH) is
a downloadable *file* with the same intent. They need different
extractors (HTML text-node parsing vs. PDF `extract_text()`), so they stay
separate families despite the similar naming ("earnings release") —
folding them together would blur two genuinely different parsing problems
into one template that fits neither well.

**Reusable template (unchanged):** generalize the existing ETEL/ORAS pair
into one parameterized `IrHighlightsCollector(ticker, currency,
feed_or_page_url)` and wire CCAP/RAYA through it — a refactor, not new
parsing logic.

**Confidence: unchanged, still highest of all families** — live,
tested, production code today for 2 companies; lowest engineering risk.

### Family D — Dedicated IR subdomain (possible shared third-party platform)

**Members (7 distinct companies, 8 records, unchanged in membership):**
CCAP (`ir.qalaaholdings.com`), GBCO (`ir.gb-corporation.com`), RMDA
(`ramedapharma-ir.com`), VLMR/VLMRA (`ir.valmore.com`), and three still
`blocked` with HTTP 403 on the same convention: EFID (`ir.edita.com.eg`),
EFIH (`investors.efinanceinvestment.com`), ISPH (`ir.ibnsina-pharma.com`).

**New evidence strengthening the shared-vendor hypothesis:** GBCO's
`ir.gb-corporation.com` now shows a second real page —
`ir.gb-corporation.com/en/filings?type=investor-presentation` — a
`/filings?type=X` query-parameter convention. That specific shape (a
generic "filings" endpoint filtered by a `type` parameter) reads more like
a templated third-party IR-portal product's own URL convention than a
bespoke one-off page a company's web team would independently invent —
still not confirmed without fetching and comparing DOM/JS-bundle evidence
across two or more of these subdomains, but a stronger real signal than
the provisional version had.

**The three HTTP 403s remain unresolved the same way** (`collectors.fetcher
.HttpFetcher`'s single hardcoded user agent rejected by all three
identically) — no new evidence either way this run, since none of the
three flipped from `blocked`.

**Confidence: still highest potential leverage, still not yet confirmed**
— now slightly better evidenced (the `/filings?type=` convention) but
still the family most needing a real, careful fetch-and-compare before any
implementation decision.

### Not a template — genuinely one-off

**EGAL** is now confirmed (not just suspected) to have no reusable
pattern: re-checked with Arabic keywords active and still found nothing.
A real manual IR-page review is the honest next step for this one
company, not a template.

## Roadmap (revised, ordered to maximize coverage per collector, not collector count)

1. ~~Close Gap 1 (crawl depth) and Gap 2 (Arabic keywords)~~ — **done**,
   regenerated data confirms the fix (documents discovered 61→174; EAST's
   real Arabic content surfaced; the Family A PDF/HTML split resolved).
2. **Build the Family B generic PDF label-extractor first** (promoted
   above Family D in this revision — the new evidence is the reason): 8
   real member companies now confirmed, with the 4-company Quarterly
   Earnings Release PDF sub-pattern (JUFO/RMDA/ORWE/TMGH) as the narrowest,
   most tractable starting target — all 4 real files are already named and
   linked above, no further discovery needed to begin. TMGH's 64-PDF
   archive is the natural stress-test once the extractor's basic
   assumptions hold.
3. **Generalize Family C** (ETEL/ORAS → one parameterized
   `IrHighlightsCollector`) and wire CCAP/RAYA through it. Still lowest
   engineering risk of any family; independent of Family B's work, so it
   can proceed in parallel.
4. **Spot-check Family D's shared-vendor hypothesis** (CCAP, GBCO, RMDA,
   one of the three 403s with a corrected fetch config) — still valuable,
   now with the `/filings?type=` signal to specifically look for across
   subdomains, but ranked after B/C since those two are already
   evidence-ready to start.
5. **Build the Family A HTML-table/text extractor** for the 9 companies
   that resolved to HTML rather than PDF (ABUK, AMOC, ARCC, BTFH, COMI,
   EMFD, FWRY, GBCO, HRHO) — including the locale-duplicate-URL dedup this
   version's diff surfaced for HRHO/COMI.
6. Only companies that survive all of the above as genuine one-offs (EGAL
   today; possibly others once the 75 `homepage_unresolved` companies
   resolve) should get a hand-written, ETEL/ORAS-style bespoke collector —
   the fallback, not the default.

## What this document is not

Not a promotion, not a collector, not a claim that any family's *parsing*
is confirmed beyond what's cited above — a real PDF/HTML URL being
discovered is not the same as its content shape being inspected and
parsed. `SourceStatus` for every company here stays whatever the registry
already honestly records; nothing changes in `sources/catalog.py` or
`CAPABILITY_STRATEGIES` as a result of this document. Implementation of
any family above should follow the existing `AD-16`/`Collector.__init__`
discipline — a collector only becomes `IMPLEMENTED` after being built and
tested against real, fetched content, never on structural-pattern evidence
alone (the same lesson `skynews_arabia_economy`'s catalog history already
recorded once).
