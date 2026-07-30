# The Free Decision Data Blueprint — EGX-Genom

**Status: pure research and architecture. No production code referenced,
audited, or changed. This document deliberately ignores
`sources/catalog.py`, `acquisition_intelligence/capability.py`, and every
other existing implementation artifact — it re-derives the answer from
first principles, then (only at the very end, in an appendix) notes where
it converges with or diverges from what already exists.**

## The one question this document answers

> What is the complete set of free, legal information required to produce
> the highest-quality long-term investment decision for an Egyptian
> stock?

Everything below is organized to answer exactly that, and nothing else.
Implementation effort, existing code, and engineering convenience are
deliberately absent from every ranking in this document.

---

## Part 0 — First principles: what does a long-term equity decision actually require?

Before surveying sources, decompose the decision itself. A long-term
investor choosing Buy / Hold / Increase / Reduce / Exit / No Action on an
Egyptian stock is really answering ten distinct epistemic questions.
Every source surveyed below is graded by which of these it answers — a
source that answers none of them has no place in the architecture,
regardless of how easy or interesting it is to collect.

| # | Question | Why it matters for EGX specifically |
|---|---|---|
| Q1 | Is the stock cheap or expensive relative to its own fundamentals? | Needs clean multi-period financial statements — the input free EGX data is weakest on. |
| Q2 | Is the underlying business growing, stable, or deteriorating? | Needs trend data across enough periods to distinguish a cycle from a decline. |
| Q3 | Is the balance sheet safe (leverage, liquidity, FX exposure)? | Egyptian corporates carry meaningful foreign-currency debt exposure; EGP devaluation risk makes this sharper than in most markets. |
| Q4 | Is there a near-term catalyst or event risk? | Disclosures, earnings, regulatory action, M&A. |
| Q5 | What is the macro/FX backdrop doing to earnings power and the multiple the market will pay? | Egypt's equity risk premium is dominated by currency and monetary-policy risk more than in most emerging markets. |
| Q6 | Does trading behavior (liquidity, momentum) confirm or contradict the fundamental thesis? | EGX has real liquidity concentration in a handful of names; a "good" thesis in an illiquid name is a different risk than in COMI. |
| Q7 | How does it compare to sector peers? | Relative positioning drives Hold vs. Reduce far more than an absolute number does. |
| Q8 | Is governance and ownership trustworthy (related-party risk, insider activity, free float)? | State ownership, family-controlled conglomerates, and related-party transactions are structurally more common on EGX than on developed exchanges. |
| Q9 | What is the sovereign/country-risk backdrop (credit, capital controls, political stability)? | A country-risk shock (a currency float, a credit downgrade, an IMF program breakdown) can dominate any single stock's idiosyncratic thesis. |
| Q10 | Is the underlying data itself trustworthy enough to act on? | Free EM data is genuinely less complete/timely than paid vendor data; a decision system must know its own blind spots. |

Every table below cites these by number in its "investment questions
answered" column.

---

## Part 1 — Survey of all legally accessible free information

Organized into 14 categories by **what kind of question it answers**, not
by organization or access method (source-type organization is exactly
what this redesign discards). "Free?" and "Legal?" are assessed against
public, no-registration, no-paid-tier access; "Legal?" flags where
automated collection specifically (vs. human browsing) needs its own
review, independent of the underlying data being public.

### 1. Universe, Identity & Market Structure

The prerequisite layer — nothing else attaches to a ticker without this.

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Egyptian Exchange (EGX) | Official listed-company directory, ISIN/ticker/sector mapping, EGX30/EGX70/EGX100 constituent lists | Yes | Yes (official public disclosure) | Structured download/HTML directory (method needs live verification) | Medium (anti-automation measures observed historically) | On rebalance (quarterly-ish) | Structured | High (authoritative) | Foundational — without it, no other layer can attach to a ticker | Primary | Q1–Q10 (all, as prerequisite) | Critical |
| EGX | Free-float percentage, foreign-ownership limits, shares outstanding | Yes | Yes | Same as above | Medium | On corporate action | Structured | High | Position sizing/liquidity risk context | Primary | Q6, Q8 | High |
| Financial Regulatory Authority (FRA) | Registered issuer list, licensing status of non-bank financial companies | Yes | Yes | PDF/HTML bulletins | Medium | Periodic | Semi-structured | High | Corroborates EGX's own listing status; catches suspensions/delistings | Primary | Q4, Q8, Q10 | Medium |
| Wikidata | Structured company facts (sector, founding date, legal form, official website) | Yes | Yes (open license, CC0) | JSON API | Low | Continuous (crowd-updated) | Structured | Medium (crowd-sourced, needs corroboration) | Sector/industry classification when official data is missing | Secondary | Q7 | Medium |
| GAFI (General Authority for Investment) | Corporate registration, FDI project data | Yes | Yes | HTML/PDF | High | Periodic | Unstructured | Medium | New entrant/competitor context for a sector | Secondary | Q7 | Low |

### 2. Price & Trading Data

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EGX (official) | Daily OHLCV per ticker, index levels | Yes | Yes | CSV/API (endpoint needs live verification; historically anti-bot protected) | High (historically blocked) | Daily (EOD) | Structured | Highest (authoritative) | Sole independent basis for entry/exit price levels and technical signals | Primary | Q1, Q5, Q6 | Critical |
| Yahoo Finance / StockAnalysis / other free aggregators | Daily OHLCV, cross-checked against EGX | Yes | ToS-restricted for automated use (varies by aggregator; verify per-provider) | JSON/HTML | Low–Medium | Daily | Structured | High (secondary confirmation) | Fallback/corroboration when the official feed is unreachable; two-source price agreement is itself a decision-safety signal (Q10) | Secondary | Q1, Q6, Q10 | Critical |
| Mubasher / regional market-data portals | Post-close price snapshots | Yes | Robots.txt/ToS varies, review per site | HTML | Medium–High | Daily | Semi-structured | Medium | Third corroborating leg for price agreement | Secondary | Q6, Q10 | Medium |
| EGX | Market breadth (advancers/decliners), traded value/volume market-wide | Yes | Yes | Same as OHLCV | Medium | Daily | Structured | High | Market-regime context for timing Hold vs. Reduce | Derived from Primary | Q5, Q6 | Medium |
| EGX | Circuit-breaker/trading-halt notices | Yes | Yes | HTML bulletin | Medium | Event-driven | Unstructured | High | Flags abnormal trading conditions that should suppress confidence | Primary | Q4, Q10 | Medium |

### 3. Corporate Fundamentals (Financial Statements)

The category Part 0 flags as the weakest link in free EM data — and,
per Q1–Q3, one of the most decision-critical.

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Company Investor Relations pages (per issuer) | Full annual/quarterly financial statements, MD&A, auditor's report | Yes | Yes (issuer's own public disclosure) | PDF (usually); occasionally HTML press release | High (101 different IR sites, no standard layout, PDF extraction risk) | Quarterly/annual | Mostly unstructured (PDF) | High content, low structure | The single highest-value, hardest-to-extract input for Q1–Q3 | Primary | Q1, Q2, Q3, Q7 | Critical |
| EGX / official issuer disclosure system | Mandatory periodic disclosures (financial results announcements) | Yes | Yes | PDF/structured feed (endpoint verification pending) | Medium–High | Quarterly | Semi-structured | High (regulator-mandated) | Same content as IR pages, but from the regulator (independent corroboration of what the company itself published) | Primary | Q1, Q2, Q3 | Critical |
| FRA | Non-bank financial-company regulatory filings (insurance, leasing, microfinance issuers) | Yes | Yes | PDF | High | Periodic | Unstructured | High | Sector-specific fundamentals for FRA-regulated issuers | Primary | Q1, Q2, Q3 | Medium |
| Central Bank of Egypt (CBE) | Bank soundness indicators, sector-aggregate banking statistics | Yes | Automated collection blocked historically (WAF); public data itself is free | PDF/HTML | High | Quarterly | Semi-structured | High | Sector-level context for bank stocks specifically (a large share of EGX30 by weight) | Primary | Q1, Q3, Q7 | High |
| No free source exists | Standardized machine-readable (XBRL) financial statements | — | — | — | — | — | — | — | **Missing capability** — see Part 3 | — | Q1, Q2, Q3 | Critical (gap) |

### 4. Corporate Actions & Disclosures

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EGX / issuer disclosure system | Dividends, splits, rights issues, capital changes | Yes | Yes | PDF/structured feed | Medium–High | Event-driven | Semi-structured | High | Corrects raw price series (without this, return calculations are simply wrong) | Primary | Q4 | Critical |
| Company IR / press releases | M&A, management changes, guidance updates | Yes | Yes | HTML/RSS/PDF | Medium | Event-driven | Unstructured | High | Direct catalyst identification | Primary | Q4 | High |
| Financial news outlets (Enterprise, FRA press releases, Al Borsa, Mubasher, Zawya, Reuters Africa) | Same events, independently reported | Yes | Varies by outlet (RSS/robots review per outlet) | RSS/HTML | Low–Medium | Continuous | Semi-structured | Medium (varies by outlet) | Cross-corroboration of official disclosures; often faster than the official filing | Primary/Secondary (per-outlet review) | Q4, Q10 | High |
| FRA | Regulatory circulars affecting listed non-bank issuers | Yes | Yes | PDF | Medium | Periodic | Unstructured | High | Regulatory-risk catalysts | Primary | Q4, Q9 | Medium |

### 5. Governance & Ownership

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EGX / issuer disclosure | Major shareholder / beneficial ownership disclosures (crossing ownership thresholds) | Yes | Yes | PDF/HTML | Medium–High | Event-driven | Unstructured | High | Direct evidence of insider conviction (accumulation/distribution) | Primary | Q8 | High |
| Company annual reports | Board composition, related-party transaction disclosure | Yes | Yes | PDF | High (buried in long-form reports) | Annual | Unstructured | High | Governance-risk assessment; related-party red flags | Primary | Q8 | High |
| EGX | Free float and state/strategic ownership percentage | Yes | Yes | Structured directory | Medium | On change | Structured | High | Distinguishes genuinely tradable float from nominal market cap | Primary | Q6, Q8 | High |
| No free, timely source exists | Real-time insider-transaction filings (equivalent to a Form-4 feed) | — | — | — | — | — | — | — | **Missing capability** — see Part 3 | — | Q8 | High (gap) |

### 6. Domestic Macroeconomic Data

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Central Bank of Egypt (CBE) | Policy rate, inflation, FX reserves, monetary aggregates, balance of payments | Yes | Automated collection historically WAF-blocked; data itself public | HTML/PDF bulletins | High | Monthly/quarterly | Semi-structured | Highest (authoritative) | The single most important macro input given Egypt's FX-dominated risk premium | Primary | Q5, Q9 | Critical |
| CAPMAS | CPI, population, labor statistics, national accounts | Yes | Yes (JSON API observed reachable) | JSON API | Low–Medium | Monthly/annual | Structured | High | Inflation context for real returns and consumer-sector demand | Primary | Q5 | High |
| Ministry of Finance (Egypt) | Budget documents, public debt statistics, T-bill/bond auction results | Yes | Yes | PDF | High | Periodic/per-auction | Unstructured | High | Fiscal-risk context; local-currency yield curve proxy | Primary | Q5, Q9 | Medium |
| Information & Decision Support Center (IDSC), Egyptian Cabinet | Macro/economic bulletins, government strategy reports | Yes | Yes | PDF/HTML | Medium | Periodic | Semi-structured | Medium–High | Independent corroboration of CBE/CAPMAS figures; policy-direction signal | Secondary | Q5, Q9 | Medium |
| World Bank Open Data | Egypt macro indicators (GDP, trade, reserves) — annual, lagged | Yes | Yes (CC-BY) | JSON API | Low | Annual | Structured | High | Long-run structural context, not near-term signal | Secondary | Q5 | Medium |
| IMF | Egypt macro indicators; Article IV consultation reports; Extended Fund Facility program review reports | Yes | API access historically WAF-blocked; published reports are free PDFs | PDF (reports); JSON API (blocked) | High | Per program review (roughly semi-annual) | Unstructured (reports) / Structured (API, if reachable) | Highest for program-review reports (independent, rigorous) | Program reviews are a uniquely high-value, under-used free source: they combine macro data, fiscal conditionality, and forward risk assessment in one document | Primary | Q5, Q9 | High |

### 7. External Sector — Egypt-Specific FX & Balance-of-Payments Drivers

This category doesn't appear as a distinct group in a typical developed-market
research platform, but Egypt's equity risk premium is dominated by FX and
external-balance risk more than fundamentals in many periods — these
inputs earn their own category on that basis alone.

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Suez Canal Authority | Monthly transit/receipt statistics | Yes | Yes | PDF/HTML | Medium | Monthly | Semi-structured | High | A major, distinct hard-currency inflow; a real leading indicator for FX/reserve pressure independent of CBE's own aggregate reporting | Primary | Q5, Q9 | High |
| Ministry of Tourism and Antiquities (Egypt) | Tourist arrivals, revenue estimates | Yes | Yes | PDF/HTML | Medium | Monthly/quarterly | Semi-structured | Medium–High | Second major hard-currency inflow; leading indicator for consumer/hospitality-sector names and FX supply | Primary | Q5, Q7, Q9 | High |
| CBE | Workers' remittances (balance of payments detail) | Yes | Same WAF caveat as CBE above | PDF/HTML | High | Quarterly | Semi-structured | High | Third major hard-currency inflow; remittance softness has historically preceded EGP pressure | Primary | Q5, Q9 | High |
| Ministry of Petroleum / EGPC (Egypt) | Oil & gas production volumes | Yes | Yes | PDF/HTML | Medium | Monthly/annual | Semi-structured | Medium | Egypt is both an importer and, since offshore gas discoveries, an exporter — net energy balance materially affects the FX picture and energy-sector names | Primary | Q5, Q7, Q9 | Medium |
| GAFI | Foreign direct investment inflow statistics | Yes | Yes | PDF/HTML | Medium | Quarterly | Semi-structured | Medium | Fourth hard-currency channel; corroborates or contradicts the CBE reserve picture | Secondary | Q5, Q9 | Medium |

### 8. Sovereign & Credit Context

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Moody's / S&P Global Ratings / Fitch Ratings | Free public press releases on Egypt's sovereign rating actions and outlook changes | Yes | Yes (press releases are public; full reports are paid) | RSS/HTML | Low–Medium | Event-driven (rare) | Unstructured | Highest (rating actions are discrete, unambiguous events) | A sovereign downgrade/upgrade is one of the highest-signal, lowest-frequency country-risk events available for free | Primary | Q9 | High |
| IMF | Program review outcomes/statements (distinct from the full Article IV report) | Yes | Yes | HTML/PDF press release | Low | Per review | Unstructured | High | Faster, shorter-form country-risk signal than the full report | Primary | Q9 | High |
| Ministry of Finance (Egypt) | Eurobond issuance terms/yields at issuance | Yes | Yes | PDF/press release | Medium | Per issuance (irregular) | Unstructured | Medium | A rare but very high-signal read on how international markets price Egypt risk | Secondary | Q9 | Medium |
| No free, timely source exists | Egypt sovereign/corporate CDS spreads | — | — | — | — | — | — | — | **Missing capability** — see Part 3 | — | Q9 | Medium (gap) |

### 9. Global Market & Commodity Context

Only the subset with a defensible causal channel into Egyptian equities —
this is deliberately not "every global index," which Part 3 flags as
unnecessary.

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FRED (St. Louis Fed) | US Treasury yields, US Dollar Index | Yes | Yes (attribution) | CSV | Low | Daily | Structured | High | US rates/DXY strength are a primary driver of EM capital-flow risk appetite, directly affecting EGP and EGX foreign flows | Secondary | Q5, Q9 | High |
| FRED / free commodity feeds | Brent/WTI crude oil price | Yes | Yes | CSV | Low | Daily | Structured | High | Egypt's net energy trade balance is sensitive to oil prices in both directions (import cost vs. gas export revenue) | Secondary | Q5, Q7, Q9 | High |
| FRED / free commodity feeds | Wheat price | Yes | Yes | CSV | Low | Daily | Structured | Medium–High | Egypt is one of the world's largest wheat importers — a direct fiscal-subsidy and inflation channel | Secondary | Q5, Q9 | Medium |
| Free index/ETF price feeds | MSCI Emerging Markets index level (via a free proxy, e.g. a tracking ETF's price) | Yes | Yes (proxy, not the licensed index itself) | CSV/JSON | Low | Daily | Structured | Medium (a proxy, not the licensed index) | EM-wide risk sentiment context for foreign-flow-driven moves unrelated to Egypt-specific news | Secondary | Q5, Q6 | Medium |

### 10. Sector/Industry Context & Peer Comparables

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EGX | Sector indices and sector-level constituent weights | Yes | Yes | Structured directory | Medium | On rebalance | Structured | High | Enables true relative-to-sector performance and multiple comparison, not just absolute metrics | Primary | Q7 | High |
| Peer companies' own IR/disclosure pages | Same fundamentals as §3, for every peer in a sector | Yes | Yes | PDF (same difficulty as §3, multiplied by peer count) | High | Quarterly/annual | Unstructured | High | Direct peer comparables — arguably as valuable as the target company's own fundamentals for a relative Hold/Reduce call | Primary | Q7 | High |
| S&P Global (or equivalent) | Egypt Purchasing Managers' Index (PMI) — free monthly press release | Yes | Yes | HTML/PDF press release | Low | Monthly | Unstructured (headline number, structured in principle) | High | A genuinely leading, high-frequency real-economy indicator — rare in this list | Primary | Q5, Q7 | High |
| CAPMAS | Sector-level production/output statistics | Yes | Yes | JSON API/PDF | Medium | Monthly/quarterly | Semi-structured | Medium–High | Sector-demand corroboration independent of any single company's own reporting | Secondary | Q7 | Medium |

### 11. News & Media (Financial Press)

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Enterprise (Egypt business news) | Daily EGX/macro-focused business news | Yes | RSS terms review needed | RSS | Low | Continuous | Semi-structured | Medium–High | High-quality, EGX-specific, English-language primary reporting | Primary | Q4, Q5, Q9 | High |
| FRA press feed | Regulatory announcements | Yes | Yes | RSS | Low | Continuous | Semi-structured | High | Authoritative regulatory-event source | Primary | Q4, Q9 | High |
| Al Borsa, Masrawy Economy, Al Mal, Youm7 Economy (Arabic financial press) | EGX/company/macro news in Arabic | Yes | Robots.txt/RSS review per outlet | RSS | Low–Medium | Continuous | Semi-structured | Medium | Broader Arabic-language coverage a purely English-language pipeline would miss entirely | Primary | Q4, Q9 | High |
| Amwal Al Ghad | Egypt-specific stock-market news (distinct from general Arabic business press) | Yes (candidate — unverified) | Needs review | RSS/HTML (unverified) | Unknown pending verification | Continuous | Semi-structured | Unknown pending verification | Same as above, narrower EGX focus | Primary (pending verification) | Q4, Q9 | Medium |
| GDELT | Global multilingual news index, Egypt/EGX-filtered query | Yes | Yes (official API) | JSON API | Low | Continuous | Structured (metadata only) | Low precision (broad recall, weak precision on a narrow EGX filter) | Discovery/corroboration only — should never independently trigger a decision, only confirm a primary-source report | Secondary (discovery-tier) | Q4 (corroboration only) | Medium |
| Zawya, Reuters Africa, Asharq Business, MarketScreener, CNBC Arabia | Regional business news covering EGX-listed names | Yes | RSS/ToS review per outlet | RSS | Low–Medium | Continuous | Semi-structured | Medium | Additional corroboration/coverage breadth | Primary/Secondary (per outlet) | Q4, Q9 | Medium |

### 12. Trading Calendar & Regulatory Circulars

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EGX | Official trading calendar, market holidays | Yes | Yes | HTML/PDF | Low–Medium | Annual (with occasional ad hoc changes) | Structured | High | Operational correctness — without it, "no data today" is misread as "market inactive" or vice versa | Primary | (operational prerequisite, not a thesis input) | Critical |
| EGX / FRA | Listing rules, disclosure-timing rules, circuit-breaker rules | Yes | Yes | PDF | Medium | Periodic | Unstructured | High | Context for interpreting *why* a disclosure or halt happened | Primary | Q4, Q10 | Low |

### 13. Alternative / Corroborating Data — evaluated and mostly rejected

Every candidate here was evaluated against Part 0's ten questions, not
assumed valuable because it's fashionable or technically obtainable.

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Google Trends | Search interest for a company/ticker name | Yes | No official API (ToS-ambiguous scraping) | Unofficial scraping only | High | Daily | Structured (once scraped) | Low (no established causal link to EGX price/fundamentals) | None demonstrated | — | None reliably | Low (see Part 3, not recommended) |
| Wikipedia page views | Traffic to a company's Wikipedia article | Yes | Yes (official API) | JSON API | Low | Daily | Structured | Low (weak, indirect attention proxy) | Marginal at best; redundant with news volume, which is already captured with higher precision | Secondary | Q4 (weakly) | Low |
| Social media (public posts, X/Telegram) | Retail sentiment | Partially (platform-dependent; most require a key or ToS-restrict automation) | Mostly requires a credential or violates ToS for bulk collection | API (key-gated) or scraping (ToS risk) | High | Continuous | Unstructured | Low (noisy, manipulable, thin EGX-specific volume) | Not demonstrated to outperform primary news for EGX-specific signal | Secondary | Q4 (weakly) | Low |
| Patent databases (EPO/WIPO) | Patent filings by listed companies | Yes | Yes | API | Medium | As filed | Structured | High reliability, near-zero relevance | EGX30/70 is bank/telecom/consumer/industrial-heavy, not IP-driven; near-zero filings expected from most constituents | — | Rarely, Q2 for a handful of industrial names | Low |
| Job-posting/hiring signals | Company hiring volume | Rarely free at scale | Varies | Scraping | High | Continuous | Unstructured | Low (no established Egypt-specific correlation, thin public job-board presence for most issuers) | Not demonstrated | — | Q2 (weakly, unproven) | Low |
| Satellite imagery (retail traffic, shipping counts) | Physical activity proxies | Rarely genuinely free at usable resolution | Varies | Third-party paid processing typically required | Very high | Periodic | Unstructured | Unproven at this market's scale and cost | Not free in practice for a research platform this scoped | — | Q2 (theoretically) | Low (see Part 3) |
| GitHub activity | Developer activity for a listed company | Yes | Yes (official API) | JSON API | Low | Continuous | Structured | Near-zero relevance | EGX30/70 has essentially no companies where public code activity is a business indicator | — | None | Low |

### 14. Research & Methodology Literature

A distinct track — these sources improve *how the platform itself*
reasons (statistical methodology, factor research), not any single
ticker's evidence. Important not to conflate with Parts 1–13.

| Organization | Dataset | Free? | Legal? | Collection method | Automation difficulty | Update frequency | Structure | Reliability | Decision contribution | Evidence type | Questions answered | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arXiv (q-fin) | New quantitative finance papers | Yes | Yes | RSS/API | Low | Continuous | Structured (metadata) | High | Improves methodology, not any single ticker's thesis | Neither (methodology, not evidence) | None directly | Medium (methodology only) |
| SSRN | Working papers, incl. EM/frontier-market finance research | Yes | Yes | RSS | Low | Continuous | Structured (metadata) | High | Same as above | Neither | None directly | Medium (methodology only) |
| NBER | Working papers | Yes | Yes | RSS | Low | Continuous | Structured (metadata) | High | Same as above | Neither | None directly | Low (methodology only) |

---

## Part 2 — What is actually missing (capability gaps, not to be invented)

Per the mission's rule 8, named explicitly rather than papered over with
a proxy:

1. **Standardized, machine-readable financial statements (XBRL or
   equivalent).** No free EGX-wide structured filing format was found.
   Every fundamental figure available for free arrives as PDF prose,
   meaning extraction quality (not availability) is the real constraint
   on Q1–Q3. This is the single largest capability gap in the entire
   blueprint.
2. **Real-time, granular insider-transaction disclosure.** Threshold-crossing
   ownership disclosures exist; a continuous, granular insider-trade feed
   (the EGX equivalent of a Form 4) was not identified as reliably
   available for free, structured, timely collection.
3. **Sell-side consensus estimates (forward EPS/revenue forecasts).**
   Structurally a paid-vendor product (Bloomberg/Refinitiv/Visible Alpha
   consensus panels); no free equivalent exists for EGX-listed names.
   Explicitly out of scope per the mission's non-negotiable rule 2 — name
   as a gap, do not attempt a workaround.
4. **Sovereign/corporate CDS spreads.** Real-time credit-spread data is a
   paid Bloomberg/Markit product; free proxies (rating actions, Eurobond
   issuance terms) exist but are lower-frequency and noisier.
5. **Intraday/tick-level order-book data.** EGX's free public data is
   end-of-day; no free Level 2 depth feed exists. This bounds the
   platform to end-of-day-resolution decisions by construction — correct
   for a long-term-investor mission, worth stating explicitly rather than
   silently assuming.
6. **A verified, complete EGX70 constituent list and a live-reachable
   `egx_official` endpoint.** Named here again deliberately: several
   downstream capabilities in Parts 1.1, 1.2, 1.4, and 1.12 all terminate
   at "endpoint needs live verification" for exactly this reason. This
   is not a new finding — it is the same evidenced blocker prior sessions
   named — but it belongs in a first-principles blueprint because so much
   of the *ideal* architecture's foundation layer depends on it.
7. **A free, reliable EGP parallel/forward-market rate.** Egypt's history
   of currency crises makes a forward-looking FX signal valuable; no free,
   reliable source for one was identified (official spot rate is
   available via CBE; forward pricing is not).

## Part 3 — What is unnecessary (explicitly, not by omission)

Per rule 9. Each of these was considered and rejected with a stated
reason, not simply left out:

- **Social media sentiment** (Telegram/X/Facebook) — thin EGX-specific
  volume, high noise, no demonstrated causal channel distinct from news
  coverage the platform already captures with better precision.
- **Search-interest proxies** (Google Trends, Wikipedia page views) — a
  weak, indirect attention proxy that adds no information beyond what
  primary news volume/corporate-events already provide, at real API/ToS
  risk.
- **Patent filings** — near-zero relevance given EGX30/70's actual sector
  composition (banking, telecom, consumer, industrials — not IP-driven
  sectors).
- **Hiring signals / job-posting data** — no demonstrated Egypt-specific
  correlation, and thin public job-board presence for most issuers makes
  the signal sparse even where technically collectible.
- **Satellite imagery** — a real technique at large funds covering
  liquid, large-cap developed-market names; not genuinely free at a
  resolution/frequency useful for this platform's scope, and unproven
  for EGX's actual constituent mix (mostly financials/telecom/
  industrials, not retail-footfall-driven consumer names where this
  technique has its strongest track record).
- **GitHub developer-activity data** — essentially no EGX-listed company
  has public code activity material to its business.
- **Every global index/commodity without a stated causal channel into
  Egypt specifically** — Part 1.9 deliberately includes only oil, wheat,
  US rates/DXY, and EM risk sentiment, each with a named transmission
  mechanism; a "collect every global benchmark" instinct was rejected as
  noise, not signal.

## Part 4 — Ranked by expected decision value (not effort)

Effort is deliberately absent from this ranking, per the mission's rule
10 — several **Critical** items here are also the hardest to build
(PDF financial-statement extraction), and several trivially-easy items
(Google Trends) rank **Low**.

| Rank | Capability | Priority | Why it outranks/underranks its neighbors |
|---|---|---|---|
| 1 | Corporate fundamentals (§3) | Critical | Directly answers Q1–Q3, the core of any long-term thesis; also the largest capability gap (Part 2 #1) |
| 2 | Price & trading data (§2) | Critical | Without it, no entry/exit/technical signal exists at all — but note it answers *fewer* distinct questions (Q1, Q5, Q6) than fundamentals do |
| 3 | Universe/identity (§1) | Critical | Structurally prerequisite to everything else, but contributes no thesis content on its own |
| 4 | Domestic macro, esp. CBE (§6) | Critical | Egypt's FX-dominated risk premium makes this more decision-relevant than in most markets — ranks above sector/peer data despite being less company-specific |
| 5 | Corporate actions & disclosures (§4) | Critical | Both a return-calculation-correctness requirement (dividends/splits) and a direct catalyst signal (Q4) |
| 6 | External sector / FX drivers — Suez Canal, tourism, remittances (§7) | High | A genuinely distinctive, Egypt-specific leading indicator set with no equivalent in a typical developed-market blueprint |
| 7 | Governance & ownership (§5) | High | Q8 is under-served by most equity research platforms generally; EGX's ownership-concentration profile makes it more decision-relevant here than average |
| 8 | Sector/peer comparables (§10) | High | Q7 (relative positioning) frequently drives Hold vs. Reduce more than any absolute metric |
| 9 | Sovereign & credit context (§8) | High | Low-frequency but potentially thesis-dominating (a rating action can override every company-specific signal at once) |
| 10 | News & media (§11) | High | Fast catalyst detection (Q4); ranked below fundamentals/macro because it is corroborating/timing information, not the thesis itself |
| 11 | Global market & commodity context (§9) | High | Real transmission channel into Egypt, but always secondary/contextual, never independently decision-driving |
| 12 | Trading calendar (§12) | Critical (operational only) | Ranked "Critical" for correctness, explicitly **not** counted as a thesis input — a calendar error corrupts every other layer's interpretation |
| 13 | Research/methodology literature (§14) | Medium | Real, but improves the platform's reasoning process, not any ticker's evidence — deliberately capped below every evidence-bearing category |
| 14 | Alternative/corroborating data (§13) | Low | Evaluated in full (Part 1.13) and rejected on the merits, not by default |

---

## Part 5 — The decision-input architecture, redesigned from scratch

Deliberately not derived from `DatasetSnapshot`, `agx_research.agents`, or
any existing module — this is what the architecture would look like
starting from Part 0's ten questions and Part 1's survey alone.

### 5.1 Layers

```
Layer 0 — Identity & Universe
  (ticker, sector, ISIN, free float, index membership)
  → prerequisite for every layer below; no thesis content itself.

Layer 1 — Market Evidence
  (price, volume, liquidity, market breadth)
  → answers Q1 (partially), Q5, Q6.

Layer 2 — Fundamental Evidence
  (financial statements, ratios, trend deltas)
  → answers Q1, Q2, Q3. Highest decision value, hardest extraction.

Layer 3 — Event Evidence
  (corporate actions, disclosures, governance/ownership changes)
  → answers Q4, Q8. Also corrects Layer 1 (split/dividend adjustment).

Layer 4 — Country-Risk Evidence
  (domestic macro, external-sector/FX drivers, sovereign/credit context)
  → answers Q5, Q9. Uniquely weighted for Egypt vs. a typical blueprint.

Layer 5 — Relative Evidence
  (sector indices, peer fundamentals, peer trading data)
  → answers Q7. Requires Layers 1+2 replicated across a ticker's peer set,
    not a new kind of data.

Layer 6 — Narrative Evidence
  (primary financial press, regulator press releases; discovery-tier
   aggregators strictly for corroboration, never independent evidence)
  → answers Q4, Q9 faster than Layer 3/4's own primary disclosures, at
    lower reliability — always a corroborating signal, never sufficient
    alone.

Layer 7 — Data-Quality / Provenance Meta-Layer
  (source reliability, coverage, freshness, corroboration status — a
   layer *about* Layers 0–6, not a new evidence type)
  → answers Q10 directly, and discounts confidence in every other
    layer's conclusions.
```

### 5.2 Synthesis: from layers to thesis components to decision

```
Layers 0-7 (evidence)
        │
        ▼
Thesis Components (one score/read per component, each independently
explainable, each citing which layer(s) and which specific source(s)
produced it):

  - Valuation Read        (Layer 2, vs. own history and Layer 5 peers)
  - Growth/Quality Read    (Layer 2 trend + Layer 6 corroboration)
  - Balance-Sheet Safety   (Layer 2, FX-exposure-aware given Layer 4)
  - Catalyst/Event Read    (Layer 3, timed against Layer 6)
  - Country-Risk Read      (Layer 4 — can override every other component)
  - Relative Positioning   (Layer 5)
  - Governance Read        (Layer 3 ownership/related-party data)
  - Timing/Liquidity Read  (Layer 1)
  - Confidence Discount    (Layer 7 — multiplies, never adds, confidence)
        │
        ▼
Position-Aware Decision Function
  inputs: the 8 Thesis Components above + current position state
          (held / not held, size, cost basis — external, user-supplied,
          never fetched or fabricated, since a portfolio is inherently
          the investor's own data)
  output: one of Buy / Hold / Increase / Reduce / Exit / No Action,
          each requiring an explicit numeric entry/exit condition where
          applicable, an invalidation condition, a confidence score, and
          full evidence provenance back to the specific Layer 0-7 sources
          that produced each Thesis Component feeding it.
```

### 5.3 Design principles this architecture enforces structurally

1. **No thesis component may be computed from a single source.** Every
   component in 5.2 cites Layer evidence that itself came from at least
   the "Critical"/"High" priority sources named in Part 4 — a component
   backed by only a "Low"-priority Part-3 source is not a component, it's
   noise, and the architecture has no path for it to reach a decision.
2. **The Country-Risk Read can override, not just adjust.** Given Q9's
   weight for Egypt specifically (Part 0, Part 4 rank 4/9), a sovereign
   rating downgrade or a capital-control event must be structurally
   capable of forcing every position toward Reduce/Exit regardless of
   what every other Thesis Component says — a typical developed-market
   architecture wouldn't need this override path; this one does.
3. **Layer 6 (Narrative) never independently produces a Thesis Component
   value — it only times or corroborates a Layer 3/4 event.** This
   mirrors the discovery-tier-vs-primary-tier discipline this document
   derived independently in Part 1.11/1.13, before checking whether
   anything similar already existed anywhere.
4. **Layer 7 is multiplicative, not additive.** A low-confidence Layer 2
   read (e.g., only two comparable financial periods available) should
   shrink the resulting Thesis Component's contribution toward zero, not
   simply get labeled "low confidence" while still carrying full weight
   in the decision function.
5. **Position state is external and structural, not optional.** Sections
   5.2's decision function cannot collapse Hold into No Action or
   Increase into Buy, because position state is a first-class required
   input, not an afterthought bolted onto a buy/sell-only model.

---

## Appendix — Convergence and divergence with the existing platform

Required only as a footnote, per the instruction to design from scratch
first: this blueprint's Layers 0–7 map closely to
`docs/DECISION_CENTRIC_AUDIT_2026-07-30.md`'s Tier 1/2/3 capability
groups and to the position-aware six-way decision gap that audit already
identified independently — which is reassuring convergence, not a reason
to skip either document. Three points of genuine divergence worth
carrying into implementation planning:

- This blueprint elevates **External-Sector/FX-driver data** (Suez Canal,
  tourism, remittances — Part 1.7) to its own high-priority category;
  the existing platform has no equivalent capability at all today (not
  even a `PLANNED` entry) — a genuine first-principles addition, not
  already covered under the existing "Macroeconomic" capability.
- This blueprint treats **Sovereign & Credit Context** (rating actions,
  IMF program reviews — Part 1.8) as its own high-priority category; the
  existing platform has no capability for this today either.
- This blueprint's **multiplicative confidence discount** (5.3, point 4)
  is a stronger claim than the prior audit's roadmap item 3.4 ("wire
  reputation into confidence" as an open, unimplemented idea) — worth
  reconciling explicitly during implementation planning, not assumed
  identical.

No other action is implied by this appendix. Per the project owner's
explicit instruction, implementation planning begins only after this
blueprint is reviewed.
