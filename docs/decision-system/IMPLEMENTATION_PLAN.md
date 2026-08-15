# Implementation Plan

## P0 — protect and verify the current production contract

The pipeline must continue to pass the independent 101/101 contract, unique ranks, financial coverage, provenance, no-look-ahead, and live manifest checks. Any failed check blocks publication. Rollback is the previous canonical manifest and commit.

## P1 — decision governance, not a second engine

Add a machine-readable research-module manifest requiring question, consumer, output, uncertainty, validation status, freshness, and failure mode. Add a test that rejects a core module lacking those declarations. This is a small governance control and does not alter live scores or actions.

Add an information-value schema for decision-impact classification. Initially use it for validation and event metadata; do not retroactively reinterpret historical events without evidence. The acceptance test is that a context-only item cannot enter the core evidence set.

## P2 — evidence quality and comparative surfaces

Use existing provenance, readiness, publication, ledger, and calibration infrastructure to expose evidence freshness, conflicts, and maturity. Do not add a multiplicative confidence formula before the ledger has enough outcomes to validate it. Sector-relative comparison is deferred until a verified sector source is available.

## P3 — future research

Only after a measurable decision gap is documented should the project consider additional cross-stock, external-sector, microstructure, or news sources. Each proposal requires an experiment, a validation window, a downstream decision consumer, and a rollback plan.

## Acceptance criteria

A release is complete when the full test suite is green, the independent contract reports 101/101 and ranks 1–101, the manifest is live, the frontend has no replay warning, and the audit documents agree with the code and artifact schemas.
