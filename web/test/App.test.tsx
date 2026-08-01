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
    getMarketRegime: async () => null,
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
    getPortfolioSummary: async () => null,
    getWarnings: async () => null,
    getCommitteeSummary: async () => null,
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
  window.localStorage.clear();
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
  it("renders the sidebar with all 7 sections", async () => {
    await renderApp();
    const nav = await screen.findByRole("navigation", { name: "Main navigation" });
    for (const label of [
      "CIO Desk",
      "Portfolio",
      "Investment Cases",
      "Monitoring",
      "Market",
      "Research",
      "Settings",
    ]) {
      expect(within(nav).getByText(label)).toBeInTheDocument();
    }
  });

  it("routes to Portfolio", async () => {
    await renderApp("/portfolio");
    expect(await screen.findByText("Your current holdings")).toBeInTheDocument();
  });

  it("routes to Investment Cases", async () => {
    await renderApp("/cases");
    expect(await screen.findByText("No investment cases yet")).toBeInTheDocument();
  });

  it("routes to an Investment Case detail page", async () => {
    await renderApp("/cases/COMI");
    expect(await screen.findByText("No investment case for this ticker")).toBeInTheDocument();
  });

  it("routes to Monitoring", async () => {
    await renderApp("/monitoring");
    expect(await screen.findByText("No warnings")).toBeInTheDocument();
  });

  it("routes to Market", async () => {
    await renderApp("/market");
    expect(await screen.findByText("No market state yet")).toBeInTheDocument();
  });

  it("routes to Research", async () => {
    await renderApp("/research");
    expect(await screen.findByText("No hypotheses yet")).toBeInTheDocument();
  });

  it("routes to the Knowledge Graph (reachable, not a top-level nav item)", async () => {
    await renderApp("/knowledge-graph");
    expect(await screen.findByText("No graph data yet")).toBeInTheDocument();
  });

  it("routes to Source Intelligence (reachable, not a top-level nav item)", async () => {
    await renderApp("/sources");
    expect(await screen.findByText("No sources registered yet")).toBeInTheDocument();
  });

  it("routes to Settings", async () => {
    await renderApp("/settings");
    expect(await screen.findByText("No mission status yet")).toBeInTheDocument();
    expect(await screen.findByText("No execution report yet")).toBeInTheDocument();
  });
});

describe("CIO Desk", () => {
  it("answers 'what should I do today' with only the 5 mandated sections", async () => {
    await renderApp("/");
    expect(await screen.findByText("Market Regime")).toBeInTheDocument();
    expect(screen.getByText("Today's Actions")).toBeInTheDocument();
    expect(screen.getByText("Portfolio Summary")).toBeInTheDocument();
    expect(screen.getByText("Warnings")).toBeInTheDocument();
    expect(screen.getByText("Investment Committee Summary")).toBeInTheDocument();
  });

  it("prompts to add holdings when none are saved, linking to Portfolio", async () => {
    await renderApp("/");
    const link = await screen.findByRole("link", { name: /Go to Portfolio/ });
    expect(link).toHaveAttribute("href", "/portfolio");
  });

  it("shows model-portfolio opportunities (not personalized) when no holdings are saved", async () => {
    mockProvider = fakeProvider({
      getInvestmentCases: async () => ({
        as_of: "2026-07-22",
        recommendations: [
          {
            ticker: "COMI",
            as_of: "2026-07-22",
            combined_expected_return: 0.05,
            combined_expected_risk: 0.03,
            confidence: 0.82,
            horizon_predictions: {},
            supporting_knowledge_ids: [],
            explanation: {
              why_this_stock: "Strong fundamentals",
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
        portfolio: {
          id: "p1",
          version: 1,
          as_of: "2026-07-22",
          positions: [
            {
              ticker: "COMI",
              weight: 0.1,
              score: 1.2,
              expected_return: 0.05,
              expected_risk: 0.03,
              confidence: 0.82,
              supporting_knowledge_ids: [],
            },
          ],
          cash_weight: 0.9,
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
      }),
    });
    await renderApp("/");
    expect((await screen.findAllByText("COMI")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Suggested").length).toBeGreaterThan(0);
  });
});

describe("Universe propagation (Research → Data Readiness)", () => {
  it("renders every Decision Readiness row when the universe grows beyond ten", async () => {
    const tickers = Array.from({ length: 12 }, (_, index) => `T${String(index + 1).padStart(2, "0")}`);
    mockProvider = fakeProvider({
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

    await renderApp("/research");

    expect(await screen.findByText("T12")).toBeInTheDocument();
  });
});
