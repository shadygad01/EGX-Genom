# Live EGX30 refresh — 2026-08-13

A live production-mode run completed successfully at 2026-08-13, using the project's free-source collector chain. The official EGX prices page timed out twice, and the pipeline recorded that warning honestly; the composite public price path still produced complete coverage for all 101 EGX30/EGX70 universe tickers.

The live bundle is as of 2026-08-13. Ninety-nine tickers have their latest bar dated 2026-08-12 and two have a bar dated 2026-08-13. All 31 rows in the current EGX30 seed are matched and have latest bars dated 2026-08-12. The bundle passed `validate-dashboard` with 38 artifacts, 101 readiness rows, and two quantitative research candidates.

The six-month-low rule is current price within 8% of the lowest observed low in the last 183 days. One EGX30 ticker triggered it:

| Ticker | Latest bar | Current | Six-month low | Distance above low | Observations |
| --- | --- | ---: | ---: | ---: | ---: |
| EAST | 2026-08-12 | 36.30 | 34.83 | 4.22% | 119 |

The local dashboard was pointed at the live bundle and visually reviewed. The Investment Cases page shows the latest prices and six-month-low column, while the existing browser-notification logic remains enabled. The current replay/live dashboard banner correctly says the local bundle is not canonical production-generated, because it was generated manually outside the GitHub Actions publication workflow.
