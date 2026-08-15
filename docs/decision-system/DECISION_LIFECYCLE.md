# Decision Lifecycle

```text
OBSERVE → CANDIDATE → WATCH/NO_ACTION → BUY/INCREASE → HOLD → REDUCE → EXIT → CLOSED → OUTCOME → POST-MORTEM
```

A transition requires a timestamp, previous action, new action, evidence references, decision/policy version, confidence, and a reason. A security may remain in no action indefinitely when evidence is insufficient. A held security may remain hold when the system cannot refresh a non-critical input; a hard risk rule may still produce reduce or exit when documented conditions are met.

The append-only decision ledger is the historical memory. It records the published decision and later outcome separately. Learning is controlled: one outcome cannot modify policy, and calibration is reported only when the ledger has enough evaluated observations. Until then, the system reports maturity limitations rather than implying predictive validation.
