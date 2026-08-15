# Data to Decision Flow

Every production input must be traceable through the following chain:

| Stage | Required record | Integrity requirement |
|---|---|---|
| Source | Source id, access status, terms, collection timestamp | Source must be admissible and routed through the registry |
| Raw fact | Raw document or response reference | Preserve original content and URL |
| Normalized fact | Ticker, period, unit, currency, event time | No inferred missing values; unit and period are explicit |
| Feature/event | Calculation or classification and inputs | Formula/version and look-ahead boundary are recorded |
| Evidence | Horizon, direction, reliability, freshness, conflict status | Evidence must have a downstream consumer |
| Recommendation | HorizonDecision, thesis, expected return/risk, confidence | Existing readiness/publication gates apply |
| Decision | PositionAwareDecision and provenance | One canonical action per ticker/horizon |
| Allocation | Target weight, opportunity cost, capital source/destination | Relative pass cannot manufacture eligibility |
| Outcome | Later realized result and evaluation window | Append-only ledger; no retroactive decision edits |

The flow is considered failed if any stage loses provenance, changes a historical period without a version, or treats a zero-yield/unknown source as positive evidence.
