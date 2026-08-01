import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DashboardDataProvider } from "../src/data/DataProvider";

function fakeProvider(overrides: Partial<DashboardDataProvider> = {}): DashboardDataProvider {
  return {
    getKnowledge: async () => [],
    getEvents: async () => [],
    getPatterns: async () => [],
    getRecommendations: async () => [],
    getMarketState: async () => null,
    getUniverse: async () => null,
    getRuntimeMetrics: async () => [],
    getSystemStatus: async () => null,
    getSourceRegistry: async () => [],
    getInvestmentCases: async () => null,
    getCollectorStatus: async () => [],
    getRuntimeStatus: async () => null,
    getDashboardMetrics: async () => null,
    getMissionStatus: async () => null,
    getExecutionReport: async () => null,
    getGenes: async () => [],
    getPapers: async () => [],
    getHypotheses: async () => [],
    getKnowledgeGraph: async () => ({ nodes: [], edges: [] }),
    getFinancialStatements: async () => [],
    getFinancialCoverage: async () => null,
    getSourceMetrics: async () => [],
    getMarketBreadth: async () => null,
    getAcquisitionDecisions: async () => [],
    getDecisionReadiness: async () => [],
    getTickerDataGapReport: async () => [],
    getSourceTruth: async () => [],
    getDecisionHistory: async () => [],
    getDecisionPerformance: async () => [],
    getPublicationGate: async () => null,
    getDiscoveryReport: async () => [],
    getDiscoveryMetrics: async () => null,
    getEndpointCandidates: async () => [],
    postDecisions: async () => [],
    ...overrides,
  };
}

let mockProvider: DashboardDataProvider = fakeProvider();

vi.mock("../src/data/factory", () => ({
  get dataProvider() {
    return mockProvider;
  },
}));

afterEach(() => {
  vi.restoreAllMocks();
  mockProvider = fakeProvider();
});

async function renderApp(initialPath = "/") {
  const { App } = await import("../src/App");
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App shell", () => {
  it("renders the sidebar with all 10 sections", async () => {
    await renderApp();
    const nav = await screen.findByRole("navigation", { name: "Main navigation" });
    for (const label of [
      "AI Briefing",
      "Decision Center",
      "Opportunity Center",
      "Market Intelligence",
      "Research Center",
      "Knowledge Graph",
      "Mission Control",
      "Source Intelligence",
      "System Administration",
    ]) {
      expect(within(nav).getByText(label)).toBeInTheDocument();
    }
  });

  it("routes to Decision Center", async () => {
    await renderApp("/decisions");
    expect(await screen.findByText("Your current holdings")).toBeInTheDocument();
  });

  it("links from AI Briefing to Decision Center", async () => {
    await renderApp("/");
    const link = await screen.findByRole("link", { name: "Open Decision Center" });
    expect(link).toHaveAttribute("href", "/decisions");
  });

  it("routes to the Opportunity Center", async () => {
    await renderApp("/opportunities");
    expect(await screen.findByText("No opportunities yet")).toBeInTheDocument();
  });

  it("routes to Market Intelligence", async () => {
    await renderApp("/market");
    expect(await screen.findByText("No market state yet")).toBeInTheDocument();
  });

  it("routes to the Research Center", async () => {
    await renderApp("/research");
    expect(await screen.findByText("No hypotheses yet")).toBeInTheDocument();
  });

  it("routes to the Knowledge Graph", async () => {
    await renderApp("/knowledge-graph");
    expect(await screen.findByText("No graph data yet")).toBeInTheDocument();
  });

  it("routes to Mission Control", async () => {
    await renderApp("/mission-control");
    expect(await screen.findByText("No mission status yet")).toBeInTheDocument();
  });

  it("routes to Source Intelligence", async () => {
    await renderApp("/sources");
    expect(await screen.findByText("No sources registered yet")).toBeInTheDocument();
  });

  it("routes to System Administration", async () => {
    await renderApp("/admin");
    expect(await screen.findByText("No execution report yet")).toBeInTheDocument();
  });
});

describe("Universe propagation", () => {
  it("renders every Decision Readiness row when the universe grows beyond ten", async () => {
    const tickers = Array.from({ length: 12 }, (_, index) => `T${String(index + 1).padStart(2, "0")}`);
    mockProvider = fakeProvider({
      getUniverse: async () => ({
        as_of: "2026-07-26",
        count: tickers.length,
        tickers,
        constituents: Object.fromEntries(tickers.map((ticker) => [ticker, ticker])),
      }),
      getDecisionReadiness: async () =>
        tickers.map((ticker) => ({
          ticker,
          as_of: "2026-07-26",
          status: "blocked" as const,
          decision: "abstain" as const,
          ready_horizons: [],
          price_observations: 0,
          latest_price_date: null,
          news_items: 0,
          corporate_events: 0,
          financial_periods: 0,
          fair_value_available: false,
          price_vs_fair_value_pct: null,
          macro_series: 0,
          active_knowledge: 0,
          blockers: ["No data"],
          next_actions: [],
        })),
    });

    await renderApp("/opportunities");

    expect(await screen.findByText("T12")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(13);
  });
});

describe("AI Briefing", () => {
  it("shows the full 101-security universe with explicit abstention when no decision exists", async () => {
    const tickers = Array.from({ length: 101 }, (_, index) => `S${String(index + 1).padStart(3, "0")}`);
    mockProvider = fakeProvider({
      getUniverse: async () => ({
        as_of: "2026-07-31",
        count: tickers.length,
        tickers,
        constituents: Object.fromEntries(tickers.map((ticker) => [ticker, `Company ${ticker}`])),
      }),
    });
    await renderApp("/");
    expect(await screen.findByText("S101")).toBeInTheDocument();
    expect(screen.getByText("101 securities")).toBeInTheDocument();
    expect(screen.getAllByText("Abstain").length).toBeGreaterThanOrEqual(303);
  });

  it("shows empty states when no artifacts have been produced yet", async () => {
    mockProvider = fakeProvider();
    await renderApp("/");
    expect(await screen.findByText(/No opportunities yet/)).toBeInTheDocument();
    expect(await screen.findByText(/No elevated-severity events/)).toBeInTheDocument();
  });

  it("renders a top opportunity from the recommendations artifact", async () => {
    mockProvider = fakeProvider({
      getRecommendations: async () => [
        {
          ticker: "COMI",
          as_of: "2026-07-22",
          combined_expected_return: 0.05,
          combined_expected_risk: 0.03,
          confidence: 0.82,
          horizon_predictions: {},
          supporting_knowledge_ids: [],
          explanation: {
            why_this_stock: "",
            why_now: "",
            why_not_others: "",
            supporting_evidence: [],
            evidence_refs: [],
            similar_historical_cases: [],
            invalidation_conditions: [],
          },
          provenance: { produced_by: "test", produced_at: "2026-07-22T00:00:00", inputs: [] },
        },
      ],
    });
    await renderApp("/");
    expect((await screen.findAllByText("COMI")).length).toBeGreaterThan(0);
  });
});

describe("Company Research Workspace", () => {
  it("shows an honest empty state when the ticker has no recommendation or knowledge", async () => {
    await renderApp("/company/COMI");
    expect(await screen.findByText("No active recommendation")).toBeInTheDocument();
    expect(await screen.findByText("No knowledge objects yet")).toBeInTheDocument();
  });
});
