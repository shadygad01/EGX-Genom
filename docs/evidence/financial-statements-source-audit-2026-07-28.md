# EGX financial-statements source audit — 2026-07-28

## Scope

This audit tested financial-statement surfaces specifically. It does not reuse
the earlier price-data verdict as a proxy for fundamentals coverage. The live
sample deliberately included a bank (`COMI`) and a non-bank industrial issuer
(`ABUK`).

## Verified live results

| Source | COMI | ABUK | Data observed | Automation verdict |
|---|---|---|---|---|
| Investing.com | Yes | Yes | Annual and quarterly financial pages; COMI income statement exposed periods through 2025 and structured line-item tables, with separate balance-sheet and cash-flow pages | Coverage is real. Do not integrate yet: terms/licensing and an approved machine-readable route must be established first. |
| TradingView | Yes | Yes | Yearly/quarterly financials and the three core statements are advertised on both EGX symbol surfaces | Coverage is real, but automated collection/non-display processing is explicitly prohibited by current policy without permission. Display availability is not integration permission. |
| Mubasher | Yes | Yes | Dedicated `/financial-statements` pages, financial ratios, EGX announcements, and linked financial-statement PDFs on the static Mubasher document hosts | Strong candidate for discovery of primary EGX disclosure documents. The rendered statement page is client-driven; identify the lawful document/API route and verify robots/terms before implementing collection. |
| MarketScreener | Yes | Not yet fully table-verified | COMI annual/quarterly/half-year/YTD/LTM income statement, balance sheet and cash flow, with history through 2025 | Coverage is real. Terms/licensing and a stable permitted export/API route remain unverified. |

## Concrete evidence

- Investing COMI income statement: `https://www.investing.com/equities/com-intl-bk-income-statement`
- Investing COMI summary: `https://www.investing.com/equities/com-intl-bk-financial-summary`
- Investing ABUK summary: `https://ca.investing.com/equities/abou-kir-fertilizers-financial-summary`
- TradingView COMI: `https://www.tradingview.com/symbols/EGX-COMI/`
- TradingView ABUK: `https://www.tradingview.com/symbols/EGX-ABUK/`
- Mubasher COMI statements: `https://english.mubasher.info/markets/EGX/stocks/COMI/financial-statements`
- Mubasher ABUK statements: `https://english.mubasher.info/markets/EGX/stocks/ABUK/financial-statements/`
- MarketScreener COMI balance sheet: `https://www.marketscreener.com/quote/stock/COMMERCIAL-INTERNATIONAL--6491751/finances-balance-sheet/`

## Corrected conclusion

The former statement that real per-company financial statements had not been
found was not supported by a financials-specific source audit. Multiple sources
do cover Egyptian issuers. The remaining problem is narrower: establish a
permitted, stable acquisition path and reconcile the resulting figures against
primary issuer/EGX filings before feeding them to research agents.

## Implemented primary-issuer paths

The implementation gate is now cleared for two representative issuers without
using an aggregator or redistributing the source document:

| Source | Ticker | Live result | Canonical output |
|---|---|---|---|
| Telecom Egypt Investor Relations | ETEL | Q1 2026 release discovered from the issuer homepage; 8 explicit financial and decision metrics | EGP revenue, EBITDA, net income, FCFF, YoY growth, net margin, and net-debt/EBITDA |
| Orascom Construction Investor Relations | ORAS | Q1 2026 result article discovered from the issuer updates archive; 3 explicit headline values | USD revenue, EBITDA, and attributable net income |

Both collectors retain the article URL, retrieval timestamp, content hash,
collector/version, and per-value provenance in the existing raw-document and
provenance repositories. They fail closed when the labelled result shape or
reporting period is absent. A live cumulative run on 2026-07-28 selected both
sources, produced 11 canonical rows, reported no failures, and scored each
batch at 0.97 confidence.

## Next implementation gate

1. Add per-issuer primary IR configurations before considering a licensed
   aggregator route for issuers without a stable public IR surface.
2. Record period, consolidation scope, currency, scale, language, and document
   hash for every filing.
3. Build a source-specific parser only after two layouts from the same issuer
   have been reconciled manually; reject ambiguous line items rather than infer.
4. Use aggregator tables only for coverage comparison and reconciliation until
   explicit automated-use permission or a licensed API is confirmed.

## EGID official service audit

EGID's public issuer-IR application was inspected on 2026-07-28. Its Angular
client uses the following official endpoints:

- `GET /api/identity/Settings/getCompanySettings/{appKey}` returns a JWT with
  role `Feed:Get` and an explicit `company` claim.
- `POST /api/Feed/getnewsbysearch` accepts the issuer ISIN, date range and EGX
  financial-statement section identifiers and returns disclosure metadata plus
  official EGX PDF attachment paths.

The route was verified against VERT's own public page and returned its 2021-2026
financial-result filings. A technical probe also showed that the backend accepts
COMI, ABUK, ETEL and EKHO ISINs while presenting a JWT whose company claim belongs
to VERT. That behavior is not treated as permission: it may be a tenant-isolation
defect. The repository therefore catalogs `egid_financial_filings` as
`TOS_REVIEW`/`BLOCKED`, and must not automate cross-company requests until EGID
provides a market-wide credential or written public bulk-use terms.

This audit materially narrows the remaining external dependency: EGID already
has a centralized official filing index keyed by the ISINs present in the AGX
universe files, but lawful market-wide API authorization and reliable access to
the protected EGX PDF host are still required before extraction can be run for
all 101 constituents.
