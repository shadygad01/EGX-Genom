# EGX-Genom Repository Assessment for the Investment Dashboard

**Assessment date:** 13 August 2026  
**Repository reviewed:** [shadygad01/EGX-Genom](https://github.com/shadygad01/EGX-Genom)  
**Conclusion:** The existing repository already contains most of the requested investment-research platform. The correct direction is **integration and focused extension**, not a separate dashboard application.

## Executive conclusion

The live repository is not an empty project or merely a pattern-discovery experiment. Its README describes AGX / Project Alpha Genome as an autonomous quantitative research platform dedicated to the Egyptian Exchange and focused on EGX30 and EGX70. It explicitly separates research from signal generation and requires statistical validation, stress testing, backtesting, peer validation, promotion, and explanation before a relationship can inform a recommendation [1].

The repository already has the major layers needed for the requested product: a Python research engine, a Fastify API, a React/Vite dashboard, financial-statement collection, valuation metrics, a full-universe opportunities view, macro and market-intelligence pages, monitoring, source registry, provenance, static/API data providers, and a self-hosted VPS runbook [1] [2] [3] [4]. Building a second `/dashboard` application would duplicate the existing web layer and would split the source-of-truth, contracts, tests, i18n, deployment, and research artifacts.

The existing platform is therefore a strong foundation for the requested daily decision-support dashboard. However, the repository also records material limitations that must remain visible: the live collector and public deployment cadence have been deliberately changed to twice daily; the current free-source strategy has incomplete price and fundamental coverage; the repository’s own real-data evidence says that only 4 of 100 tickers cleared the three-of-seven fair-value floor in one examined snapshot; and the current dashboard can show honest empty or pending states instead of fabricating values [5] [6].

## What is already reusable

| Requested capability | Existing repository evidence | Assessment |
|---|---|---|
| EGX30/EGX70 universe | README and `MarketIntelligence`/`InvestmentCases` use the Egyptian Exchange universe and expose constituents, sectors, horizons, and full-universe rows [1] [7] [8] | Reuse directly; verify the current constituent snapshot and its point-in-time provenance. |
| Daily opportunity ranking | `InvestmentCases.tsx` ranks recommendations by combined expected return, supports horizon filters, previews evidence, and includes a universe table with coverage/readiness [7] | Reuse as the core scanner; add the user’s preferred valuation-gap and six-month-low columns. |
| Investment case detail | Existing routed `/cases/:ticker` page and the recommendation/evidence data model are already present [3] [7] | Reuse; add an explicit valuation-assumption block and source-age panel. |
| Market and macro dashboard | `MarketIntelligence.tsx` already shows constituent composition, sectors, macro observations, corporate events, market breadth, market regime, and macro-overlay implications [8] | Reuse and extend with Egypt-specific inflation, rates, EGP/USD, debt, reserves, and news source cards where data exists. |
| Valuation | `ValuationMetrics` computes market P/E, EPS, dividend yield, beta, enterprise value, EV/EBITDA, P/B, DCF per share, weighted fair value, bear case, bull case, included models, and unavailable reasons [9] | Strong base. Do not replace with a single opaque fair-value number; expose method, assumptions, periods, currency, and missing inputs. |
| Financial statements | The repository’s financials package models line items by ticker, period end, statement type, value, and currency, and materializes collected statements under `financial_statements/<TICKER>.csv` [5] | Reuse. The remaining work is source coverage, reconciliation, and freshness rather than inventing a new financial model. |
| Free-source acquisition framework | `DATA_ACQUISITION.md` defines source discovery, legality, stability, historical availability, source qualification, health, provenance, replay, and collector interfaces [10] | Reuse as the source-governance backbone. Do not bypass its robots/ToS rules. |
| Source quality and freshness | `SourceSpec`, source registry, health monitoring, provenance index, raw archive, and artifact manifest are already part of the architecture [10] [11] | Reuse and surface this metadata on every investment row and valuation card. |
| Browser dashboard | `web/` is a React/Vite app with seven main routes plus deeper research routes, bilingual i18n/RTL support, a provider factory, and reusable primitives [3] [12] | Extend the existing app rather than shipping the standalone prototype. |
| Static and live deployment | `StaticJsonProvider` and `ApiProvider` share one `DashboardDataProvider` contract; the self-hosted runbook builds `web` in selfhosted mode and proxies API requests through Nginx [3] [4] | Reuse. The user’s VPS is compatible with the repository’s intended self-hosted option. |
| Monitoring and alerts | `Monitoring.tsx` already renders warnings, shadow-fund state, transactions, execution deltas, and review-related signals [13] | Extend with a browser-only six-month-low alert based on validated latest-price snapshots. |
| Decision support without execution | README describes on-demand decision and capital-allocation routes using externally supplied positions; the platform is not an order-execution system [1] [3] | Matches the user’s requirement for screening and ranking only. Keep execution out of scope. |

## Material gaps that must not be hidden

The most important gap is not the frontend. It is **live, legally usable, sufficiently broad Egyptian market data**. The README says that the current production pipeline runs against mock or replayed data and that no live collector is wired in yet; it also says a licensed EGX vendor remains a gating decision before any output is real research [1]. The data-acquisition documentation describes a free-source framework, but it also explains that this environment has faced network, robots, terms-of-use, and source-stability blockers [10].

The current source catalog already contains an implemented composite price adapter using Yahoo, StockAnalysis, and Mubasher fallback legs, but its declared latency is end-of-day and its notes require ongoing monitoring of provider-specific terms and endpoint stability [11]. The repository therefore contains a useful daily-price architecture, not a verified exchange-grade one-minute feed. A server process can poll every minute, but it cannot create new market information when every upstream source is delayed or publishes only after the close.

The repository’s own latest deployment history is especially important for this project. The current `egx-collector.timer` is configured for 07:00 and 16:00 Africa/Cairo, twice daily, with the 16:00 run intended to capture the EGX session close [14]. A recent repository commit description says the collector was deliberately changed from every minute to twice daily and that GitHub Pages was also reduced to twice daily. Therefore, the user’s requested “update every minute” is not the current repository behavior. It is an architectural requirement that must be reconsidered at the source and license level, not merely implemented as a frontend timer.

The valuation layer is ahead of the available inputs but is not yet broad enough to support a uniform fair-value claim across the full universe. The repository’s mission log reports that `egxpilot_fundamentals` fetched 100 distinct tickers in one real production-state snapshot and that financial-statement CSV files existed for all 100 tickers; nevertheless, only 4 of 100 cleared the three-of-seven fair-value floor because `cash_and_equivalents` was missing for 100/100, `ebitda` for 98/100, and `total_debt` for 99/100 [6]. The same log reports that one discovered financial source had only reached five real companies before a pagination fix and that missing inputs must remain explicit rather than fabricated [6].

The repository also reports a real pattern-discovery multiple-testing problem: 7,899 candidates produced 1,773 validated patterns in a run against 14 EGX30-covered tickers, while 354 EGAL patterns collapsed to 19 base-feature groups after removing window suffixes [5] [6]. This is not a reason to delete the research engine. It is a reason to ensure that the investment dashboard consumes only the repository’s gated, explainable recommendation artifacts and clearly labels system maturity, data quality, and unresolved evidence gaps.

## Recommended direction

The standalone dashboard prototype should not become the production application. It can be retained as a visual reference, but the production implementation should be moved into the existing `web/` application and wired through its existing `DashboardDataProvider` interface. The existing API, research artifacts, Pydantic models, TypeScript contracts, provider factory, tests, bilingual i18n, and self-hosted deployment should remain the single integration path.

The product should be reframed as an **EGX Investment Research Desk** rather than as a new generic dashboard. Its primary landing page can remain the existing CIO Desk because the repository’s product law already gives that page a decision-first purpose. The main additions should be an Opportunity Scanner view that joins recommendation, valuation, price-distance, data-quality, and expected-horizon fields; a Valuation Lab view that exposes assumptions and missing inputs; and a source/freshness panel that prevents a stale or incomplete value from appearing equivalent to a verified one.

| Integration workstream | Reuse | Focused extension |
|---|---|---|
| Universe | Existing `UniverseProvider`, `MarketState`, constituent map, and full-universe table | Verify EGX30/EGX70 membership source, effective dates, ticker mappings, and missing constituents. |
| Prices | Existing composite price collector, raw archive, provenance, price-bar validation | Add an explicit six-month low artifact and a source-age/latency field; do not claim one-minute freshness without a source that supports it. |
| Fundamentals | Existing financial-statement provider and line-item materialization | Expand coverage where legally possible; expose “unavailable reasons” and fiscal periods beside each ratio. |
| Valuation | Existing `compute_valuation_metrics` and `FairValueEngine` | Add method-level assumptions, scenario ranges, and a consistent currency/period display. |
| Ranking | Existing recommendations, horizon predictions, readiness, and Investment Cases | Add a transparent composite score: expected return, valuation gap, risk, confidence, liquidity, data quality, and macro overlay. Keep the score descriptive, not a black box. |
| Macro/news | Existing macro observations, macro snapshot, corporate events, RSS/event platform, source registry | Add Egypt-specific debt/inflation/rates/reserves/news tiles only when their metadata and freshness are present. |
| Alerts | Existing Monitoring page and browser frontend | Add a local browser notification rule for validated price distance from the six-month low; record last notification state to avoid repeated alerts. |
| Hosting | Existing VPS systemd, Nginx, API, collector, verify script, and selfhosted Vite mode [4] | Use the existing runbook rather than the standalone Docker shell. Align timer policy with actual data-source cadence. |

## Proposed implementation sequence

First, obtain or verify the current upstream checkout and run the repository’s existing API/web/research tests and build. The previous local `/dashboard` prototype was built in a directory that did not contain the upstream application and therefore should not be treated as the current production base.

Second, add a single typed artifact for opportunity-ranking rows, or extend the existing `InvestmentCases`/`DecisionReadiness` contracts if the fields already exist in the current branch. A row should include ticker, index membership, company name, current price, six-month low, distance from low, P/E, forward P/E only when a forecast EPS source exists, P/B, EV/EBITDA, DCF/scenario range, expected return by horizon, confidence, risk, liquidity, macro overlay, source quality, retrieved-at timestamp, and explicit unavailable reasons.

Third, add or extend a `price_proximity` artifact generated by the research pipeline rather than calculating six-month lows in React. The pipeline must use point-in-time adjusted or explicitly unadjusted prices consistently, define the six-month trading-day window, record the as-of date, and withhold the alert when the price or lookback history is stale or incomplete.

Fourth, extend the existing web pages rather than adding a parallel app. The best placement is `/cases` for ranking, `/cases/:ticker` for valuation and evidence, `/market` for macro and news, `/monitoring` for six-month-low alerts and thesis changes, and `/settings` for source/freshness and user alert preferences.

Fifth, reconcile the user’s one-minute refresh request with the repository’s twice-daily collector policy. If the only legally usable free price sources are end-of-day or delayed, keep the server health check frequent but label the underlying data as delayed. If a truly minute-level public source is later verified and permitted, add a separate high-frequency collector and rate-limit policy rather than changing the existing daily collector blindly.

## Final recommendation

**Do not redirect the project entirely.** The repository already is the investment-research platform the user wants, and it contains substantially more relevant functionality than the separate prototype. Redirecting the whole project would discard existing valuation, source-governance, provenance, readiness, macro, monitoring, and self-hosted deployment work.

**Do redirect the implementation effort.** Stop extending the standalone `/dashboard` prototype as a production product. Integrate the user-facing workflow into the upstream `web/` and `api/` layers, connect it to the existing research artifacts, and make the remaining work explicit: verified free-source coverage, valuation-input completeness, price freshness, six-month-low artifact generation, and transparent ranking.

The repository is therefore **usable and directionally aligned**, but it is not yet safe to describe every displayed opportunity as a current, fully valued EGX investment opportunity. The correct product behavior is to rank only evidence-backed rows, display data quality and as-of timestamps, preserve explicit missing fields, and keep the system in research mode when source coverage or valuation inputs are insufficient.

## References

[1]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/README.md "EGX-Genom README"

[2]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/package.json "EGX-Genom workspace package"

[3]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/web/src/data/DataProvider.ts "DashboardDataProvider contract"

[4]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/deploy/README.md "Self-hosted VPS deployment runbook"

[5]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/DATA_ACQUISITION.md "AGX Data Acquisition Platform"

[6]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/CURRENT_MISSION.md "Current mission and verified project findings"

[7]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/web/src/pages/InvestmentCases.tsx "Investment Cases page"

[8]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/web/src/pages/MarketIntelligence.tsx "Market Intelligence page"

[9]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/research/src/agx_research/valuation/metrics.py "Valuation metrics implementation"

[10]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/docs/ARCHITECTURE.md "AGX architecture"

[11]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/research/src/agx_research/sources/catalog.py "AGX source catalog"

[12]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/web/src/App.tsx "AGX web routes"

[13]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/web/src/pages/Monitoring.tsx "Monitoring page"

[14]: https://raw.githubusercontent.com/shadygad01/EGX-Genom/main/deploy/systemd/egx-collector.timer "Current collector timer"
