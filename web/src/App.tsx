import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { CIODesk } from "./pages/CIODesk";
import { InvestmentCaseDetail } from "./pages/InvestmentCaseDetail";
import { InvestmentCases } from "./pages/InvestmentCases";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import { MarketIntelligence } from "./pages/MarketIntelligence";
import { Monitoring } from "./pages/Monitoring";
import { Portfolio } from "./pages/Portfolio";
import { ResearchCenter } from "./pages/ResearchCenter";
import { Settings } from "./pages/Settings";
import { SourceIntelligence } from "./pages/SourceIntelligence";

/** The routed shell for the Institutional Investment Operating System's 7
 * nav sections plus 2 deeper, non-nav research routes (Knowledge Graph,
 * Source Intelligence -- reachable from Research, never top-level). Each
 * page pulls its own data via useArtifact/DashboardDataProvider -- App
 * only wires paths to pages. CIO Desk is the landing page: "what should I
 * do today?" answered before any research page is reachable. */
export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<CIODesk />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/cases" element={<InvestmentCases />} />
        <Route path="/cases/:ticker" element={<InvestmentCaseDetail />} />
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/market" element={<MarketIntelligence />} />
        <Route path="/research" element={<ResearchCenter />} />
        <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
        <Route path="/sources" element={<SourceIntelligence />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </AppShell>
  );
}
