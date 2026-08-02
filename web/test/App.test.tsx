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
    getClaims: async () => [],
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
    getSystemMaturity: async () => null,
    getDiscoveryReport: async () => [],
    getDiscoveryMetrics: async () => null,
    getEndpointCandidates: async () => [],
    getPortfolioSummary: async () => null,
    getWarnings: async () => null,
    getCommitteeSummary: async () => null,
    getShadowFund: async () => null,
    getShadowFundHistory: async () => ({ nav_series: [], transactions: [] }),
    postDecisions: async () => [],
    postCapitalAllocation: async () => ({
      as_of: "2026-07-22",
      ranking: [],
      queue: [],
      capital_released_today: [],
      capital_recycled: [],
      best_new_opportunities: [],
      highest_opportunity_cost: [],
      allocation_changes: [],
      cash_waiting: { idle_cash_before: 1, idle_cash_after: 1, reason: "test" },
      explanation: { why_this_stock: "", why_now: "", why_not_others: "" },
      provenance: { produced_by: "test", produced_at: "2026-07-22T00:00:00", inputs: [] },
    }),
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
    expect(screen.getByText("Capital Allocation")).toBeInTheDocument();
    expect(screen.getByText("Portfolio Summary")).toBeInTheDocument();
    expect(screen.getByText("Warnings")).toBeInTheDocument();
    expect(screen.getByText("Investment Committee Summary")).toBeInTheDocument();
  });

  it("renders the Capital Allocation deployment queue live when holdings are saved", async () => {
    window.localStorage.setItem(
      "agx.portfolio.positions.v1",
      JSON.stringify([{ ticker: "COMI", currentWeight: 0.05, averageCost: 60 }])
    );
    mockProvider = fakeProvider({
      postDecisions: async () => [],
      postCapitalAllocation: async () => ({
        as_of: "2026-07-22",
        ranking: [
          {
            rank: 1,
            ticker: "ETEL",
            opportunity_score: 1.5,
            action: "buy",
            target_weight: 0.2,
            current_weight: 0,
            confidence: 0.8,
            expected_return: 0.1,
            expected_risk: 0.04,
            is_new_position: true,
          },
        ],
        queue: [
          {
            ticker: "ETEL",
            priority: 1,
            action: "buy",
            target_weight: 0.2,
            current_weight: 0,
            capital_delta: 0.2,
            expected_contribution: 0.02,
            marginal_benefit: 1.5,
            marginal_risk: 0.04,
            capital_sources: [{ ticker: null, amount: 0.2 }],
            required_action: "Buy ETEL to 20.00%, funded by idle cash: 20.00%.",
            opportunity_cost_note: "Every ticker with a positive opportunity score is already funded; no rejected alternative exists today.",
          },
        ],
        capital_released_today: [],
        capital_recycled: [],
        best_new_opportunities: [
          {
            rank: 1,
            ticker: "ETEL",
            opportunity_score: 1.5,
            action: "buy",
            target_weight: 0.2,
            current_weight: 0,
            confidence: 0.8,
            expected_return: 0.1,
            expected_risk: 0.04,
            is_new_position: true,
          },
        ],
        highest_opportunity_cost: [],
        allocation_changes: [
          { ticker: "ETEL", action: "buy", current_weight: 0, target_weight: 0.2, capital_delta: 0.2 },
        ],
        cash_waiting: { idle_cash_before: 0.95, idle_cash_after: 0.75, reason: "test reason" },
        explanation: { why_this_stock: "", why_now: "", why_not_others: "" },
        provenance: { produced_by: "test", produced_at: "2026-07-22T00:00:00", inputs: [] },
      }),
    });
    await renderApp("/");
    expect(await screen.findByText("Capital Deployment Queue")).toBeInTheDocument();
    expect(await screen.findByText(/Buy ETEL to 20\.00%/)).toBeInTheDocument();
    expect(screen.getByText("Capital Recycling")).toBeInTheDocument();
    expect(screen.getByText("Capital Released Today")).toBeInTheDocument();
    expect(screen.getByText("Best New Opportunities")).toBeInTheDocument();
    expect(screen.getByText("Highest Opportunity Cost")).toBeInTheDocument();
    expect(screen.getByText("Allocation Changes")).toBeInTheDocument();
    expect(screen.getByText("Capital Waiting For Better Opportunities")).toBeInTheDocument();
    expect(screen.getByText("test reason")).toBeInTheDocument();
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
