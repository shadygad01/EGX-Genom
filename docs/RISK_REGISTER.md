# Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R-01 | Conclusions drawn from placeholder data being mistaken for real research output. | High (until a vendor is licensed) | Critical | Placeholder status stamped in code/docs at every placeholder (universe, sectors, holidays, mock CSVs); `PHASE_STATUS.md` states it as the gating item; no external publication of outputs before real data. |
| R-02 | Statistical gates passing spurious relationships at current tiny sample sizes. | High | High | Small-sample adversarial attack + sample-size reviewer thresholds are strict by default (permissive settings exist only inside tests, clearly labeled); confidence capped at 0.9 and adversarially reduced. |
| R-03 | Threshold/constant miscalibration (conflict policy, retirement policy, ontology horizons). | Medium | Medium | All constants centralized, documented as uncalibrated defaults (TD-6), deterministic → recalibration is a config change with replayable comparison. |
| R-04 | JSON store corruption or loss. | Low | High | Integrity-checked backup/verify/restore (refuses partial restores); append-only revisions make partial recovery meaningful. |
| R-05 | Silent divergence between Python schemas and TS mirrors. | Low | Medium | `contracts/` drift check fails CI. |
| R-06 | Vendor lock-in / feed outage once a real provider is integrated. | Medium | Medium | `FallbackDataProvider` composition seam; provider-shape assumptions confined to `data/`. |
| R-07 | Look-ahead bias reintroduced by a future contributor bypassing snapshots. | Low | Critical | Snapshot-only consumption enforced in interfaces; adversarial LookAheadBias attack audits snapshots independently (defense in depth); CLAUDE.md invariants. |
| R-08 | Knowledge base ossifying (nothing retired, stale knowledge driving recommendations). | Medium | High | ContinuousLearningMonitor wired into operations (CLI/runtime); retirement is mechanical, not discretionary; monitoring status transitions are automatic on first evaluation. |
| R-09 | Single-maintainer bus factor on architecture intent. | Medium | Medium | CLAUDE.md + ADR + design docs kept synchronized with code by convention; every invariant also enforced by at least one test. |
| R-10 | Regulatory/legal constraints on investment research publication in Egypt. | Unknown | High | Flagged as a business/legal question for the user before any external distribution of recommendations (out of engineering scope). |
