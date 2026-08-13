# Price-source research notes

Date: 2026-08-13

## Sources checked

- EGXLytics/EGXPY: public LinkedIn announcement says the project offered historical and intraday EGX data and links to `https://egxlytics.com/` and `https://egxlytics.github.io/egxpy/`. The linked GitHub Pages documentation currently returns 404, so no stable documented endpoint was verified.
- EGXLytics/Neuro Systems homepage: still advertises a Market Data API and links to the same broken GitHub Pages documentation; no public API endpoint or unauthenticated contract was verified.
- `rgf2004/egx-stock-api`: public Flask wrapper whose README says it uses `yfinance` and exposes `/EGX/ABUK`; it is not an independent market-data source and inherits Yahoo/terms and availability concerns, so it is not accepted as a direct source.
- `M-Abdelmegeed/EGX-Data-MCP-Server`: public MCP project uses `tradingview_ta` with TradingView's Egypt screener and EGX exchange. Existing EGX-Genom policy/docs classify TradingView as restricted for automated extraction/redistribution, so it is not accepted.
- `HussienElSawy/EGX.com-Scanner`: public project scrapes `https://www.egx.com.eg/en/investorstypepiechart.aspx` with requests/BeautifulSoup and proves an official EGX page can be automated, but that specific page contains investor-type tables, not stock OHLC prices.
- Official EGX pages: `https://www.egx.com.eg/en/CurrentIndexConstituntes.aspx?type=1&Nav=1` is extractable and provides current EGX30 constituents; `https://www.egx.com.eg/en/prices.aspx` and `InradayTradingStatistics.aspx` expose only page titles to the extraction layer in this environment, and the browser page rendered blank, so the price-table request/HTML contract is not yet verified here.

## Current conclusion

Do not add Yahoo/TradingView wrappers as new "free" sources. The compliant path still needs a directly verified official EGX price endpoint/page parser or a genuinely public source with a stable documented contract. The repository currently has a composite collector for Yahoo/StockAnalysis/Mubasher and documents those routes as blocked or unavailable in the sandbox.

- EGXBot/Borsa'gy AI daily report (`https://egxbot.com/en/market-report`) is publicly readable and reports an exchange-sourced session summary after the close, including EGX30/EGX70/EGX100 close/change/percent and breadth. It does not expose a documented individual-stock OHLC endpoint on the report page, so it is a candidate for index/breadth cross-checking, not yet an individual-stock price source.

## EGXBot individual-stock surface

The public page `https://egxbot.com/en/stocks` exposes a full table of individual EGX stocks with Code, Stock, Sector, Price, Change, and Rating. The page states that prices are from the Egyptian Exchange and may be delayed a few minutes. It covers symbols relevant to EGX30 (for example COMI, ETEL, ABUK, MFPC, TMGH, FWRY, EFIH, PHDC, etc.) and many EGX70 names. This is the first newly verified public individual-stock price surface found. It has no documented API contract yet, so the integration should use the public HTML table with conservative rate limits, provenance, and a staleness check, while treating the stated delay as part of the source metadata.
