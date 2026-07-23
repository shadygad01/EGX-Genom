import { afterEach, describe, expect, it, vi } from "vitest";
import { StaticJsonProvider } from "../src/data/StaticJsonProvider";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("StaticJsonProvider", () => {
  it("fetches list resources from BASE_URL + data/<file>.json", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([{ id: "k1" }]));
    vi.stubGlobal("fetch", fetchMock);

    const provider = new StaticJsonProvider();
    const result = await provider.getKnowledge();

    expect(result).toEqual([{ id: "k1" }]);
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain("data/knowledge.json");
    expect(url).not.toContain("/api/");
  });

  it("fetches every one of the eight resources", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse([])));
    vi.stubGlobal("fetch", fetchMock);
    const provider = new StaticJsonProvider();

    await provider.getKnowledge();
    await provider.getEvents();
    await provider.getPatterns();
    await provider.getRecommendations();
    await provider.getRuntimeMetrics();
    await provider.getSourceRegistry();

    const urls = fetchMock.mock.calls.map((call) => call[0] as string);
    expect(urls.some((u) => u.includes("knowledge.json"))).toBe(true);
    expect(urls.some((u) => u.includes("events.json"))).toBe(true);
    expect(urls.some((u) => u.includes("patterns.json"))).toBe(true);
    expect(urls.some((u) => u.includes("recommendations.json"))).toBe(true);
    expect(urls.some((u) => u.includes("runtime_metrics.json"))).toBe(true);
    expect(urls.some((u) => u.includes("source_registry.json"))).toBe(true);
  });

  it("returns [] for a list resource on 404 rather than throwing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(null, 404)));
    const provider = new StaticJsonProvider();
    await expect(provider.getKnowledge()).resolves.toEqual([]);
  });

  it("returns null for market_state.json / system_status.json when absent (404)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(null, 404)));
    const provider = new StaticJsonProvider();
    await expect(provider.getMarketState()).resolves.toBeNull();
    await expect(provider.getSystemStatus()).resolves.toBeNull();
  });

  it("passes through a genuinely null market_state.json (no run has happened yet)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(null, 200)));
    const provider = new StaticJsonProvider();
    await expect(provider.getMarketState()).resolves.toBeNull();
  });

  it("throws on a non-404 error response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, 500)));
    const provider = new StaticJsonProvider();
    await expect(provider.getKnowledge()).rejects.toThrow(/500/);
  });
});
