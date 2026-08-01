import { useCallback, useEffect, useState } from "react";
import type { PositionInput } from "../types";

const STORAGE_KEY = "agx.portfolio.positions.v1";

export interface HeldPosition {
  ticker: string;
  currentWeight: number;
  averageCost: number | null;
}

function load(): HeldPosition[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as HeldPosition[]) : [];
  } catch {
    return [];
  }
}

function save(positions: HeldPosition[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(positions));
  } catch {
    // localStorage unavailable (private browsing, quota, disabled) --
    // holdings simply don't persist across reloads; never a fatal error.
  }
}

/** The investor's own holdings, persisted client-side only -- never sent
 * anywhere except as the `positions` payload of an explicit POST /decisions
 * call the investor's own visit triggers (decision_service stays on-demand
 * only, see CLAUDE.md's decision_service rules: this platform never
 * autonomously discovers or stores real portfolio data). Persisting client-
 * side is what lets the CIO Desk show "today's actions" automatically on a
 * return visit without the backend needing to know anything between calls.
 * Shared by the CIO Desk and Portfolio pages so "my holdings" is exactly
 * one piece of state, never two that could drift apart. */
export function usePortfolioPositions() {
  const [positions, setPositionsState] = useState<HeldPosition[]>(() => load());

  useEffect(() => {
    save(positions);
  }, [positions]);

  const toPositionInputs = useCallback((): Record<string, PositionInput> => {
    const result: Record<string, PositionInput> = {};
    for (const position of positions) {
      const ticker = position.ticker.trim().toUpperCase();
      if (!ticker) continue;
      result[ticker] = {
        held: true,
        current_weight: position.currentWeight,
        average_cost: position.averageCost,
      };
    }
    return result;
  }, [positions]);

  const hasPositions = positions.some((position) => position.ticker.trim().length > 0);

  return { positions, setPositions: setPositionsState, toPositionInputs, hasPositions };
}
