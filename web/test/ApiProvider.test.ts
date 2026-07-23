import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiProvider } from "../src/data/ApiProvider";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ApiProvider", () => {
  it("fetches every resource from /api/<resource>", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse([])));
    vi.stubGlobal("fetch", fetchMock);
    const provider = new ApiProvider();

    await provider.getKnowledge();
    await provider.getEvents();
    await provider.getPatterns();
    await provider.getRecommendations();
    await provider.getRuntimeMetrics();
    await provider.getSourceRegistry();

    const urls = fetchMock.mock.calls.map((call) => call[0] as string);
    expect(urls).toEqual([
      "/api/knowledge",
      "/api/events",
      "/api/patterns",
      "/api/recommendations",
      "/api/runtime-metrics",
      "/api/source-registry",
    ]);
  });

  it("getMarketState/getSystemStatus hit /api/market-state and /api/system-status", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse(null)));
    vi.stubGlobal("fetch", fetchMock);
    const provider = new ApiProvider();

    await provider.getMarketState();
    await provider.getSystemStatus();

    const urls = fetchMock.mock.calls.map((call) => call[0] as string);
    expect(urls).toEqual(["/api/market-state", "/api/system-status"]);
  });

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([{ id: "k1" }])));
    const provider = new ApiProvider();
    await expect(provider.getKnowledge()).resolves.toEqual([{ id: "k1" }]);
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, 500)));
    const provider = new ApiProvider();
    await expect(provider.getKnowledge()).rejects.toThrow(/500/);
  });
});
