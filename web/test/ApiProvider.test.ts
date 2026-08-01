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
    await provider.getTickerDataGapReport();

    const urls = fetchMock.mock.calls.map((call) => call[0] as string);
    expect(urls).toEqual([
      "/api/knowledge",
      "/api/events",
      "/api/patterns",
      "/api/recommendations",
      "/api/runtime-metrics",
      "/api/source-registry",
      "/api/ticker-data-gaps",
    ]);
  });

  it("object artifacts use their matching API endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse(null)));
    vi.stubGlobal("fetch", fetchMock);
    const provider = new ApiProvider();

    await provider.getMarketState();
    await provider.getUniverse();
    await provider.getSystemStatus();

    const urls = fetchMock.mock.calls.map((call) => call[0] as string);
    expect(urls).toEqual(["/api/market-state", "/api/universe", "/api/system-status"]);
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

  it("postDecisions POSTs to /api/decisions with the request body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([{ ticker: "COMI" }]));
    vi.stubGlobal("fetch", fetchMock);
    const provider = new ApiProvider();

    const result = await provider.postDecisions({
      date: "2026-06-14",
      positions: { COMI: { held: true, current_weight: 0.05 } },
    });

    expect(result).toEqual([{ ticker: "COMI" }]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/decisions",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: "2026-06-14",
          positions: { COMI: { held: true, current_weight: 0.05 } },
        }),
      }),
    );
  });

  it("postDecisions surfaces the server's error message on failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: "unconfigured" }, 501)));
    const provider = new ApiProvider();
    await expect(provider.postDecisions({ date: "2026-06-14" })).rejects.toThrow(/unconfigured/);
  });

  it("postCapitalAllocation POSTs to /api/capital-allocation with the request body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ as_of: "2026-06-14", queue: [] }));
    vi.stubGlobal("fetch", fetchMock);
    const provider = new ApiProvider();

    const result = await provider.postCapitalAllocation({
      date: "2026-06-14",
      positions: { COMI: { held: true, current_weight: 0.05 } },
    });

    expect(result).toEqual({ as_of: "2026-06-14", queue: [] });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/capital-allocation",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: "2026-06-14",
          positions: { COMI: { held: true, current_weight: 0.05 } },
        }),
      }),
    );
  });

  it("postCapitalAllocation surfaces the server's error message on failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: "unconfigured" }, 501)));
    const provider = new ApiProvider();
    await expect(provider.postCapitalAllocation({ date: "2026-06-14" })).rejects.toThrow(/unconfigured/);
  });

  it("fetches the CIO Desk artifacts from their matching API endpoints", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse(null)));
    vi.stubGlobal("fetch", fetchMock);
    const provider = new ApiProvider();

    await provider.getPortfolioSummary();
    await provider.getWarnings();
    await provider.getCommitteeSummary();

    const urls = fetchMock.mock.calls.map((call) => call[0] as string);
    expect(urls).toEqual(["/api/portfolio-summary", "/api/warnings", "/api/committee-summary"]);
  });
});
