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
    getSourceMetrics: async () => [],
    getAcquisitionDecisions: async () => [],
    getDecisionReadiness: async () => [],
    getTickerDataGapReport: async () => [],
    getSourceTruth: async () => [],
    getDecisionHistory: async () => [],
    getDecisionPerformance: async () => [],
    getPublicationGate: async () => null,
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
  it("renders the sidebar with all 9 sections", async () => {
    await renderApp();
    const nav = await screen.findByRole("navigation", { name: "Main navigation" });
    for (const label of [
      "الملخص الذكي",
      "مركز القرارات",
      "تحليل السوق",
      "مركز الأبحاث",
      "خريطة المعرفة",
      "مراقبة التشغيل",
      "شفافية المصادر",
      "إدارة النظام",
    ]) {
      expect(within(nav).getByText(label)).toBeInTheDocument();
    }
  });

  it("routes to the Opportunity Center", async () => {
    await renderApp("/opportunities");
    expect(await screen.findByText("لا توجد قرارات بحثية بعد")).toBeInTheDocument();
  });

  it("routes to Market Intelligence", async () => {
    await renderApp("/market");
    expect(await screen.findByText("لا توجد حالة سوق بعد")).toBeInTheDocument();
  });

  it("routes to the Research Center", async () => {
    await renderApp("/research");
    expect(await screen.findByText("لا توجد فرضيات بعد")).toBeInTheDocument();
  });

  it("routes to the Knowledge Graph", async () => {
    await renderApp("/knowledge-graph");
    expect(await screen.findByText("لا توجد بيانات للخريطة بعد")).toBeInTheDocument();
  });

  it("routes to Mission Control", async () => {
    await renderApp("/mission-control");
    expect(await screen.findByText("لا توجد حالة للمهمة بعد")).toBeInTheDocument();
  });

  it("routes to Source Intelligence", async () => {
    await renderApp("/sources");
    expect(await screen.findByText("لا توجد مصادر مسجلة بعد")).toBeInTheDocument();
  });

  it("routes to System Administration", async () => {
    await renderApp("/admin");
    expect(await screen.findByText("لا يوجد تقرير تنفيذ بعد")).toBeInTheDocument();
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

  it("shows the exact missing data layers and next action", async () => {
    mockProvider = fakeProvider({
      getTickerDataGapReport: async () => [{
        ticker: "COMI",
        as_of: "2026-07-26",
        status: "blocked",
        decision: "abstain",
        ready_horizons: [],
        swing_ready: false,
        investment_ready: false,
        price_observations: 30,
        latest_price_date: "2026-07-26",
        layers: [
          { layer: "financials", count: 0, threshold: 2, complete: false, completeness_pct: 0 },
          { layer: "macro", count: 3, threshold: 3, complete: true, completeness_pct: 100 },
        ],
        overall_completeness_pct: 50,
        blockers: ["Missing financials"],
        next_actions: ["اجمع فترتين ماليتين قابلتين للمقارنة."],
      }],
    });

    await renderApp("/opportunities");
    expect(await screen.findByText("القوائم المالية")).toBeInTheDocument();
    expect(screen.getByText("اجمع فترتين ماليتين قابلتين للمقارنة.")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
  });
});

describe("AI Briefing", () => {
  it("shows every failed publication gate before research output", async () => {
    mockProvider = fakeProvider({
      getPublicationGate: async () => ({
        as_of: "2026-07-28",
        publication_ready: false,
        checks: [{
          id: "legal_approval",
          label: "مراجعة قانونية بشرية سارية",
          passed: false,
          evidence_refs: [],
          blocker: "لا توجد موافقة قانونية بشرية كاملة وسارية.",
        }],
        blockers: ["لا توجد موافقة قانونية بشرية كاملة وسارية."],
      }),
    });
    await renderApp("/");
    expect(await screen.findByText("بوابة النشر: محظورة")).toBeInTheDocument();
    expect(screen.getByText(/مراجعة قانونية بشرية سارية/)).toBeInTheDocument();
  });

  it("shows empty states when no artifacts have been produced yet", async () => {
    mockProvider = fakeProvider();
    await renderApp("/");
    expect(await screen.findByText(/لا توجد فرص بعد/)).toBeInTheDocument();
    expect(await screen.findByText(/لا توجد أحداث مرتفعة الشدة/)).toBeInTheDocument();
  });

  it("renders a top opportunity from the recommendations artifact", async () => {
    mockProvider = fakeProvider({
      getPublicationGate: async () => ({
        as_of: "2026-07-22", publication_ready: true, checks: [], blockers: [],
      }),
      getRecommendations: async () => [
        {
          ticker: "COMI",
          as_of: "2026-07-22",
          combined_expected_return: 0.05,
          combined_expected_risk: 0.03,
          confidence: 0.82,
          horizon_predictions: {},
          horizon_decisions: {
            micro: {
              horizon: "micro", horizon_window: "1-3 days", action: "buy_candidate",
              expected_return: 0.05, expected_risk: 0.03,
              risk_metric: "model_expected_risk_for_horizon", confidence: 0.82,
              risk_adjusted_score: 1.37, valid_until: "2026-07-25",
              entry_condition: "test", invalidation_conditions: ["test"],
              max_position_pct: 0.03, publication_status: "publication_ready",
              abstention_reasons: [], evidence_refs: [],
            },
          },
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
    expect(await screen.findByText("لا يوجد قرار نشط")).toBeInTheDocument();
    expect(await screen.findByText("لا توجد كائنات معرفة بعد")).toBeInTheDocument();
  });
});
