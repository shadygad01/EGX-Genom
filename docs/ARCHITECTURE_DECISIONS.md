# Architecture Decision Record

Compact ledger of load-bearing decisions and their reasoning. Full context
for the early ones lives in `docs/ARCHITECTURE_AUDIT.md` (Epoch I) and
`docs/EPOCH_II_DESIGN.md`; entries here are the ongoing record.

| # | Decision | Rationale |
|---|----------|-----------|
| AD-01 | One generic versioned `Repository[T]` under every store; JSON-file backed until scale demands otherwise. | Principle 5 uniformly; backend swap is one new implementation, not N rewrites. |
| AD-02 | `DatasetSnapshot` is content-hashed and immutable; agents/experiments/validators never touch a live `DataProvider`. | Reproducibility and look-ahead-bias prevention by construction, not convention. |
| AD-03 | Hypothesis validation is a configurable `GateSpec` pipeline, strictly ordered at runtime. | New gates/tracks are data changes; skipping is impossible. |
| AD-04 | `KnowledgeStore.promote()` depends on a structural `PromotableEvidence` protocol, signature frozen since Epoch I; board/causal gate run *before* it. | Decoupling + existing-caller stability; review composition stays outside the store. |
| AD-05 | Every return calculation routes through `data.adjustments` (split/dividend backward adjustment; dividend factor from the last cum-dividend close). | A corporate action must never masquerade as a return; the ex-date-close variant was a real caught bug. |
| AD-06 | Event identity = content fingerprint excluding source; `EventPlatform.register()` is the sole event write path; corrections supersede, never edit. | Dedup and cross-source corroboration require stable identity; disputes are surfaced, not resolved by guessing. |
| AD-07 | The Knowledge Graph is a derived view (provenance + event projection), never hand-maintained. | A second source of truth would drift; a view cannot. |
| AD-08 | Genes are immutable; `mutate()` = single-parent refinement, `merge()` = multi-parent synthesis; parents marked REPLACED with forward links. | "New discoveries create new genes"; the multi-parent question resolved explicitly rather than left ambiguous. |
| AD-09 | The hypothesis claim statistic is defined once (`hypotheses/statistic.py`), dispatched by asset arity; unknown arities raise. | Experiments, backtester, stress tester, and adversary must judge the same number; no silent fallbacks. |
| AD-10 | Anything not honestly implementable raises `NotImplementedError` / reports `attempted=False`; boards/batches skip-not-fake, and zero working checks can never approve. | The charter's anti-fabrication principles, enforced in code paths rather than documentation. |
| AD-11 | Pipeline confidence is derived: `min(1 − bootstrap_p, 0.9)` then adversarially adjusted; expected return/risk are measured historical moments, labeled as such. | Confidence and expectations must trace to measurements; the cap encodes that one window never justifies certainty. |
| AD-12 | Prediction v1 (`KnowledgeWeightedHorizonModel`) only aggregates promoted knowledge; no knowledge → no prediction; aggregate confidence ≤ the strongest input. | "No recommendation without evidence" at the model layer; combining evidence must not fabricate certainty. Trained models wait for real data depth. |
| AD-13 | Retirement policy v1: majority sign-disagreement between realized and expected returns over ≥N monitored records, with audited reasons. | Mechanical, deterministic, explainable; thresholds are calibration targets once real data exists (TD-6). |
| AD-14 | Runtime engine isolates per-day failures into a persistent run ledger and records non-trading days explicitly; OS scheduling is deployment config. | A bad day must not halt the organization; a replayed range must reproduce a complete, identical ledger. |
| AD-15 | Movable EGX holidays are an explicit per-year table, not a lunar-calendar algorithm. | Approximated dates would be fabricated calendar data; observed closures follow official announcements anyway. |
| AD-16 | Every data source is a declarative `SourceSpec` in `sources.SourceRegistry`, gated by an explicit `status` (IMPLEMENTED/PLANNED/NEEDS_KEY/TOS_REVIEW/DISABLED); `Collector.__init__` refuses to construct against any non-IMPLEMENTED source. | Independent replaceability and honest cataloguing per source, enforced in code so an untested/unauthorized/ToS-ambiguous source can't be silently collected by a future contributor. |
| AD-17 | `collectors.service.CollectionService` withholds (never materializes) any batch whose mechanically-scored confidence falls below a floor; derived events route through the existing `EventPlatform.register()`, never a new write path. | "No downstream system may ignore data quality" and "no source is authoritative by itself" enforced structurally, reusing the Event Platform's identity/dedup/conflict machinery rather than duplicating it. |
