// Which provider the dashboard uses is pure configuration: VITE_DATA_PROVIDER
// ("static" | "api"), set per Vite mode in web/.env.production (static, for
// the GitHub Pages build) and web/.env.development (api, for local dev
// against `npm run dev -w api`). No component imports StaticJsonProvider or
// ApiProvider directly -- only this factory does, so switching providers
// never touches React code, exactly per the dual-provider architecture in
// docs/ARCHITECTURE.md.

import { ApiProvider } from "./ApiProvider";
import type { DashboardDataProvider } from "./DataProvider";
import { StaticJsonProvider } from "./StaticJsonProvider";

export type ProviderKind = "static" | "api";

export function createDataProvider(kind?: ProviderKind): DashboardDataProvider {
  const resolved = kind ?? (import.meta.env.VITE_DATA_PROVIDER as ProviderKind | undefined) ?? "static";
  switch (resolved) {
    case "api":
      return new ApiProvider();
    case "static":
      return new StaticJsonProvider();
    default:
      throw new Error(`Unknown VITE_DATA_PROVIDER: ${resolved}`);
  }
}

export const dataProvider: DashboardDataProvider = createDataProvider();
