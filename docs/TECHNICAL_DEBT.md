# Technical Debt Register

Known, deliberate debts — each with why it's acceptable now and what
triggers repayment. Anything not listed here and discovered later should
be added, not silently fixed or silently tolerated.

| # | Debt | Why acceptable now | Repayment trigger |
|---|------|--------------------|-------------------|
| 1 | `KnowledgeObject` inherits its `Hypothesis`'s id (Epoch I contract); the graph skips the resulting self-loop edge in pipeline projection. | Stable contract; ids stay traceable. | Any consumer needing hypothesis and knowledge as distinct graph nodes → introduce distinct knowledge ids in a 2.0 schema migration. |
| 2 | `ProvenanceRef.kind` is a free string informally synced with `graph.NodeType`; unrecognized kinds silently skip edge creation (documented in `edges_from_provenance`). | Every current kind is a NodeType member; skip-not-mislabel limits damage. | First bug traced to a typo'd kind → shared enum + conformance test. |
| 3 | JSON-file repositories are in-memory, single-writer, fully rewritten per `add()`. | Correct and fast at current scale; interface hides it. | Data volume or concurrent writers → database-backed `Repository[T]`. |
| 4 | Pairwise feature search is O(n²) in universe size (435 pairs at EGX30). | Trivial at 30 tickers. | Universe expansion toward all listed companies → candidate pre-filtering/caching. |
| 5 | `NaiveDirectionalBacktester` ignores transaction costs and sizing (stated in its own notes). | Honest gate on directional evidence; costs need a portfolio-level harness. | Portfolio optimizer work (post-1.0) → cost-aware backtest replaces the gate threshold defaults. |
| 6 | Conflict-policy confidence constants (corroboration boost 0.5, dispute penalty 0.2) and ontology impact-horizon mapping are defensible defaults, not calibrated. | No multi-source or long-horizon real data exists to calibrate against. | First real second data source / first year of real events → calibration study. |
| 7 | `PeerValidatorReviewer` replication uses the same snapshot (perturbed methodology only). | The only data that exists is one snapshot; perturbation is the honest replication available. | Real multi-day history → replicate on disjoint periods. |
| 8 | Pipeline `PipelineConfig.extra_agents` field is currently unused. | Harmless config surface. | Next pipeline change → remove or wire. |
| 9 | `api/`/`web/` expose only knowledge objects; sessions/genes/papers/portfolios have no HTTP surface. | Epochs II+ were explicitly scoped Python-core-only. | First presentation-layer requirement → extend the read-only API + regenerate contracts. |
| 10 | Monkey-test note: `learning` monitor uses each knowledge object's *primary* asset only for realized performance. | Single-asset attribution is the defensible v1; pair claims are directional on the primary. | Portfolio-level attribution work → per-claim realized-return definitions. |
