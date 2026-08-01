import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { AIBriefing } from "./pages/AIBriefing";
import { CompanyWorkspace } from "./pages/CompanyWorkspace";
import { DecisionCenter } from "./pages/DecisionCenter";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraphPage";
import { MarketIntelligence } from "./pages/MarketIntelligence";
import { MissionControlPage } from "./pages/MissionControlPage";
import { OpportunityCenter } from "./pages/OpportunityCenter";
import { ResearchCenter } from "./pages/ResearchCenter";
import { SourceIntelligence } from "./pages/SourceIntelligence";
import { SystemAdministration } from "./pages/SystemAdministration";

/** The routed shell for all 9 sections. Each page pulls its own data via
 * useArtifact/DashboardDataProvider -- App only wires paths to pages. */
export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<AIBriefing />} />
        <Route path="/decisions" element={<DecisionCenter />} />
        <Route path="/opportunities" element={<OpportunityCenter />} />
        <Route path="/company/:ticker" element={<CompanyWorkspace />} />
        <Route path="/market" element={<MarketIntelligence />} />
        <Route path="/research" element={<ResearchCenter />} />
        <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
        <Route path="/mission-control" element={<MissionControlPage />} />
        <Route path="/sources" element={<SourceIntelligence />} />
        <Route path="/admin" element={<SystemAdministration />} />
      </Routes>
    </AppShell>
  );
}
