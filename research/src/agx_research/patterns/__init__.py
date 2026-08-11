"""EGX30 Autonomous Pattern Discovery Engine.

Searches point-in-time-safe market/company/macro data for repeatable
relationships with future outcomes, then validates or rejects each one
with out-of-sample statistics -- never assumes a relationship exists, and
a run producing zero validated patterns is a legitimate, honest result
(see `docs/PATTERN_DISCOVERY_REPORT.md`).

Deliberately separate from `agents.historical_patterns.HistoricalPatternsAgent`:
that agent does single-ticker nearest-neighbor analog matching and feeds
one `ResearchFinding` into the normal hypothesis/knowledge pipeline. This
package is the broader, systematic search — multi-feature/cross-sectional/
regime-conditioned candidate generation, purged walk-forward validation,
multiple-testing control, a persistent lifecycle registry, live activation,
and decay monitoring — and persists its own `Pattern` entities rather than
routing through `Hypothesis`/`KnowledgeObject`. It reuses rather than
duplicates: `market_memory.MarketMemory.reconstruct()` for point-in-time
state, `data.adjustments` for split/dividend-adjusted returns,
`storage.JsonFileRepository` for persistence, `market_memory.regime` for
market regime, and `data.point_in_time.is_knowable` for macro publication
lag.

See `docs/PATTERN_DISCOVERY_DATA_AUDIT.md` for exactly what data this can
run against today, and its honest conclusion: real multi-year EGX price
history does not exist in this repository yet, so a run against current
data is expected to discover and validate zero patterns. The pipeline
stages below are still real, tested, and ready for the day real depth
exists.
"""

from __future__ import annotations
