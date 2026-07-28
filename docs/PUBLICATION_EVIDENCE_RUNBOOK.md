# Publication Evidence Runbook

This runbook is the only supported route from `research_only` to
`publication_ready`. It validates claims against archived inputs; it does not
create evidence, grant data rights, or replace legal review.

## Run the gate

From `research/`, with the production environment installed:

```bash
uv run python -m agx_research.cli \
  --data-dir /absolute/path/to/production-data \
  publication-status --date 2026-07-28
```

The command prints the complete JSON report. Exit code `0` means every check
passed. Exit code `2` means publication remains blocked. Missing or malformed
input files appear under `publication_input_validation` rather than being
silently treated as approval.

## External evidence file

Copy `research/data/publication_evidence.template.json` to
`<data-dir>/publication_evidence.json`. Keep every claim `false` until its
references exist in the same data directory's `raw_documents.json`.

Each key changed to `true` needs references under the same `evidence_refs` key:

```json
{
  "live_egx_market_data": true,
  "official_disclosures_four_periods": false,
  "current_cbe_capmas_macro": false,
  "two_source_price_corroboration": false,
  "evidence_refs": {
    "live_egx_market_data": [{
      "raw_document_id": "rawdoc_ID_FROM_ARCHIVE",
      "source_id": "SOURCE_ID_FROM_REGISTRY",
      "content_hash": "64_LOWERCASE_HEX_CHARACTERS_FROM_RAW_DOCUMENT",
      "fetched_at": "2026-07-28T09:30:00",
      "coverage_pct": 1.0,
      "independent_group": "provider-family-name"
    }]
  }
}
```

The validator requires an exact raw-document id, source id, SHA-256 hash and
fetch timestamp match. Coverage must equal `1.0`; the source must be legally
cleared in `source_registry.json`; evidence must be no older than 7 days for
live prices, 550 days for four-period disclosures, 45 days for macro, and 7
days for price corroboration. Price corroboration needs at least two verified
references with different `independent_group` values.

Setting booleans to `true`, copying ids from another data directory, or editing
an exported dashboard artifact cannot pass the gate.

## Human legal approval file

An actual legal reviewer—not an operator or automated process—creates
`<data-dir>/legal_publication_approval.json` after reviewing the stated scope:

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

The signed review must itself be archived in `raw_documents.json`. Approval
must be effective on the evaluation date, unexpired, fully scoped, and no more
than 366 days old. Do not ship a pre-filled approval template: that would turn
a human control into a copy-and-edit checkbox.

## Performance gate

The command reads `decision_ledger.json` directly. Every short, medium and long
horizon must have at least 30 expired benchmark-matched decisions. After costs,
mean and median excess return and the 95% lower confidence bound must all be
positive; mean realized return must be positive and maximum drawdown must not
be below -25%. Missing EGX30 observations fail the gate.

Archive the emitted report and use generated `publication_gate.json` as the
UI/API source. Do not override `publication_status` downstream.
