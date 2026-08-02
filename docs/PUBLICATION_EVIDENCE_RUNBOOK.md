# Publication Evidence Runbook

**Superseded (2026-08-02).** Until this date, this runbook described the
only supported route from `research_only` to `publication_ready`: a
human had to author two evidence files and clear a 30-result-per-horizon
performance bar before *any* decision, of any quality, could size a
position. Neither had ever been done once in this platform's history, so
every decision stayed `research_only` regardless of how complete or
well-evidenced it was.

The project owner's explicit correction: publication should be governed
by decision quality, not by how much track record has accumulated or
whether a human has formally signed off. See `docs/ARCHITECTURE_DECISIONS.md`
(the numbered entry for this change) for the full reasoning, and
`research/src/agx_research/meta/decision_quality.py`'s module docstring
for the mechanism. Nothing in this runbook is a manual step anymore.

## What actually gates publication now

`meta.decision_quality.evaluate_decision_quality()`, evaluated
automatically per ticker per horizon on every `agx decide`/`agx run` —
no file to author, no command to run separately. A decision publishes
when its own `Explanation` and `HorizonDecision` are complete:

1. Supporting evidence is present and traceable (`supporting_evidence`/
   `evidence_refs` both non-empty).
2. The investment thesis is complete (`why_this_stock`/`why_now`/
   `why_not_others` all stated).
3. Confidence was actually calculated (a finite number in `[0, 1]`).
4. Invalidation conditions are defined.
5. Entry and review (monitoring) conditions are defined.
6. The decision is internally consistent (a `BUY_CANDIDATE` carries
   numeric entry and invalidation price levels).

Nothing here needs external authoring — every one of these is already
computed by the agent/model/decision-engine code that produced the
recommendation in the first place.

## System Maturity — informational only, never a gate

`agx publication-status --date <ISO date>` reports
`meta.system_maturity.SystemMaturityReport`: a label (`early` /
`validating` / `developing` / `established` / `verified`) built from
real `decision_ledger.json` history. It always exits `0` — there is no
"blocked" outcome left to signal. Use it to see how much the platform's
own track record has earned, not to decide whether to trust today's
recommendations (that's what the per-decision quality checks above are
for).

## Optional governance review — decoupled, never blocking

`<data-dir>/legal_publication_approval.json` remains a real, optional
input, unchanged in shape:

```json
{
  "reviewer": "REVIEWER_NAME",
  "scope": "EGX investment-decision publication and data-use scope",
  "approved_at": "2026-07-28T10:00:00",
  "expires_at": "2027-07-28",
  "conflicts_disclosed": true,
  "methodology_approved": true,
  "evidence": {
    "raw_document_id": "rawdoc_ID_OF_SIGNED_REVIEW",
    "source_id": "LEGAL_REVIEW_SOURCE_ID",
    "content_hash": "64_LOWERCASE_HEX_CHARACTERS_FROM_RAW_DOCUMENT",
    "fetched_at": "2026-07-28T10:00:00",
    "coverage_pct": 1.0,
    "independent_group": "human-legal-review"
  }
}
```

Supplying one can only ever raise `SystemMaturityReport.level` to
`verified` (and only once the real track record already reaches
`established` on its own) — it is never read by, and never gates,
`agx decide`/`agx run`. It exists for a future regulated/officially-
published distribution mode this platform does not operate in today; a
real fund manager using this platform's own recommendations for their
own decisions (its only mode today) needs no governance file at all.

`research/data/publication_evidence.template.json` and the old
`publication_evidence.json` input are retired entirely — the four
external-evidence booleans they encoded are now implicitly, honestly
answered by whether a specific decision actually has traceable evidence,
per decision, rather than asserted system-wide by a human copying
document ids into a file.
