# Phase 1 — Free-source audit

## Date
2026-08-13.

## Initial source findings

The Egyptian Exchange official homepage states that it publishes stocks, bonds, securities, EGX indices, trading/listing rules, and related market data: https://www.egx.com.eg/en/homepage.aspx.

The official EGX disclosure reports page is available at https://www.egx.com.eg/en/Disclosure_Reports.aspx and is the primary route for company announcements and disclosure evidence.

The Central Bank of Egypt provides official inflation statistics at https://www.cbe.org.eg/en/economic-research/statistics/inflation-rates and publishes official EGP exchange-rate information through its website.

CAPMAS provides official CPI metadata and consumer-price datasets through its census information portal: https://censusinfo.capmas.gov.eg/Metadata-en-v4.2/index.php/catalog/CPI.

## Design implications

The refactor must distinguish primary official data from fallback web sources. EGX should be the primary source for market prices, index membership snapshots, corporate disclosures, and trading calendars. CBE and CAPMAS should be primary sources for FX, inflation, monetary-policy and macro series where available. Any secondary source must carry source, retrieval timestamp, as-of date, and confidence metadata, and must not silently replace a missing official value.

The dashboard must expose data freshness and coverage per ticker. A price being current does not imply that a fair value is decision-ready; financial-period coverage, model count, macro coverage, FX coverage, disclosure freshness, liquidity, and evidence quality need separate gates.

## References

[1] [The Egyptian Exchange — Home Page](https://www.egx.com.eg/en/homepage.aspx)

[2] [The Egyptian Exchange — Disclosure Reports](https://www.egx.com.eg/en/Disclosure_Reports.aspx)

[3] [Central Bank of Egypt — Inflation Rates](https://www.cbe.org.eg/en/economic-research/statistics/inflation-rates)

[4] [CAPMAS — CPI Metadata](https://censusinfo.capmas.gov.eg/Metadata-en-v4.2/index.php/catalog/CPI)
