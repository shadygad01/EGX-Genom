import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App";
import { createDataProvider } from "../src/data/factory";
import type { DashboardDataProvider } from "../src/data/DataProvider";
import type { KnowledgeObject } from "../src/types";

function fakeProvider(overrides: Partial<DashboardDataProvider> = {}): DashboardDataProvider {
  return {
    getKnowledge: async () => [],
    getEvents: async () => [],
    getPatterns: async () => [],
    getRecommendations: async () => [],
    getMarketState: async () => null,
    getRuntimeMetrics: async () => [],
    getSystemStatus: async () => null,
    getSourceRegistry: async () => [],
    ...overrides,
  };
}

function knowledgeObject(overrides: Partial<KnowledgeObject> = {}): KnowledgeObject {
  return {
    id: "egx-test-knowledge",
    version: 1,
    discovery_date: "2026-06-01",
    creator_agent: "test_agent",
    supporting_evidence: [],
    confidence: 0.8,
    statistical_evidence: {
      method: "test",
      statistic: 1,
      p_value: 0.01,
      sample_size: 10,
      confidence_interval: null,
    },
    economic_explanation: "test explanation",
    affected_assets: ["COMI"],
    horizon: "swing",
    expected_return: 0.05,
    expected_risk: 0.03,
    status: "promoted",
    performance_history: [],
    retired_at: null,
    retirement_reason: null,
    provenance: { produced_by: "test", produced_at: "2026-06-01T00:00:00", inputs: [] },
    ...overrides,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the knowledge table using whatever provider it's given", async () => {
    const provider = fakeProvider({ getKnowledge: async () => [knowledgeObject()] });
    render(<App provider={provider} />);

    expect(await screen.findByText("egx-test-knowledge")).toBeInTheDocument();
    expect(screen.getByText("COMI")).toBeInTheDocument();
    expect(screen.getByText("promoted")).toBeInTheDocument();
  });

  it("shows the empty state when no knowledge has been promoted", async () => {
    render(<App provider={fakeProvider()} />);
    expect(await screen.findByText(/No knowledge objects have been promoted yet/)).toBeInTheDocument();
  });

  it("shows an error state when the provider rejects", async () => {
    const provider = fakeProvider({
      getKnowledge: async () => {
        throw new Error("boom");
      },
    });
    render(<App provider={provider} />);
    expect(await screen.findByText(/Error loading knowledge: boom/)).toBeInTheDocument();
  });

  it("renders identically regardless of which provider kind is behind the interface", async () => {
    const knowledge = [knowledgeObject()];
    const staticLike = fakeProvider({ getKnowledge: async () => knowledge });
    const apiLike = fakeProvider({ getKnowledge: async () => knowledge });

    const { unmount } = render(<App provider={staticLike} />);
    expect(await screen.findByText("egx-test-knowledge")).toBeInTheDocument();
    unmount();

    render(<App provider={apiLike} />);
    expect(await screen.findByText("egx-test-knowledge")).toBeInTheDocument();
  });

  it("makes no /api/* requests when rendered with a real StaticJsonProvider (GitHub Pages mode)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([knowledgeObject()]), {
        status: 200,
        headers: { "content-type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App provider={createDataProvider("static")} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(urls.some((u) => u.includes("/api/"))).toBe(false);
    expect(urls.some((u) => u.includes("knowledge.json"))).toBe(true);
  });
});
