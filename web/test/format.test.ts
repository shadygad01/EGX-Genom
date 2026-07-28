import { describe, expect, it } from "vitest";
import { humanizeEvidence } from "../src/lib/format";

describe("humanizeEvidence", () => {
  it("formats a single key=value evidence string", () => {
    expect(humanizeEvidence("macro_correlation=0.5320")).toBe("Macro Correlation: 0.5320");
  });

  it("formats multiple comma-separated key=value pairs", () => {
    expect(humanizeEvidence("expected_risk=0.0500, confidence=0.80")).toBe(
      "Expected Risk: 0.0500, Confidence: 0.80",
    );
  });

  it("does not split a value that itself contains commas", () => {
    expect(humanizeEvidence("sources=enterprise,mubasher")).toBe("Sources: enterprise,mubasher");
  });

  it("humanizes key=value pairs embedded inside a larger sentence", () => {
    expect(
      humanizeEvidence(
        "episode 2020-01-11..2020-01-30 (distance=0.0000, next_10d_return=+10.00%)",
      ),
    ).toBe("episode 2020-01-11..2020-01-30 (Distance: 0.0000, Next 10d Return: +10.00%)");
  });

  it("leaves free-form text after a key=value prefix untouched", () => {
    expect(humanizeEvidence("headline=Egypt central bank holds rates steady")).toBe(
      "Headline: Egypt central bank holds rates steady",
    );
  });

  it("leaves plain prose with no key=value shape untouched", () => {
    const prose = "Any supporting knowledge object is retired or its performance degrades.";
    expect(humanizeEvidence(prose)).toBe(prose);
  });
});
