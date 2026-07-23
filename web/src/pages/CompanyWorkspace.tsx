import { useParams } from "react-router-dom";
import { ComingSoon } from "./ComingSoon";

export function CompanyWorkspace() {
  const { ticker } = useParams<{ ticker: string }>();
  return (
    <ComingSoon
      title={`Company Research Workspace — ${ticker ?? ""}`}
      detail="Investment thesis, knowledge timeline, financials, evidence, and lineage for this company. Next milestone."
    />
  );
}
