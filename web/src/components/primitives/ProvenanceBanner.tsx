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

  // Only the loading state stays silent. A fetch failure (network error, an
  // older API with no /manifest route) is its own distinct warning -- it
  // must never be conflated with "the request succeeded and returned no
  // manifest," which is what provenanceIssue's "missing_manifest" means.
  if (manifest.loading) return null;

  const detailKey = manifest.error
    ? "provenanceBanner.detailError"
    : (() => {
        const issue = provenanceIssue(manifest.data);
        return issue === null
          ? null
          : issue === "missing_manifest"
            ? "provenanceBanner.detailMissing"
            : issue === "non_live_mode"
              ? "provenanceBanner.detailMode"
              : "provenanceBanner.detailWorkflow";
      })();
  if (detailKey === null) return null;

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
