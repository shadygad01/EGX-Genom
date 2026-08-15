# Decision Contract

The canonical production decision is the existing `PositionAwareDecision`, not a second object. It must contain the following fields or their existing nested equivalent:

| Group | Required content |
|---|---|
| Identity | ticker, as-of date, horizon, decision action |
| Position context | current weight, target weight, held/not-held state |
| Thesis | investment thesis and why-now explanation |
| Evidence | supporting refs, contradicting evidence, catalysts, monitoring events |
| Economics | opportunity score, expected return, expected risk, confidence |
| Risk controls | key risks, invalidation conditions, liquidity and country-risk overrides |
| Governance | abstention flag/reasons, publication status, model/policy version, provenance |
| Lifecycle | expected review date, later outcome and ledger reference when available |

The action vocabulary remains the six position-aware actions already implemented: `buy`, `increase_position`, `hold`, `reduce_position`, `exit`, and `no_action`. `no_action` is not a BUY substitute. An abstained unheld security is no action; an abstained held security remains hold unless a separate validated risk rule supports reduction or exit.

The contract must remain fail-closed. A missing field may be nullable only when the corresponding evidence is genuinely unavailable and the decision explains that gap. It must never be populated with an inferred value merely to satisfy the schema.
