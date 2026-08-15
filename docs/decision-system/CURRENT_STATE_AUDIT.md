# Current State Audit

## Executive finding

EGX-Genom is no longer a research-only dashboard. The production path currently has a canonical position-aware decision service, capital-allocation layer, provenance, publication gates, decision ledger, financial-statement coverage, and a live dashboard contract. The attached proposal is directionally correct, but much of its requested architecture already exists. Rebuilding it would add duplication and operational risk.

The remaining product gap is not a missing grand architecture. It is **decision-surface consistency and governance**: every production artifact must remain traceable from source to fact to evidence to decision, every decision must expose why/why-not/invalidation, and new research must not enter the core path without a declared consumer and validation status.

## Component inventory

| Component | Knows | Produces | Consumer | Decision influence | Status | Disposition |
|---|---|---|---|---|---|---|
| Source registry and acquisition intelligence | Source capability, legality, reliability, freshness, route | Ranked source decisions and provenance | Production collectors | Selects admissible evidence sources | Operational | Keep |
| Price composite | EGX price history and liquidity inputs | Price bars, adjusted series, coverage metrics | Readiness, technical, liquidity, ranking | Candidate eligibility and risk/execution | Operational | Keep |
| Financial collectors and provider | Reported statement line items and periods | Financial facts and coverage | Fair-value and investment readiness | Fundamental thesis and valuation gate | Operational | Keep |
| Macro collectors | FX, inflation, growth, rates and external context | Macro overlay and risk posture | Decision and allocation layers | Exposure dampening and country-risk context | Operational | Keep as secondary |
| News/events platform | Attributed events, dates, affected entities | Corporate events and event evidence | Catalyst/risk explanation and monitoring | Confirms, contradicts, or invalidates thesis | Operational but selective | Keep; add value gate |
| Research engines | Technical, market, pattern, event and financial signals | Findings and evidence refs | Recommendation and explanation | Horizon-specific evidence | Operational with unequal maturity | Govern by consumer |
| DecisionService | Recommendations, positions, risk overlays and constraints | PositionAwareDecision | Capital allocation and dashboard | Canonical action | Operational | Keep as canonical |
| CapitalAllocationEngine | Decisions, positions, budget and opportunity set | Relative queue, capital flows, opportunity cost | Dashboard and portfolio views | Chooses where capital goes | Operational | Keep |
| Decision ledger and calibration | Published decisions and later outcomes | Historical records and calibration summaries | Maturity, learning, audit | Evaluates policy quality, not live signal fabrication | Operational; data-maturity limited | Keep |
| Cross-stock exploratory network | Relationship signatures from market data | Exploratory graph artifacts | Research only | No automatic production signal | Isolated | Keep isolated |
| Dashboard | Canonical artifacts and explanations | Decision Center views | Human decision-maker | Presentation only; no independent truth | Operational | Keep; no client recomputation |

## What the attached proposal gets right

The proposal correctly prioritizes one coherent decision, explicit conflicts, fail-closed behavior, provenance, portfolio context, comparative opportunity, a decision lifecycle, and a learning loop. It also correctly rejects report volume, raw news volume, unsupported market-maker claims, and forced BUY outputs as success measures.

## What is already implemented

The position-aware contract already carries action, target/current weight, horizon, confidence, opportunity score, expected return/risk, thesis, risks, contradicting evidence, catalysts, monitoring events, review date, abstention reasons, explanation, and provenance. The capital-allocation layer already compares opportunities relative to one another and cash. The published production contract already verifies 101/101 readiness, unique ranks from 1 to 101, and live manifest publication.

## Material gaps

The highest-value remaining gaps are governance and observability rather than another decision engine. First, research modules need a machine-checkable declaration of question, consumer, evidence status, freshness, and failure mode. Second, event/news inputs need a formal decision-impact classification so context is not silently treated as evidence. Third, production audit documentation should make the canonical flow and dispositions explicit. Sector-relative evidence remains a valid future gap, but it must not be fabricated from an unverified taxonomy.

## Evidence boundary

Daily OHLCV can support behavioral and relative-strength signatures, but it cannot identify market makers, coordination, manipulation, absorption, or order-level intent. Such claims remain outside the production decision path unless quote/trade/order-level data is obtained and validated.
