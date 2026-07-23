# Event Platform Design Audit (System 03)

A standalone design audit of the Event Platform, per the instruction to
treat it as its own subsystem and ignore the lack of production data
providers. This documents what Epoch II actually built, what was missing
against a real production-readiness bar, and the design of everything
closeable without external data. The goal stated for this work: adding a
real data provider later should be a configuration task (write one more
adapter), not an architectural one.

## Audit: what Epoch II's Event Platform actually had

`events/event.py`, `repository.py`, `adapters.py` — a canonical `Event`
schema, a versioned repository, and adapters deriving events from a
`DatasetSnapshot`. Real, but incomplete against everything the brief now
asks for:

1. **Event identity was accidental, not designed.** `new_id("event")` is a
   random UUID. Re-deriving events from the same underlying data (e.g.
   re-running an adapter, or two independent sources reporting the same
   real-world occurrence) produced two *different* event records with no
   way to recognize them as the same thing. This is the root cause of
   points 2–4 below — without stable identity, deduplication and
   corroboration have nothing to key on.
2. **No deduplication.** Nothing detected or merged duplicate event
   records.
3. **No conflict resolution.** Nothing existed for the case where two
   sources disagree about the same event's details.
4. **No lifecycle.** An `Event`, once created, had no notion of being
   confirmed, corroborated by a second source, disputed, retracted, or
   superseded by a corrected version — Epoch II gave every other major
   entity (`KnowledgeObject`, `Gene`, `Hypothesis`) a lifecycle but not
   `Event`.
5. **No taxonomy.** `EventType` was six flat categories with no controlled
   vocabulary underneath; adapters wrote free-form strings into
   `metadata["event_type_raw"]` instead.
6. **No entity resolution.** `entities: list[str]` was raw tickers with no
   structure — no distinction between a resolved canonical id and an
   unresolved mention, no entity kind, no link to `universe.UniverseProvider`.
7. **No impact-horizon classification.** Nothing said which `Horizon`(s)
   an event type is even relevant to investigate.
8. **No event-specific graph integration.** The generic
   `graph.edges_from_provenance()` covers provenance edges for any entity,
   but nothing built entity nodes or typed event-to-event relationship
   edges specifically for events.

## Design decisions

### Event identity = content fingerprint, not a random id

`events/identity.py`: `compute_event_fingerprint()` hashes
`(event_type, subtype, sorted canonical entity ids, event date)` —
deliberately **excluding** `source`, so two different sources reporting the
same real-world event collide onto the same fingerprint and can be
recognized as corroborating each other, rather than treated as unrelated
events. `derive_event_id()` turns that fingerprint into the event's `id`.
This makes event registration naturally idempotent: re-deriving the same
event from the same data always produces the same `id`.

### Entity resolution

`events/entity.py` (`EntityKind`, `EntityRef`) and
`events/entity_resolver.py` (`EntityResolver`). `EntityRef` carries the
canonical id, kind, an optional display name, and the raw mention that was
resolved — auditable, not just a bare string. `EntityResolver` uses
`universe.UniverseProvider`/`SectorProvider` as the source of truth for
company identity, with real (if simple) mechanical matching: exact ticker,
then case-insensitive company-name containment, then known macro series
ids, falling back to `EntityKind.UNKNOWN` rather than guessing. Resolving
free-text mentions from unstructured news bodies (real NLP entity linking)
is out of scope until real unstructured text data exists — flagged as a
gap, not faked.

### Taxonomy and ontology

`events/taxonomy.py`: `EventSubtype` — a controlled vocabulary of ~28
subtypes under the six `EventType` categories (e.g. `CORPORATE` →
`EARNINGS`/`DIVIDEND`/`STOCK_SPLIT`/`MERGER_ACQUISITION`/...), with
`validate_subtype()` enforcing that a subtype belongs to its category.
`events/ontology.py`: `classify_impact_horizons(subtype)` — a documented,
explicit mapping from subtype to the `Horizon`(s) it's relevant to
*investigate* (not a prediction of price impact — a triage/categorization
decision, the same kind `MarketStructureAgent` already makes when it
proposes `Horizon.MICRO` for a candidate hypothesis). This is engineering
classification of research relevance, not fabricated market knowledge.

### Deduplication and conflict resolution

`events/conflict.py`: `ConflictResolutionPolicy` (ABC) +
`ConservativeConflictPolicy` (the one real, concrete implementation).
Comparing an existing event's metadata against a new candidate's: keys
present in both with *equal* values are corroboration (confidence rises,
capped at 1.0); keys present in both with *different* values are a
material conflict — the event is marked `DISPUTED` and the conflicting
keys are recorded, rather than silently picking one value. This is the
direct implementation of "never fabricate confidence" applied to conflicting
sources: a disagreement must be visible, not resolved by guessing.

### Lifecycle

`events/lifecycle.py`: `EventStatus` (`PENDING → CONFIRMED/CORROBORATED →
DISPUTED ⇄ CORROBORATED → RETRACTED/SUPERSEDED → ARCHIVED`) with
`can_transition()`, mirroring the `KnowledgeStatus`/`GeneStatus` pattern
already established elsewhere in the codebase.

### The registration service

`events/service.py`: `EventPlatform` is the sole sanctioned entry point for
turning a candidate `Event` (whatever an adapter proposes) into a
persisted, deduplicated, conflict-resolved, lifecycle-managed one —
mirroring the "agents propose, the pipeline decides" pattern:
`adapters.py` still only *proposes* candidate events; nothing writes to
`EventRepository` except through `EventPlatform.register()`.

- `register(candidate)` — computes the fingerprint/id; if unseen, persists
  as a new event (version 1); if seen, resolves via
  `ConflictResolutionPolicy` and persists a new revision (corroborated or
  disputed).
- `retract(event_id, reason)` — status → `RETRACTED`.
- `supersede(event_id, corrected_candidate)` — mirrors
  `AlphaGenome.mutate()`: creates a **new** event (new fingerprint, since
  the corrected facts changed) linked via an `EventRelationship`
  (`SUPERSEDES`), and marks the original `SUPERSEDED` — never overwritten.

### Event relationships and graph integration

`Event.relationships` becomes `list[EventRelationship]`
(`related_event_id` + a typed `EventRelationshipType`: `CORROBORATES`,
`SUPERSEDES`, `CONTRADICTS`, `CAUSALLY_PRECEDES`, `PART_OF`) instead of a
flat, untyped id list — this is what "Event Graph links" in the original
brief actually needs to mean something.

`events/graph_integration.py` builds `GraphNode`s for entities and events
and `GraphEdge`s for both entity-involvement and typed event relationships,
reusing `graph.NodeType`/`GraphEdge` (one new member, `NodeType.MACRO_SERIES`,
added for macro-series entities) rather than inventing a parallel
representation.

## What becomes a configuration task, not an architecture task

Adding a real data provider now means: write a function that turns that
provider's raw payload into candidate `Event`s (same shape
`adapters.events_from_*` already produce) and call
`EventPlatform.register()` on each. Identity, deduplication, conflict
resolution, lifecycle, taxonomy validation, entity resolution, and graph
integration all already exist and don't change.

## What remains a genuine gap (not closeable without external data)

- Political and Technical event adapters (no data source).
- Real NLP entity linking over unstructured text (news bodies, not just
  pre-tagged tickers).
- A true multi-source conflict scenario has not been observed in
  production — `ConservativeConflictPolicy`'s specific confidence-adjustment
  constants are a defensible default, not a calibrated one.
