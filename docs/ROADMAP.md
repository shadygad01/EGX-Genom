# Roadmap

Current engineering state: all 18 systems architecturally complete and
tested except the business-blocked remainder of 18 (see
`docs/PHASE_STATUS.md` for per-system detail). The platform runs
end-to-end daily research cycles on placeholder data.

## Milestone: Production 1.0 (blocked on business decisions)

Required user/business inputs, in priority order:

1. **EGX market data vendor selection** (the gating decision). Candidates
   to evaluate on cost/coverage/latency/licensing: EGX official feeds,
   Mubasher, Refinitiv/LSEG, Bloomberg. Engineering integration after the
   decision: one `DataProvider` implementation + `FallbackDataProvider`
   configuration + re-run of `data.quality` calibration. Estimated
   engineering: small — the seam exists.
2. **Deployment target** (cloud provider + payment), which unlocks:
   secrets management, managed scheduling of `RuntimeEngine`, monitoring/
   alerting, API authentication context, backup storage/retention.
3. **Authoritative EGX trading calendar + universe/sector membership
   feeds** (replace the placeholder tables).

## Post-1.0 engineering roadmap (unblocked by real data accumulating)

- Trained per-horizon statistical models (replacing/augmenting the
  knowledge-weighted v1) once years of real history exist; the
  `HorizonModel` contract and model versioning are ready.
- Covariance-based portfolio optimization replacing capped proportional
  scoring; cost-aware portfolio-level backtesting harness.
- Remaining scientist agents as their feeds arrive: NewsIntelligence
  (NLP), FinancialPerformance (fundamentals), HistoricalPatterns
  (long-history analogs) — plus the HistoricalReviewer and the three
  remaining adversarial attacks (overfitting harness, regime labels,
  live-degradation comparison).
- Monte Carlo experiment once a market simulator design is chosen.
- Database-backed `Repository[T]` implementation when JSON stores hit
  scale limits; dedicated graph store behind the same interface.
- Full TS codegen for `contracts/` when the API surface grows.
