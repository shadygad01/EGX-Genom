import type { ReactNode } from "react";
import { ProvenanceBanner } from "../primitives/ProvenanceBanner";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import styles from "./AppShell.module.css";

export interface AppShellProps {
  children: ReactNode;
}

/** The persistent frame -- left nav across all 7 sections plus the status
 * top bar -- every routed page renders inside this, never its own layout.
 * ProvenanceBanner sits above every page's own content (AD-64): whether
 * the data behind this dashboard is verified as a real GitHub Actions
 * production run is a fact about the whole bundle, not one page's
 * concern, so it can never be missed by only visiting some routes. */
export function AppShell({ children }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.main}>
        <TopBar />
        <ProvenanceBanner />
        <main id="main-content" className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  );
}
