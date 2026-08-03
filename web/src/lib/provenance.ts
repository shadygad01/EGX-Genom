// Artifact provenance verification (AD-64, docs/ARCHITECTURE_DECISIONS.md).
// Mirrors agx_research.dashboard.manifest.is_canonical_production() --
// the same fields, the same all-or-nothing rule. Kept as a small, pure
// function (no fetching here) so it's trivial to unit-test every branch:
// a manifest that merely claims `pipeline_mode: "live"` with no workflow
// identity behind it is not enough to call this "production-generated".

import type { ArtifactPublicationManifest } from "../types";

export const CANONICAL_WORKFLOW_NAME = "Deploy web dashboard to GitHub Pages";
export const CANONICAL_REPOSITORY = "shadygad01/EGX-Genom";

export type ProvenanceIssue = "missing_manifest" | "non_live_mode" | "unverified_workflow";

/** Why this bundle can't be verified as canonical production data, in
 * priority order -- `null` only when every check passes. Used to pick a
 * specific, honest banner message rather than one generic "unverified"
 * string that would blur "nothing was published" with "something was
 * published, but not by the real workflow". */
export function provenanceIssue(manifest: ArtifactPublicationManifest | null): ProvenanceIssue | null {
  if (manifest == null) return "missing_manifest";
  if (manifest.pipeline_mode !== "live") return "non_live_mode";
  if (
    manifest.workflow_name !== CANONICAL_WORKFLOW_NAME ||
    manifest.repository !== CANONICAL_REPOSITORY ||
    !manifest.workflow_run_id ||
    !manifest.git_commit
  ) {
    return "unverified_workflow";
  }
  return null;
}

export function isProductionVerified(manifest: ArtifactPublicationManifest | null): boolean {
  return provenanceIssue(manifest) === null;
}
