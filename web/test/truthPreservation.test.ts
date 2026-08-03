// Permanent Truth Preservation regression suite (AD-60,
// docs/TRUTH_PRESERVATION_POLICY.md). Deliberately separate from
// StaticJsonProvider.test.ts so this file's job -- "never fabricates a
// decision" -- can't be quietly diluted by edits made for unrelated
// StaticJsonProvider coverage. Weakening or deleting an assertion here
// requires the same scrutiny as any other protected test.
import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveDecisionsUnavailableError } from "../src/data/DataProvider";
import { StaticJsonProvider } from "../src/data/StaticJsonProvider";
import cioDeskEn from "../src/i18n/locales/en/cioDesk.json";
import portfolioEn from "../src/i18n/locales/en/portfolio.json";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Truth Preservation: StaticJsonProvider never fabricates a decision or a capital allocation plan", () => {
  it("postDecisions always reports itself unavailable, never fabricating a decision", async () => {
    const provider = new StaticJsonProvider();
    await expect(
      provider.postDecisions({ date: "2026-06-14", positions: { COMI: { held: true, current_weight: 0.15, average_cost: 100 } } }),
    ).rejects.toThrow(LiveDecisionsUnavailableError);
  });

  it("postCapitalAllocation always reports itself unavailable, never fabricating a plan", async () => {
    const provider = new StaticJsonProvider();
    await expect(
      provider.postCapitalAllocation({ date: "2026-06-14", positions: { COMI: { held: true, current_weight: 0.15, average_cost: 100 } } }),
    ).rejects.toThrow(LiveDecisionsUnavailableError);
  });
});

describe("Truth Preservation: CIO Desk / Portfolio copy stays honest about what's live", () => {
  it("never claims a live decision/allocation engine is active without one", () => {
    const strings = JSON.stringify(cioDeskEn) + JSON.stringify(portfolioEn);
    const lowered = strings.toLowerCase();
    expect(lowered).not.toContain("client decision engine");
    expect(lowered).not.toContain("model portfolio allocation active");
  });

  it("still tells the investor personalized decisions need a live backend", () => {
    expect(cioDeskEn.capitalAllocation.needsBackendTitle.toLowerCase()).toContain("live backend");
    expect(portfolioEn.unavailable.title.toLowerCase()).toContain("live backend");
  });
});
