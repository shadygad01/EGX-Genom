import { useEffect, useState } from "react";
import type { DashboardDataProvider } from "../data/DataProvider";
import { dataProvider } from "../data/factory";

export interface ArtifactState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  reload: () => void;
}

/** The one hook every page uses to pull an artifact through
 * DashboardDataProvider -- pages never call the provider directly, so
 * loading/error handling is consistent everywhere and never duplicated. */
export function useArtifact<T>(
  fetcher: (provider: DashboardDataProvider) => Promise<T>,
  deps: unknown[] = [],
): ArtifactState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher(dataProvider)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadToken, ...deps]);

  return { data, loading, error, reload: () => setReloadToken((t) => t + 1) };
}
