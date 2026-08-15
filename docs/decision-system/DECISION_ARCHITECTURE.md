# Decision Architecture

## Canonical path

```text
SOURCE → RAW FACT → NORMALIZED FACT → FEATURE/EVENT → EVIDENCE → HORIZON RECOMMENDATION → POSITION-AWARE DECISION → CAPITAL ALLOCATION → MONITORING → OUTCOME
```

The path is intentionally one-directional. A dashboard page, report, or research notebook may display an artifact, but it must not create a second version of decision truth.

## Responsibility boundaries

| Layer | Primary question | Allowed output | Must not do |
|---|---|---|---|
| Market posture | What environment are we operating in? | Macro/regime context and exposure overlay | Independently force a ticker BUY |
| Security evidence | What changed for this security? | Validated facts, features, events, and conflicts | Convert raw data directly into action |
| Thesis/recommendation | Is the investment thesis supported for the horizon? | HorizonDecision with evidence, risk, return, confidence, and abstention | Ignore publication gates or fabricate missing data |
| Position-aware decision | What should be done given current holdings? | PositionAwareDecision | Recompute facts or create a second score |
| Allocation | Where should scarce capital go? | Relative queue, target weights, capital flows, cash waiting | Override hard publication or integrity gates |
| Execution | How could an approved decision be entered? | Entry conditions, liquidity constraints, invalidation and monitoring | Change the investment thesis silently |
| Learning | What happened after publication? | Outcome, calibration, attribution and post-mortem | Retrain or modify policy from one outcome |

## Hard controls

The existing readiness and publication gates remain the single gate system. Liquidity and country-crisis overlays remain hard constraints where their documented conditions are met. Missing, stale, contradictory, or legally unusable evidence produces abstention or no action; it never becomes a positive proxy.

## Research boundaries

Fundamental evidence informs thesis and valuation. Technical and SMC evidence informs execution and timing unless validated otherwise. News and corporate events can confirm, contradict, or invalidate a thesis but do not independently create a BUY. Cross-stock analysis can inform relative opportunity and regime context but remains research-only until its validation criteria are met. Daily data cannot support market-maker identity or manipulation claims.
