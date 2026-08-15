# Architecture Options and Adversarial Debate

## Position 1: Research-centric with a stronger integrator

This option keeps the current research engines as the organizing principle and adds a stronger final integrator. It is familiar and preserves maximum research flexibility. It also minimizes migration risk because collectors, findings, and reports remain first-class.

Its strongest objection is that it preserves the information-warehouse gravity identified in the attached proposal. Research modules can continue to grow without a measurable decision consumer. The hidden assumption is that a better final integrator can compensate for weak upstream ownership. The failure mode is a larger report system with a final score or vote that remains hard to audit. It loses because the repository already contains a working decision service and capital-allocation layer; making research primary would move the architecture backward.

## Position 2: Decision-first evidence architecture

This option treats the canonical decision as the product primitive. Collectors produce facts; research engines produce bounded evidence; the DecisionService produces one position-aware decision; allocation and dashboard consume that decision. Evidence is gated, provenance-preserving, horizon-specific, and never averaged blindly. News, cross-stock, and execution research remain sensors with explicit downstream roles.

The strongest objection is that some research questions will not fit the immediate decision contract and could be prematurely demoted. The hidden assumption is that decision consumers can be declared clearly enough to govern research. The failure mode is over-gating useful exploratory research. The countermeasure is to keep exploratory work outside the production path with an explicit research-only status and promotion criteria. This option wins because it matches the code that is already operational and adds governance rather than another layer.

## Position 3: Portfolio/position-centric architecture

This option makes current positions, capital budget, concentration, and alternatives the primary organizing axis. Every security analysis exists only to decide whether to enter, add, hold, reduce, exit, or wait for cash. It is closest to actual fund operations and naturally supports opportunity cost.

Its strongest objection is that a security must sometimes be evaluated before a portfolio exists, and research must remain useful for candidate generation. The hidden assumption is that positions and capital constraints are always available. The failure mode is a portfolio screen that hides market-wide knowledge and makes pre-trade research unnecessarily dependent on user holdings. This option is valuable as the allocation layer, but not as the entire system root.

## Decision

Select **Decision-first evidence architecture with a portfolio-aware allocation layer**. It preserves the existing position-aware DecisionService and CapitalAllocationEngine, while making the source-to-decision contract explicit and machine-checkable. Research remains modular, but no module enters the production decision path without a declared question, consumer, uncertainty, freshness, and validation status.

## What is rejected

The project should reject a new weighted 31-row evidence score, a second mandatory-gate system, automatic news-to-BUY conversion, market-maker or manipulation claims from OHLCV, a separate speculative score blended into the investment horizon, and a dashboard that recomputes truth in the browser. These ideas add unvalidated assumptions or duplicate existing gates and services.
