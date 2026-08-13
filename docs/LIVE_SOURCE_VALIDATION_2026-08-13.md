# Live source validation — 13 August 2026

## Executive result

A fresh live production run was executed after the source-routing refactor. It completed with `partial` status in 1,962.11 seconds because the optional GDELT discovery request returned HTTP 429. The core decision path succeeded: price data, disclosures, financial statements, investor relations, news, macroeconomic data, index membership, and sector membership all had successful selected strategies.

| Check | Result |
|---|---:|
| EGX30/EGX70 universe | 101 securities |
| Securities with a current price | 101 |
| Price observations | 11,585 composite records |
| Latest price dates | 99 on 2026-08-12; 2 on 2026-08-13 |
| Sources with produced records | 16 of 52 catalogued rows |
| Sources reaching decision path | 16 |
| Corroborated sources | 1, the composite price source |
| Source failures | 1, GDELT HTTP 429 |
| Source unavailable/retired/not eligible | 28 |
| Fair values available | 4 |
| Executable decisions | 0 |
| Quantitative watchlist candidates | 2: EXPA and ARCC |

## Active sources

The following sources produced records and reached a downstream consumer during the run: the Yahoo/StockAnalysis/Mubasher composite price provider, EGX universe seed, EGX disclosures, Enterprise Press, Al Borsa, Masrawy Economy, Amwal Al Ghad, World Bank Open Data, UN SDG Data, CAPMAS, Egypt NSDP, EGXpilot fundamentals, Chief Capital financials, Orascom Construction IR, Rameda IR, and TMG Holding IR.

The active macro pool is intentionally limited to World Bank, UN Data, CAPMAS, and Egypt NSDP. These are free public sources with real live records in the run. A source is not considered active merely because it has a collector class or a catalog entry.

## Removed from active routing

Stooq and FRED are now disabled/retired in the catalog. Stooq's CSV path is blocked by its robots policy. FRED's live CSV endpoint timed out repeatedly and also failed a fresh direct probe on this date. Their parsers remain unit-tested against recorded wire-format fixtures, but they cannot affect the production decision.

The official EGX market-watch collector remains an explicit standby fallback because the official endpoint did not produce a live table in this environment. GDELT remains optional discovery-only; the 429 response did not block primary news sources or the decision path.

## Decision interpretation

All 101 securities have current prices, but only four have a multi-model fair value. The engine therefore issued no executable Buy/Hold decision. EXPA and ARCC remain quantitative watchlist candidates, not execution recommendations, because the investment-readiness gates require stronger model evidence and complete macro/event coverage.

The Dashboard's Source Intelligence page now displays only operational evidence rows in the CIO workspace and shows `Sources collected`, `Reached decision path`, `Corroborated`, `Failed`, and `Unavailable` counters. Planned or unavailable placeholders remain in raw provenance artifacts for auditability but cannot appear as live decision inputs.

## References

[1]: https://api.worldbank.org/v2/country/EGY/indicator/FP.CPI.TOTL.ZG?format=json&per_page=5 "World Bank Open Data — Egypt inflation indicator"
[2]: https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data?indicator=8.1.1&areaCode=818 "United Nations SDG API — Egypt indicator data"
[3]: https://www.capmas.gov.eg/Pages/IndicatorsPage.aspx?page_id=6131 "CAPMAS — public indicators"
[4]: https://www.egx.com.eg/en/Disclaimer.aspx "Egyptian Exchange — public data disclaimer"
