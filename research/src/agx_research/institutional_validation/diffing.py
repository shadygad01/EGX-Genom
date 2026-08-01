"""Answers "why did this change?" for a versioned knowledge object.

Q9 of the Institutional Investment Validation mission ("can it identify
why a recommendation changed?") revealed a genuine, previously-missing
capability: `KnowledgeStore`/`storage.Repository` already keep every
revision (`revisions_for()`/`Repository.history()`), but nothing computed
a human-readable diff between two revisions. This is the minimal such
capability -- built entirely on the existing repository/versioning
mechanism (Principle 5, "everything is versioned"), not a new storage
path, and not a new pipeline stage.

Scope, stated honestly rather than silently: only `KnowledgeObject` is
diffed here, because it's the only decision-chain entity that is actually
persisted with multiple revisions in a `Repository`. `Recommendation` and
`PortfolioRecommendation` are recomputed fresh on every run and never
stored with a version history at all -- there is nothing to diff for them
without adding a new persisted, versioned store for ephemeral outputs,
which is a real architectural decision outside this validation mission's
scope (named in the validation report, not silently built around).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agx_research.knowledge.schema import KnowledgeObject
from agx_research.knowledge.store import KnowledgeStore

# Fields worth surfacing in a "what changed" summary -- deliberately not
# every field (e.g. `supporting_evidence` prose rarely changes meaningfully
# between monitoring revisions; `provenance.produced_at` always changes and
# would drown out the fields that actually matter to an investor).
_TRACKED_FIELDS = (
    "status",
    "confidence",
    "expected_return",
    "expected_risk",
    "retired_at",
    "retirement_reason",
)


class FieldChange(BaseModel):
    field: str
    before: Any
    after: Any


class RevisionDiff(BaseModel):
    knowledge_id: str
    from_version: int
    to_version: int
    changed_fields: list[FieldChange]
    performance_records_added: int
    summary: str


def diff_knowledge_revisions(previous: KnowledgeObject, current: KnowledgeObject) -> RevisionDiff:
    """Diff two adjacent revisions of the *same* knowledge object.

    Never fabricates a reason: if nothing in `_TRACKED_FIELDS` changed and
    no performance record was appended, the summary says exactly that
    rather than inventing a narrative.
    """
    if previous.id != current.id:
        raise ValueError(
            f"Cannot diff revisions of different entities ({previous.id} vs {current.id})."
        )
    changed = [
        FieldChange(field=field, before=getattr(previous, field), after=getattr(current, field))
        for field in _TRACKED_FIELDS
        if getattr(previous, field) != getattr(current, field)
    ]
    records_added = len(current.performance_history) - len(previous.performance_history)

    parts = [f"{c.field}: {c.before!r} -> {c.after!r}" for c in changed]
    if records_added > 0:
        parts.append(f"{records_added} new performance record(s)")
    summary = (
        f"{current.id} v{previous.version}->v{current.version}: " + "; ".join(parts)
        if parts
        else f"{current.id} v{previous.version}->v{current.version}: no tracked field changed."
    )

    return RevisionDiff(
        knowledge_id=current.id,
        from_version=previous.version,
        to_version=current.version,
        changed_fields=changed,
        performance_records_added=records_added,
        summary=summary,
    )


def diff_knowledge_history(store: KnowledgeStore, knowledge_id: str) -> list[RevisionDiff]:
    """Every adjacent-revision diff for `knowledge_id`, oldest first --
    the full "what changed and why" timeline for one piece of knowledge.
    """
    revisions = store.revisions_for(knowledge_id)
    return [
        diff_knowledge_revisions(previous, current)
        for previous, current in zip(revisions, revisions[1:])
    ]


__all__ = ["FieldChange", "RevisionDiff", "diff_knowledge_history", "diff_knowledge_revisions"]
