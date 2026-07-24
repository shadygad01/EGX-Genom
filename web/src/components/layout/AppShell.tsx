import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import styles from "./AppShell.module.css";

export interface AppShellProps {
  children: ReactNode;
}

/** The persistent frame -- left nav across all 9 sections plus the status
 * top bar -- every routed page renders inside this, never its own layout. */
export function AppShell({ children }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <div className={styles.main}>
        <TopBar />
        <main id="main-content" className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  );
}
