import { describe, expect, it } from "vitest";
import type { ArtifactPublicationManifest } from "../src/types";
import {
  CANONICAL_REPOSITORY,
  CANONICAL_WORKFLOW_NAME,
  isProductionVerified,
  provenanceIssue,
} from "../src/lib/provenance";

function canonicalManifest(overrides: Partial<ArtifactPublicationManifest> = {}): ArtifactPublicationManifest {
  return {
    generated_at: "2026-08-03T12:00:00",
    pipeline_mode: "live",
    git_commit: "deadbeef",
    workflow_run_id: "123456",
    workflow_name: CANONICAL_WORKFLOW_NAME,
    repository: CANONICAL_REPOSITORY,
    generator_version: "1.0.0",
    source_data_as_of: "2026-08-01",
    schema_version: "1",
    ...overrides,
  };
}

describe("provenanceIssue / isProductionVerified", () => {
  it("is missing_manifest when no manifest was published at all", () => {
    expect(provenanceIssue(null)).toBe("missing_manifest");
    expect(isProductionVerified(null)).toBe(false);
  });

  it("is non_live_mode for a mock-mode manifest, even with everything else canonical", () => {
    const manifest = canonicalManifest({ pipeline_mode: "mock" });
    expect(provenanceIssue(manifest)).toBe("non_live_mode");
    expect(isProductionVerified(manifest)).toBe(false);
  });

  it("is non_live_mode for a replay-mode manifest", () => {
    expect(provenanceIssue(canonicalManifest({ pipeline_mode: "replay" }))).toBe("non_live_mode");
  });

  it("is unverified_workflow when workflow_run_id is missing", () => {
    const manifest = canonicalManifest({ workflow_run_id: null });
    expect(provenanceIssue(manifest)).toBe("unverified_workflow");
  });

  it("is unverified_workflow when git_commit is missing", () => {
    expect(provenanceIssue(canonicalManifest({ git_commit: null }))).toBe("unverified_workflow");
  });

  it("is unverified_workflow when the workflow name doesn't match", () => {
    expect(provenanceIssue(canonicalManifest({ workflow_name: "some other workflow" }))).toBe(
      "unverified_workflow"
    );
  });

  it("is unverified_workflow when the repository doesn't match", () => {
    expect(provenanceIssue(canonicalManifest({ repository: "someone-else/EGX-Genom" }))).toBe(
      "unverified_workflow"
    );
  });

  it("is verified (null issue) only when every field matches the canonical workflow", () => {
    const manifest = canonicalManifest();
    expect(provenanceIssue(manifest)).toBeNull();
    expect(isProductionVerified(manifest)).toBe(true);
  });
});
