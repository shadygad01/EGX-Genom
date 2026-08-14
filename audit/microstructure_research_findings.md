# EGX Microstructure Research — Initial Findings

## Primary paper

Rushdy and Samak, “Examining Market Quality on the Egyptian Exchange (EGX): An Intraday Liquidity Analysis,” Journal of Risk and Financial Management, 18(1), 32 (2025), DOI: https://doi.org/10.3390/jrfm18010032.

The paper states that it reconstructs five-minute limit order books from transaction and order-file data covering EGX constituents. It studies bid–ask spread, depth, immediacy, tick size, interval-of-day effects, and day-of-week effects. The abstract reports an inverted J-shaped spread pattern, a U-shaped total-depth pattern, a J-shaped market-depth pattern, and lower liquidity on Sundays with higher trading activity on Thursdays.

The article lists Ahmed Rushdy as corresponding author at the Faculty of Economics and Political Sciences, Cairo University, with `ahmed_rushdy2016@feps.edu.eg` and ORCID `0000-0002-9718-148X`. Nagwa Samak is listed with Cairo University and Galala University, with `nagwa.samak@gu.edu.eg` and ORCID `0000-0003-3259-1848`.

The paper’s relevant methodological scope supports a separate microstructure/Execution Overlay, not a Fair Value model. Its measurable dimensions include tightness, immediacy, depth, breadth, and resiliency. The user-supplied hypotheses are therefore directionally relevant, but raw order/transaction data availability must be verified before implementation.

## Initial design conclusion

Do not mix microstructure features into Fair Value. If validated data becomes available, expose them as liquidity, execution-risk, price-impact, and short-horizon flow signals. Do not infer participant identity or intent from order behavior without direct evidence.

## Author/contact verification

The official Galala University page lists Nagwa Samak as Dean of the Faculty of Administrative Science and Professor of Economics, gives `nagwa.samak@GU.edu.eg`, and links to ResearchGate and Google Scholar. The MDPI article lists her Cairo University and Galala University affiliations.

The MDPI page lists Ahmed Rushdy as corresponding author at Cairo University with `ahmed_rushdy2016@feps.edu.eg` and ORCID `0000-0002-9718-148X`. The official paper page is the strongest verified source for this contact; a separate university profile still requires confirmation.

## Data availability verification

The full MDPI article states that the study used three datasets supplied by the EGX Information Center: Trade File, Transaction File, and Order File, for 123 trading days from August 2017 to January 2018 covering EGX30 constituents. It describes approximately 18,324 trade observations, 1.74 million transactions, 9.46 million order observations, 2.8 million orders, and a reconstructed five-minute quote file.

The paper's explicit Data Availability Statement says: "Dataset available on request from the authors." No public raw-data download or repository link was identified in the article text. This makes direct author contact the strongest free route currently verified.

## EGX official access check

The official EGX intraday-statistics page exposes current intraday and total value/volume statistics by listed company. It is a public summary page, not evidence of public historical Order File, Transaction File, or Market-by-Order access.

The referenced article identifies its source as the EGX Information Center, but the official public pages reviewed so far do not document a free research-access application route for the raw historical files. This remains an open verification item rather than a claim that no route exists.

## Newer research hypotheses

A 2025 open-access Quantitative Finance study, “Deep limit order book forecasting: a microstructural guide,” emphasizes that predictive accuracy alone is not enough; a practical metric should estimate the probability of executing a correct transaction. It also links model performance to tick size and liquidity characteristics. This creates a stronger candidate hypothesis for EGX: **predictive signal quality should be evaluated by executable transaction probability and net-of-cost return, not classification accuracy alone**.

A 2025 Federal Reserve note argues that large directional order flow can amplify price moves when liquidity supply is impaired. The stronger hypothesis for EGX is therefore an interaction: **order-flow imbalance has greater price impact when market depth is low and volatility is high**. This is more useful than testing imbalance alone.

The article’s hypotheses should remain separate from Fair Value. Candidate overlay variables are: executable-signal probability, order-flow imbalance × depth stress, liquidity vacuum/replenishment, price-impact asymmetry, and event-conditioned resilience.

## Open code and data access

The official LOBFrame GitHub repository is open source and provides preprocessing, training, evaluation, backtesting, and post-trading analysis for LOBSTER-format data. It explicitly requires the user to supply raw LOBSTER data; it does not provide EGX data. Its license is CC BY-NC-ND 4.0, so it should be used as a reference or carefully reviewed component rather than copied into production without license review.

The ICE EGX catalog confirms that Market-by-Order, Level 2 depth, tick-by-tick history, and normalized timestamps exist as commercial data products. This verifies technical feasibility, but it is not a free research-access route and is not recommended as the project’s acquisition path.

## Additional hypotheses from newer/open research

The 2025 arXiv paper “Order Book Filtration and Directional Signal Extraction at High Frequency” proposes filtering transient order-book events by order lifetime, update count, and inter-update delay before recomputing OBI. It reports that filtering improves correlation and regime diagnostics but may provide limited causal gains; trade-event OBI can have stronger causal alignment. A suitable EGX test is therefore: **filtered OBI should be compared with raw OBI using both predictive and causal diagnostics, not correlation alone**.

The 2021 paper “Tick Size and Price Reversal after Order Imbalance” provides a regime hypothesis: OIB-reversal depends on tick-size binding frequency, spread, liquidity, depth, trade frequency, and volatility. This is especially relevant to EGX because the 2025 EGX paper documents a unified EGP 0.01 minimum price variation during its sample period. The EGX test should distinguish a tick-size-censoring regime from an augmentation regime rather than assume one universal imbalance effect.

These are candidates for later testing only if raw order and transaction data are obtained. No current EGX daily-price data can validly test them.

## Official EGX contact and usage constraints

The official EGX contact page directs queries to `info@egx.com.eg` and hotline 15221. The reviewed Market Operations Division forms page contains operational forms, not a documented historical market-data research request form.

The EGX disclaimer states that website materials are EGX property, permits viewing/printing for personal noncommercial use, and prohibits copying, storing in an electronic retrieval system, reproducing, distributing, or creating derivative works without written permission. It directs permission requests to `info@egx.com.eg`. Any local storage or computational use of EGX-provided raw files should therefore be covered by written permission or a research-use agreement.
