import { describe, expect, it } from "vitest";
import { dedupeEvidence, humanizeEvidence } from "../src/lib/format";

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

  it("relabels a knowledge object id + version prefix", () => {
    expect(
      humanizeEvidence("hyp_3f2a91bc7d4e v2: confidence=0.72, expected_return=0.0410, p_value=0.031"),
    ).toBe("Knowledge: Confidence: 0.72, Expected Return: 0.0410, P Value: 0.031");
  });

  it("relabels an event id prefix", () => {
    expect(
      humanizeEvidence(
        'event event_a1b2c3d4e5f6: "Egypt raises fuel prices" large_price_move, severity=high, confidence=0.65, sources=reuters',
      ),
    ).toBe('Event: "Egypt raises fuel prices" Large Price Move, Severity: high, Confidence: 0.65, Sources: reuters');
  });

  it("title-cases a leading horizon prefix", () => {
    expect(humanizeEvidence("micro: expected_return=0.0210, expected_risk=0.0500, confidence=0.60")).toBe(
      "Micro: Expected Return: 0.0210, Expected Risk: 0.0500, Confidence: 0.60",
    );
  });

  it("humanizes a bare snake_case token with no key=value form", () => {
    expect(humanizeEvidence("macro_news, severity=low")).toBe("Macro News, Severity: low");
  });
});

describe("dedupeEvidence", () => {
  it("drops exact-duplicate lines while preserving first-seen order", () => {
    expect(dedupeEvidence(["a", "b", "a", "c", "b"])).toEqual(["a", "b", "c"]);
  });

  it("leaves a list with no duplicates unchanged", () => {
    expect(dedupeEvidence(["a", "b", "c"])).toEqual(["a", "b", "c"]);
  });
});
