# Final public dashboard check

- Public URL: https://shadygad01.github.io/EGX-Genom/
- Investment Cases URL: https://shadygad01.github.io/EGX-Genom/cases
- Deploy run 31752410478 for commit 98e9630: success.
- CI run 31753273745 for commit 61daafb: success. Python research engine passed ruff, Truth Preservation, pytest, contracts freshness, and artifact provenance; TypeScript/API/web job also passed.
- Public artifact HTTP checks after the successful deploy: `macro_snapshot.json` 200 (957 bytes), `research_candidates.json` 200 (3 bytes, `[]`), `market_state.json` 200, `universe.json` 200, `recommendations.json` 200, and `knowledge.json` 200.
- CIO Desk displays real macro values from Yahoo Finance and World Bank, with last snapshot date 2026-08-06.
- CIO Desk and Investment Cases display a truthful replay provenance warning: the bundle is not a fresh canonical live run. The previous missing-manifest warning is resolved.
- Investment Cases displays the Quantitative research candidates section. The code-push snapshot is honestly empty because no historical candidate artifact was available; the next scheduled live run is responsible for generating fresh candidates.
- The Investment Cases board still shows executable-looking cases such as EXPA and ARCC separately from the research-only table, with valuation models and six-month price-low coverage visible.
