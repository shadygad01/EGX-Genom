# Decision-Centric Gap Audit — EGX-Genom (2026-07-30)

**Status: Phase 1 (Audit) and Phase 2 (Architecture) complete. Phase 3
(Roadmap) below is a plan, not an implementation — no production code
changed in this document's authoring.**

## 0. Mission and method

The project owner's mission for this audit: redesign EGX-Genom around
producing the highest-quality **long-term** investment decisions for EGX,
using only free, legal data, where every retained input demonstrably
improves a **Buy / Hold / Increase Position / Reduce Position / Exit / No
Action** decision. Non-negotiable: preserve the existing architecture
wherever possible — only change what a measurable decision-quality gap
justifies. Do not modify code until this audit and its architecture are
complete.

**Method.** This audit does not re-run the Free Data Census from zero.
`docs/DATA_ACQUISITION.md`, `sources/catalog.py`,
`acquisition_intelligence/capability.py`, and eleven prior mission
write-ups in `docs/PHASE_STATUS.md`/`CURRENT_MISSION.md` already performed
Phases 1–4 of the original mission (source discovery, qualification,
ranking, decision-readiness mapping) under different names, and a prior
session explicitly **froze the acquisition architecture** — future work
must improve decision quality from evidence already connected, not re-open
source discovery (`NEXT_MISSIONS.md`). This audit therefore:

1. Reads the *existing* registry, capability map, decision engine,
   readiness gates, and technical-debt register as ground truth (not
   reconstructed from scratch).
2. Reorganizes that ground truth around **investment decision value**
   instead of source category — the mission's actual ask.
3. Names only the **real, evidenced gaps** a decision-centric lens
   surfaces that the existing architecture doesn't already close.

Every finding below is sourced from reading the current code
(`research/src/agx_research/`) and current docs directly — no source, its
status, or its legal posture is re-asserted from memory.

---

## PHASE 1 — AUDIT (no code changes)

### 1.1 Complete inventory of every current data source

55 `SourceSpec` entries exist in `sources/catalog.py` today (a fresh count
from the code, not from a possibly-stale doc figure):

**16 IMPLEMENTED** (tested collector, real endpoint verified):
`egx_price_composite`, `stooq`, `fred`, `rss_generic`, `worldbank`,
`egx_universe_seed`, `fra_egypt`, `capmas`, `telecom_egypt_ir`,
`orascom_ir`, `enterprise_press`, `gdelt`, `alborsa`, `masrawy_economy`,
`undata`, `global_benchmarks`.

**28 PLANNED** (catalogued, endpoint/collector pending verification):
`mof_egypt`, `egypt_open_data`, `company_ir`, `african_markets_egx`,
`reuters`, `zawya`, `asharq_business`, `cnbc_arabia`,
`alarabiya_business`, `marketscreener`, `skynews_arabia_economy`,
`almal`, `youm7_economy`, `asharq_economy`, `oecd`, `suez_canal_stats`,
`wikipedia_pageviews`, `google_trends`, `github_releases`,
`company_social_official`, `public_telegram`, `patents`,
`hiring_signals`, `arxiv`, `ssrn`, `nber`, `google_scholar`,
`researchgate`.

**1 TOS_REVIEW**: `egid_financial_filings` (ambiguous cross-issuer
automation terms).

**10 DISABLED** (evidenced dead end — WAF/robots/ToS/paid-tier-only —
never a silent "planned" item with no path forward): `egx_official`,
`cbe`, `yahoo_finance`, `stockanalysis`, `investing_com`, `tradingview`,
`investing_news`, `mubasher`, `imf`, `trading_economics`.

No `NEEDS_KEY` sources are catalogued at all (project owner decision,
AD-32/`docs/DATA_ACQUISITION.md`: the platform is scoped to sources
collectable with zero registration/credential, so nothing waits on a key
indefinitely).

Every source's category, access method, update frequency, legal-use
status, and a live-evidenced note is recorded in `sources/catalog.py`
itself — restating all 55 entries' full detail here would duplicate that
file rather than audit it. Section 1.5/2.3 below re-derive what actually
matters for a decision-centric view: not *what exists*, but *what it's
for*.

### 1.2 Additional free, legal EGX-related sources worth considering

Per this codebase's own anti-fabrication discipline (never assert a URL
or feed exists without an independent probe — `AD-24`), these are named as
**candidate organizations for the existing Acquisition Intelligence
Engine to resolve**, not asserted as verified sources. None should be
added to `sources/catalog.py` as anything but `PLANNED`/`CANDIDATE` until
independently probed exactly like every existing `TargetOrganization`.

| Candidate | Why it's a candidate | Why it isn't already catalogued |
|---|---|---|
| Amwal Al Ghad (`amwalalghad.com`) | Egypt-specific financial/stock-market news outlet (distinct from the general-interest Arabic outlets already catalogued) | Not yet named as a `TargetOrganization`; no prior mission's web-search pass covered it |
| Information & Decision Support Center (IDSC), Egyptian Cabinet | Publishes macro/economic bulletins independent of CBE/CAPMAS | Never named; would sit in `MACROECONOMIC` |
| Egypt's Ministry of Planning and Economic Development | Publishes development-plan and budget data relevant to fiscal-policy macro context | Never named |
| Wikidata structured company facts (sector, ISIN, founding date) | Already used for **domain hints** (`discovery.wikidata_lookup`) but never for **company metadata** (sector/ISIN) that could feed `SECTOR_MEMBERSHIP` | Currently scoped to domain resolution only, not data collection |
| google_scholar / researchgate (already catalogued, `PLANNED`) | Redundant with `arxiv`/`ssrn`/`nber` for the same "new quant-finance papers" need, via a strictly worse access method (`HTML_SCRAPE` vs. RSS/API) | Listed for completeness — see 1.8/2.3, recommended **Tier 4 removal**, not expansion |

No other credible, free, legal, EGX-specific source was identified beyond
what `docs/DATA_ACQUISITION.md`'s 55-entry catalog and eleven prior
missions' web-search/discovery passes already found. This is consistent
with those missions' own repeated conclusion: the catalog is close to
exhaustive for what free/legal/no-key EGX data exists; the remaining gap
is **verifying reachability** (blocked on network egress in this sandbox
today), not **finding more organizations to catalog**.

### 1.3 Source qualification (recap of existing pipeline)

Already built and unchanged by this audit: `sources/qualification.py`'s
CANDIDATE → QUARANTINE → EVALUATION → TRUSTED → CORE pipeline, gated
purely on accumulated evidence (`sources/reputation.py`'s 9-dimension
score), never assigned by fiat. Current lifecycle distribution (derived
from `default_lifecycle_for_status`): all 16 IMPLEMENTED sources start
`TRUSTED`/`ACTIVE`; all 28 PLANNED sources sit `CANDIDATE`/`ACTIVE`; the 1
TOS_REVIEW and 0 NEEDS_KEY sources would sit `CANDIDATE`/`PAUSED`; all 10
DISABLED sit `CANDIDATE`/`RETIRED`. This audit found no defect in the
qualification mechanism itself — it is orthogonal to, and unaffected by,
decision-centric reorganization.

### 1.4 Source ranking (as currently computed)

Ranking today happens two ways, both real and unaffected by this audit:
`conflict_priority` (breaks ties when sources disagree on the same fact)
and `sources.reputation.compute_reputation()`'s composite (availability,
accuracy, freshness, coverage, latency, correction_rate, duplicate_rate,
schema_stability, historical_usefulness). **Finding**: neither ranking
mechanism currently feeds *decision* confidence — see 1.8.

### 1.5 Decision mapping

The mission's required mapping is "every field → at least one of Buy /
Hold / Increase / Reduce / Exit / No Action." The codebase's actual
decision surface is `meta.decision_engine.DecisionAction`:
`BUY_CANDIDATE`, `WATCH`, `AVOID`, `ABSTAIN` — a **four-way**, not
six-way, taxonomy, and structurally **position-unaware**: nothing in
`Recommendation`, `HorizonDecision`, or `PortfolioConstructor` records
whether the platform already holds a position in a ticker. This is the
single most important finding of this audit — detailed in full in
**2.5**. Every data source maps to a decision only through this narrower
lens today:

| Data layer (from `meta.readiness`'s own 5 gates) | Feeds which agent/finding | Feeds which `DecisionAction` |
|---|---|---|
| Price (`price_history`) | `liquidity`, `technical_structure`, `market_structure` agents | All four — the only layer that can independently justify `BUY_CANDIDATE` |
| Disclosures/corporate events | `corporate_events` agent | `WATCH`/`AVOID` (drift findings), gates SWING readiness |
| News | `news_intelligence` agent (via `news_sentiment` classifier) | `WATCH`/`AVOID`, gates SWING readiness |
| Macro | `macro` agent | Gates INVESTMENT readiness (≥3 series required); correlational, never alone sufficient for `BUY_CANDIDATE` |
| Financials | **No agent** — `FinancialPerformanceAgent` is a stub | **None** — see 1.8 |
| Knowledge (aggregate of the above, post-validation) | `KnowledgeWeightedHorizonModel` → `MetaDecisionEngine` | All four |

### 1.6 Gap analysis

1. **No position-awareness** (detailed in 2.5): the platform cannot
   distinguish Hold from No Action, or Increase from Buy, or Reduce from
   Exit, because it has no concept of an existing holding. This is an
   architecture gap, not a data gap — closing it needs a new small state
   object, not a new source.
2. **`FinancialPerformanceAgent` is a stub**: `financials/` collects and
   stores `FinancialStatementLineItem`s (via `telecom_egypt_ir`/
   `orascom_ir`, real, `IMPLEMENTED`), `meta.readiness` already gates
   INVESTMENT-horizon readiness on ≥4 comparable financial periods — but
   no agent ever turns a financial statement into a `ResearchFinding`.
   For a **long-term investor** mission specifically, this is the largest
   single gap: fundamentals (margins, leverage, cash flow trends) are
   exactly what a long-horizon Buy/Hold/Increase/Reduce thesis should rest
   on most, and today they influence *readiness gating* but never the
   *thesis itself*.
3. **Macro is capped at "enrichment," never a primary trigger**
   (a project owner decision already recorded in `docs/PHASE_STATUS.md`'s
   Production Execution Phase section) — correct for a mission scoped to
   *company-level* long-term decisions, not macro-driven trading, so this
   audit does not treat it as a gap to close, only to note as intentional.
4. **No sector/peer-comparison layer**: `SECTOR_MEMBERSHIP` is a named
   `Capability` with exactly one (unimplemented) candidate
   (`egx_official`) and zero agent consumes it. A long-term investor's
   Hold/Reduce/Exit decision often depends on relative sector
   positioning ("still the best in its sector" vs. "peers overtaking
   it") — this is a real, currently-unaddressed decision input, but
   correctly requires the (currently blocked) `egx_official`/company
   registry data to build honestly, not a fabricated substitute.
5. **Reputation/quality scores don't reach decision confidence** (1.8):
   a source's measured reliability should plausibly discount a
   recommendation's stated confidence when using a lower-reputation feed,
   and currently does not.

### 1.7 Duplicate analysis

Genuine, already-managed duplication (not a defect — the platform's own
composite/fallback pattern handles it correctly):

- **Price data**: `yahoo_finance` + `stockanalysis` + `mubasher` are all
  `integrated_via="egx_price_composite"` — three legs of one composite
  collector, not three independent sources double-counted. Correctly
  modeled; no change needed.
- **Macro data**: `fred` (global series incl. oil/dollar index/treasury
  yields), `worldbank` (annual Egypt indicators), `undata` (UN SDG
  Egypt), and `capmas` (Egypt CPI) overlap conceptually (all "macro") but
  cover **disjoint series**, not the same fact from different sources —
  correctly complementary per `CapabilityDecisionEngine`'s own design
  ("Macroeconomic runs every ready strategy... complementary, not
  redundant").
- **News**: `enterprise_press`/`fra_egypt`/`alborsa`/`masrawy_economy`
  are all `IMPLEMENTED` `rss_generic` configs feeding the same
  `NewsIntelligenceAgent`/`CorporateEventsAgent` path — genuine
  redundancy is *intended* here (independent corroboration across
  outlets), not a defect.
- **Real, unmanaged duplication found**: `google_scholar` and
  `researchgate` (both `PLANNED`, `HTML_SCRAPE`) serve the exact same need
  as `arxiv`/`ssrn`/`nber` (already `PLANNED`, cleaner RSS/API access) —
  see 1.8/2.3 for the removal recommendation.
- **`global_benchmarks`** is a bookkeeping entry describing configuration
  of `stooq`/`fred` that already exist as their own `SourceSpec`s — not
  wrong, but redundant as a *separate* catalog row rather than a note on
  those two specs. Flagged as a Phase 3 cleanup, not urgent.

### 1.8 Dead-input analysis

Full field-by-field detail (produced by direct code reading, not
inference):

| Input | Collected/stored? | Reaches a `ResearchFinding`/decision? | Verdict |
|---|---|---|---|
| `FinancialStatementLineItem` (all fields) | Yes — real collectors, real CSV materialization, real coverage/readiness gating | **No** — `FinancialPerformanceAgent` stub means zero path to a finding | Dead for *decisions* today; **not** dead for *readiness gating*. Highest-priority item to un-stub (1.6.2). |
| `PriceBar.open/high/low` | Yes | **No** — only `close`+`volume` reach any agent; open/high/low are validation-only (`data/quality.py`) | Dead for decisions. Legitimate to keep for validation; not a source to remove, a field to leave as-is. |
| `CorporateEvent.description` | Yes | **No** — stored/serialized only | Same verdict — display-only field, not a removal candidate (it's the human-readable audit trail for the event). |
| `CorporateEvent.details` (arbitrary dict) | Yes | **Partially** — only `split_ratio`/`dividend_amount` keys are ever read (`data/adjustments.py`) | Any other key round-trips unused. Not a source problem — a documentation-of-intent problem (Phase 3). |
| `FinancialStatementLineItem.currency` | Yes | **No** — write-only | Minor; harmless, low priority. |
| `sources.reputation` composite score | Yes, fully computed | **No** — feeds dashboard/health monitoring only, never discounts a `Recommendation.confidence` | Real gap (1.6.5) — the platform already measures exactly the signal ("how much should I trust this source") a decision-confidence calculation should use, and doesn't. |
| `DatasetSnapshot.version`/`macro_lookback_days`/`pattern_lookback_days` | N/A (build-time control fields, not collected data) | N/A | Not data-source debt; excluded from source Tier assignment. |

**No entirely-dead *source*** was found beyond what 1.7 already flags
(`google_scholar`/`researchgate`) — every `IMPLEMENTED` source's collected
records reach at least the readiness-gating layer even where they don't
yet reach a finding. The dead weight here is at the **field** and
**agent-stub** level, not the source level, with one structural
exception: **11 catalogued sources have zero mapping in
`acquisition_intelligence/capability.py`'s `CAPABILITY_STRATEGIES`** —
meaning even the platform's own capability-based acquisition engine
doesn't consider them a strategy for anything: `wikipedia_pageviews`,
`google_trends`, `github_releases`, `company_social_official`,
`public_telegram`, `patents`, `hiring_signals`, `google_scholar`,
`researchgate`, `investing_com`, `tradingview`. This is the strongest,
most evidence-grounded signal this audit found for Phase 2's Tier-4
list — it isn't a subjective judgment, it's an absence already present in
the code.

---

## PHASE 2 — DECISION-CENTRIC INPUT ARCHITECTURE

### 2.1 Why reorganize, and around what axis

The mission asks to organize inputs "by investment value instead of
source type." The codebase already built exactly this axis and it isn't
`SourceCategory` (official/company/market_data/news/...) — it's
`acquisition_intelligence.capability.Capability`, whose own docstring
states the same principle this mission asks for verbatim: *"a homepage is
not a data source... AGX needs independent kinds of data."* Re-deriving a
new Tier scheme from `SourceCategory` would duplicate work and drift from
`CAPABILITY_STRATEGIES`, the ranked pool the runtime `CapabilityDecisionEngine`
already executes against. This audit's Tier 1–4 classification is
therefore assigned **per Capability**, with individual sources inheriting
their capability's tier unless a specific source's role diverges (e.g. a
capability's own discovery-only leg).

### 2.2 Tier definitions (as applied below)

- **Tier 1 — Core Decision Source**: directly produces or gates a
  `ResearchFinding`/`Recommendation` for at least one horizon, or is a
  structural prerequisite without which no other capability can attach to
  a ticker (identity).
- **Tier 2 — Supporting Evidence**: real, wired, measurably useful, but
  correlational/corroborating rather than independently decision-driving
  (macro context; a discovery-only leg that requires independent
  corroboration to become evidence; an acquisition channel that feeds a
  Tier 1 capability rather than being consumed directly).
- **Tier 3 — Context**: operationally necessary or plausibly relevant but
  not yet — and not designed to be — consumed by any decision-producing
  agent (calendar, sector taxonomy, methodology literature).
- **Tier 4 — Remove**: no capability mapping, no agent consumer, and no
  credible path to one without inventing a use this platform doesn't
  actually have.

### 2.3 Tier assignment — all 13 capabilities + their sources

| Capability | Tier | Sources (status) | Decision contribution | Currently used? | Should remain? |
|---|---|---|---|---|---|
| **Price Data** | **1** | `egx_price_composite` (IMPL, composed of yahoo/stockanalysis/mubasher legs), `stooq` (IMPL, legally blocked), `egx_official` (DISABLED), `company_ir` (PLANNED) | Sole independent basis for `BUY_CANDIDATE`; drives liquidity/technical/pattern findings | **Yes** — the only capability every agent ultimately depends on | Yes — irreplaceable |
| **Corporate Disclosures** | **1** | `egx_official` (DISABLED), `fra_egypt` (IMPL), `company_ir` (PLANNED), `enterprise_press` (IMPL), `mubasher` (DISABLED), `zawya` (PLANNED) | Drives `CorporateEventsAgent` drift findings; gates SWING readiness | Yes (via `fra_egypt`/`enterprise_press`) | Yes |
| **Corporate Actions** | **1** | same pool as Disclosures + `reuters` (PLANNED) | Split/dividend adjustment (`data/adjustments.py`) — without this, every return calculation would be wrong | Yes (headline-classified only, TD-29) | Yes |
| **Financial Statements** | **1*** | `egid_financial_filings` (TOS_REVIEW), `telecom_egypt_ir`/`orascom_ir` (IMPL), `company_ir` (PLANNED) | Should drive fundamentals-based long-term thesis; currently gates readiness only | **No agent consumes it** (stub) | Yes — Tier 1 by design intent, but non-contributing until 3.1 closes |
| **Investor Relations** | **2** | same pool as Financial Statements | Acquisition *channel* for Financial Statements/Disclosures, not an independent evidence layer itself | Yes, as a channel | Yes |
| **News** | **1** | `reuters`/`zawya`/`asharq_business`/`cnbc_arabia`/`alarabiya_business`/`marketscreener`/`investing_news`/`almal`/`youm7_economy`/`skynews_arabia_economy`/`asharq_economy` (all PLANNED or DISABLED) + `enterprise_press`/`alborsa`/`masrawy_economy` (IMPL) + `gdelt`/`mubasher` (special-cased below) | Drives `NewsIntelligenceAgent` sentiment-drift findings; gates SWING readiness | Yes (3 real outlets) | Yes |
| **News — GDELT leg specifically** | **2** | `gdelt` (IMPL, `EvidenceTier.DISCOVERY`) | Structurally can never independently become evidence — only corroborates a PRIMARY source's report | Yes, as corroboration only | Yes, exactly as scoped (do not promote to Tier 1) |
| **Macroeconomic** | **2** | `worldbank`/`fred`/`undata`/`capmas` (IMPL), `imf`/`trading_economics` (DISABLED), `oecd`/`mof_egypt` (PLANNED), `cbe` (DISABLED) | Real `MacroAgent` correlation findings; gates INVESTMENT readiness (≥3 series) — but explicitly "enrichment, not primary" per the project owner's own prior decision | Yes | Yes, at exactly its current (secondary) weight |
| **Market Breadth** | **3** | none (deliberately derived from Price Data, not fetched) | Would support market-regime context for a Hold/Reduce call | No artifact yet (named gap in `NEXT_MISSIONS.md`) | Yes, as a derived Tier-3 artifact once built — not a new source |
| **Trading Calendar** | **3** | `egx_official` (DISABLED) | Operational correctness (which days are trading days), not evidentiary | Placeholder table only | Yes — necessary, not decision-driving |
| **Index Constituents** | **1** | `egx_universe_seed` (IMPL), `egx_official` (DISABLED) | Structural prerequisite — without it, no ticker↔name identity resolution, no news attribution, no universe to decide over at all | Yes | Yes — foundational |
| **Sector Membership** | **3** | `egx_official` (DISABLED) — sole candidate | Would support peer/sector-relative Hold/Reduce reasoning (1.6.4) | **No agent consumes it; no data exists yet** | Yes as a target capability, currently empty — real gap, not fabricable without `egx_official` or an equivalent |
| **Economic Releases** | **3** (folds into Macroeconomic) | `trading_economics`/`cbe`/`capmas`/`mof_egypt` | Redundant capability label over the same sources as Macroeconomic | No independent consumer | Recommend **merging into Macroeconomic** (Phase 3) rather than removing sources |
| **Research Papers** | **3** | `arxiv`/`ssrn`/`nber` (PLANNED, real RSS/API) | Improves the platform's *own methodology* (Scientist Framework/genome lineage), never an individual ticker's thesis | Not yet collected | Keep as Tier 3 (methodology, not investment evidence) — do not conflate with per-ticker decision inputs |

`*` Financial Statements is scored Tier 1 by **design intent** (a
long-term-investor mission cannot be complete without fundamentals) even
though it is currently non-contributing — see 2.5's distinction between
"should be Tier 1" and "is currently pulling Tier-1 weight."

### 2.4 Tier 4 — Remove

| Source | Why | Currently used? | Should remain? |
|---|---|---|---|
| `google_scholar` | `HTML_SCRAPE`, no collector, no `Capability` mapping, redundant with `arxiv`/`ssrn`/`nber`'s cleaner access | No | **No** — remove from catalog |
| `researchgate` | Same reasoning | No | **No** |
| `wikipedia_pageviews` | No `Capability` mapping, no collector, no agent could plausibly consume a raw page-view count as investment evidence under this platform's evidence-based philosophy | No | **No** |
| `google_trends` | No official API (`AccessMethod.JSON_API` declared but no real endpoint exists per the source's own note), no mapping, no consumer | No | **No** |
| `github_releases` | Speculative "tech signal" for a universe (EGX30/70) that is financial/industrial/telecom-heavy, not tech-heavy; no mapping, no consumer | No | **No** |
| `company_social_official` | Needs per-platform API review/keys; no mapping, no consumer | No | **No** |
| `public_telegram` | Needs a bot token (quasi-credential, against the no-key policy in spirit); no mapping, no consumer | No | **No** |
| `patents` | No mapping, no consumer, unclear relevance to EGX30/70's actual sector mix | No | **No** |
| `hiring_signals` | No mapping, no consumer | No | **No** |
| `investing_com` | DISABLED (403 site-wide), no `Capability` mapping despite being a plausible Price Data/News candidate in principle | No | **No** — already dead, remove rather than leave as a permanent DISABLED row |
| `tradingview` | DISABLED (ToS), no mapping | No | **No** |

**11 sources recommended for removal.** None of them currently
contribute to any capability, any agent, or any decision — removing them
is pure registry cleanup with zero loss of decision-relevant capability,
per rule 6 of the mission.

### 2.5 The decision-taxonomy gap (the audit's central finding)

The mission requires **Buy / Hold / Increase Position / Reduce Position /
Exit / No Action**. The codebase's `DecisionAction` has **Buy_Candidate /
Watch / Avoid / Abstain** — four states, and every one of them is
evaluated **without knowing whether a position already exists**:

- `BUY_CANDIDATE` conflates "open a new position" and "add to an existing
  one" — these are different real-world actions with different risk
  profiles (averaging up vs. initiating), and `PortfolioConstructor`
  currently has no way to represent "increase toward the same cap" versus
  "initiate at the cap."
- `WATCH` conflates "no existing position, no action" (**No Action**) and
  "existing position, no new evidence to change it" (**Hold**) — these
  read identically today because nothing tracks the existing position.
- `AVOID` conflates "don't buy" (**No Action** on a name never held) and
  "sell what you have" (**Exit**, or **Reduce** if only trimming) — again
  because there's no held-position state to consult.
- `ABSTAIN` (insufficient evidence) has no six-way equivalent named in the
  mission — it should probably remain a distinct, honest "insufficient
  evidence" state layered *underneath* whichever of the six actions would
  otherwise apply, not merged into any of them (fabricating a Hold/No
  Action from insufficient evidence would violate this platform's own
  anti-fabrication principle).

**This is an architecture gap, not a data gap.** Every data source
already needed to compute the six-way decision exists in the pipeline
today (price for entry/exit levels, knowledge for thesis strength,
readiness gates for confidence) — what's missing is a **position state**
input (what does the portfolio currently hold, and since when) that nothing
in `domain/`, `portfolio/`, or `meta/` currently models. Per the mission's
rule 4 (preserve the existing architecture unless proven improvement),
this is exactly the kind of gap that justifies a real change: the current
four-way taxonomy demonstrably cannot express three of the six mandated
actions (Hold vs. No Action; Increase vs. Buy; Reduce vs. Exit) for any
long-term investor who already holds positions — which is the mission's
explicitly named audience.

### 2.6 Per-field summary (dead-input table, decision-centric columns)

Restating 1.8 in the exact columns the mission specified:

| Field | Collection method | Validation method | Decision contribution | Tier | Confidence | Provenance | Used today? | Remain? |
|---|---|---|---|---|---|---|---|---|
| `PriceBar.close` | Composite HTTP fetch (`egx_price_composite`) | `data.quality.validate_price_bars` | Core input to every return-based finding and entry/invalidation price | 1 | Measured (`reliability_score` 0.75, declared prior) | `RawDocument` → provenance index | Yes | Yes |
| `PriceBar.volume` | Same | Same | Sole driver of liquidity findings | 1 | Same | Same | Yes | Yes |
| `PriceBar.open/high/low` | Same | OHLC sanity checks only | None | — (not tiered; validation-only) | N/A | Same | Validation only | Yes, as-is |
| `CorporateEvent.event_type/event_date` | `RssNewsCollector` headline classifier (TD-29) | Keyword heuristic, uncalibrated | Drift-finding trigger; adjustment-factor trigger | 1 | Low (uncalibrated, TD-29) | Same | Yes | Yes |
| `CorporateEvent.details.split_ratio/dividend_amount` | Same | `data/adjustments.py`'s cum-dividend-close discipline | Return-adjustment correctness (prevents fake-huge-return bugs) | 1 | High (deterministic once present) | Same | Yes | Yes |
| `FinancialStatementLineItem.*` | `TelecomEgyptFinancialHighlightsCollector`/`OrascomFinancialHighlightsCollector` | Fails closed unless explicitly labelled amount present | **Should be** long-term-thesis-defining; **is** readiness-gating only | 1 (intended), 0 (actual, pending 3.1) | High for the 2 companies covered; zero coverage elsewhere | Same | Readiness only | Yes — un-stub, don't remove |
| `NewsItem.headline/tickers` | `RssNewsCollector` + `entity_resolution.resolve_ticker_mentions` | Word-boundary/full-name matching (TD-36 fix); known false-positive class for short/common-word tickers (TD-42, open) | Sentiment-drift finding trigger | 1 | Medium (TD-35 uncalibrated sentiment lists) | Same | Yes | Yes |
| `MacroObservation.value` | `FredCsvCollector`/`WorldBankCollector`/`UnSdgCollector`/`CapmasIndicatorCollector` | Point-in-time lag floor (`data/point_in_time.py`) | Correlational SWING/INVESTMENT context, readiness gate | 2 | High (official sources, declared 0.9 prior) | Same | Yes | Yes |
| `IndexConstituent.ticker/company_name` | `UniverseProvider` (collected + static fallback) | Point-in-time snapshot per `as_of_date` | Identity backbone for every other layer | 1 | High for the 2 EGX30 real-company-name rows; placeholder elsewhere | Same | Yes | Yes |
| `sources.reputation` composite | `compute_reputation()` | 9-dimension formula, itself uncalibrated (TD-33) | **Should** discount recommendation confidence; currently doesn't | 2 (intended target for 3.4) | N/A | N/A | Dashboard/health only | Yes — wire it in (3.4), don't remove |

---

## PHASE 3 — IMPLEMENTATION ROADMAP (plan only; no code in this pass)

Ordered by decision-quality impact per unit of engineering effort, and
filtered to exclude anything the acquisition freeze or this audit's own
"preserve unless proven" rule would rule out.

### 3.1 Six-way, position-aware decision taxonomy (highest priority)

**Why first**: this is the one gap Section 2.5 shows the current
architecture *cannot* express at all, for the mission's explicitly named
long-term-investor audience, with data that already exists.

- Add a small, versioned `PositionState` (`ticker`, `held_since`,
  `quantity` or `held: bool`, `average_cost` optional) — a new, minimal
  domain object, not a rewrite of `Recommendation`/`HorizonDecision`.
  Source: user-supplied (a portfolio is inherently the investor's own
  data, not something to fetch or fabricate) — matches the mission's rule
  7 ("document as a capability gap" where real data can't be collected;
  here, the "data" is inherently external to any public source).
- Extend `MetaDecisionEngine._decision_for_prediction` (or a thin wrapper
  around it) to take `PositionState | None` and re-map the existing
  four-way `score`/`confidence` logic onto six actions:
  `BUY` (no position, positive score), `INCREASE` (position exists,
  positive score, below cap), `HOLD` (position exists, no disqualifying
  new evidence), `REDUCE` (position exists, score turns negative but not
  sharply), `EXIT` (position exists, score strongly negative or knowledge
  retired), `NO_ACTION` (no position, non-positive score). `ABSTAIN`
  remains a distinct overlay for insufficient evidence, per 2.5.
- `PortfolioConstructor` gains the ability to size an `INCREASE`
  relative to the existing position's weight (capped the same way a
  fresh `BUY` is today), rather than only ever sizing from zero.
- This is additive: every existing test, gate, and publication-safety
  check keeps working for a caller that passes `PositionState=None`
  (equivalent to today's behavior), so it doesn't touch `promote()`,
  the publication gate, or the ledger's schema in a breaking way.

### 3.2 Un-stub `FinancialPerformanceAgent`

**Why second**: Section 1.6.2/2.3 both name this as the single largest
data-to-decision gap for a long-term mission specifically. The data
already exists (`telecom_egypt_ir`/`orascom_ir`, real, tested,
`IMPLEMENTED`) and is currently used only for readiness gating. Define a
small, honest fundamental-factor set (e.g. margin trend, leverage trend,
revenue growth trend across the periods actually collected) and produce a
`ResearchFinding` the same way every other real agent does — abstaining
where fewer than the readiness gate's own 4-period floor exists, never
fabricating a trend from 1–2 points. Scope note: this closes real debt
already named in `docs/PHASE_STATUS.md` (System 08, "only
FinancialPerformanceAgent remains a stub") — not new scope invented by
this audit.

### 3.3 Merge `Economic Releases` into `Macroeconomic`

**Why**: 2.3 shows these are the same source pool under two capability
labels with no independent consumer distinguishing them. Low effort,
zero decision-quality risk, pure clarity — a one-line change in
`acquisition_intelligence/capability.py` removing a redundant enum value
and its pool, with call sites updated to the merged label.

### 3.4 Wire measured source reputation into recommendation confidence

**Why**: 1.6.5/2.6 both name this — the platform already computes exactly
the "how much should I trust this source" signal a decision-confidence
calculation needs and throws it away at the recommendation boundary.
Concretely: `KnowledgeWeightedHorizonModel`/`MetaDecisionEngine` could
discount a prediction's contribution by the mean `reputation_score` of
the sources behind its supporting knowledge, the same way `conflict_priority`
already resolves cross-source disagreement. This is a genuine
decision-quality improvement candidate per rule 5, but per `docs/TECHNICAL_DEBT.md`
TD-33 the reputation formula itself is uncalibrated — implement as an
explicit, documented, overridable discount (not a silent reweighting),
and log it as new debt akin to TD-6/TD-17 until real history calibrates
it.

### 3.5 Remove the 11 Tier-4 sources named in 2.4

Pure registry cleanup: delete the 11 `SourceSpec` entries from
`sources/catalog.py`, remove any references in tests/fixtures, and note
the removal in `docs/TECHNICAL_DEBT.md`/`docs/DATA_ACQUISITION.md`'s
catalog-size counts (following the exact precedent of the prior
FMP/AlphaVantage/Polygon/Tiingo removal — "removed because no free,
no-key path exists," here "removed because no capability/consumer path
exists"). Zero risk: none of the 11 currently contribute to any decision.

### 3.6 Sector Membership and Market Breadth (name, don't force)

Per the mission's rule 7 and this codebase's own established discipline:
`Sector Membership`'s sole candidate (`egx_official`) is blocked by the
same evidenced anti-bot wall named throughout `docs/PHASE_STATUS.md`; do
not chase a substitute. `Market Breadth` needs a backend-computed
artifact (advancers/decliners) derivable from already-collected Price
Data — this is real, low-risk, closeable work (already named as a gap in
`NEXT_MISSIONS.md`), but it's additive dashboard/analytics work, not a
new source, and is lower priority than 3.1/3.2 for decision quality.

### 3.7 Amwal Al Ghad + IDSC as new `TargetOrganization` candidates

Per 1.2: add both as identity-only `TargetOrganization` entries (name/
category/country, no URL) for the existing, unmodified Acquisition
Intelligence Engine to independently resolve on its next run with real
network egress — exactly the same process every other candidate in this
codebase went through. This is the one item in this roadmap that touches
the acquisition side at all, and it does so through the existing frozen
mechanism (naming an organization for the engine to probe), not by
reopening acquisition *architecture* work.

### Explicitly not recommended

- **No new source-discovery sprint.** 1.2 found the existing catalog
  already covers the credible free/legal universe; the acquisition
  freeze stands.
- **No rewrite of `MetaDecisionEngine`, `PortfolioConstructor`, or the
  publication gate.** 3.1 is additive (a new optional input), not a
  replacement, per the mission's rule 4.
- **No removal of `arxiv`/`ssrn`/`nber`** despite their Tier-3
  (not Tier-1) status — they serve a real, distinct purpose (platform
  methodology, not per-ticker evidence) that the mission's rule 6 doesn't
  ask to eliminate, only to stop conflating with investment-decision
  inputs.

---

## Cross-reference

This audit intentionally does not restate `docs/PHASE_STATUS.md`'s
system-by-system status (unchanged — no code moved in this pass) or
`docs/TECHNICAL_DEBT.md`'s existing register (cited by number throughout).
See `docs/DATA_ACQUISITION.md` for the full source-registry design and
`docs/ACQUISITION_STRATEGY.md` for the capability-engine design this
audit's Tier assignment builds directly on.
