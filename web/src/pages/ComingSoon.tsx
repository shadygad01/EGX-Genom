import { useTranslation } from "react-i18next";
import { Card } from "../components/primitives/Card";
import { EmptyState } from "../components/primitives/States";

export interface ComingSoonProps {
  title: string;
  detail: string;
}

/** Placeholder for a section not yet built -- an honest "not yet," never a
 * fabricated screen, while the remaining 9-section rollout is in progress. */
export function ComingSoon({ title, detail }: ComingSoonProps) {
  const { t } = useTranslation("common");
  return (
    <Card title={title}>
      <EmptyState title={t("states.underConstruction")} detail={detail} icon="◌" />
    </Card>
  );
}
