import { useTranslation } from "react-i18next";
import { useArtifact } from "../../hooks/useArtifact";
import { provenanceIssue } from "../../lib/provenance";
import styles from "./ProvenanceBanner.module.css";

/** Global, non-dismissible notice shown on every page whenever the
 * dashboard data currently being served cannot be verified as having
 * come from the canonical GitHub Actions production workflow (AD-64,
 * docs/ARCHITECTURE_DECISIONS.md). Absent entirely when the manifest
 * checks out -- this is a warning surface, not decoration, and must
 * never render "everything's fine" chrome of its own. */
export function ProvenanceBanner() {
  const { t } = useTranslation("common");
  const manifest = useArtifact((p) => p.getArtifactManifest());

  if (manifest.loading || manifest.error) return null;
  const issue = provenanceIssue(manifest.data);
  if (issue === null) return null;

  const detailKey =
    issue === "missing_manifest"
      ? "provenanceBanner.detailMissing"
      : issue === "non_live_mode"
        ? "provenanceBanner.detailMode"
        : "provenanceBanner.detailWorkflow";

  return (
    <div className={styles.banner} role="alert">
      <span className={styles.icon} aria-hidden="true">⚠</span>
      <div>
        <strong className={styles.title}>{t("provenanceBanner.title")}</strong>
        <span className={styles.detail}>
          {" "}
          {t(detailKey, {
            mode: manifest.data?.pipeline_mode ?? "unknown",
          })}
        </span>
      </div>
    </div>
  );
}
