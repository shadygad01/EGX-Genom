/**
 * One-off feasibility probe for Yahoo's chart endpoint.
 *
 * This is not a price collector: it never persists bars. It records only
 * availability, schema completeness, row counts, bounds, and corporate-action
 * event presence for the canonical universe.
 */

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../..");
const outputDir = resolve(root, "docs/evidence/egx-price-feasibility-2026-07-26");
const sample = new Set(["ABUK", "COMI", "TMGH", "HRHO", "ETEL", "EAST", "SWDY", "EFIH", "MFPC", "ORWE"]);

function parseTickers(csv) {
  return csv.trim().split(/\r?\n/).slice(1).map((line) => line.split(",", 1)[0]);
}

async function probe(ticker) {
  const yahooSymbol = `${ticker}.CA`;
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(yahooSymbol)}?range=max&interval=1d&events=div%2Csplits`;
  const started = Date.now();
  try {
    const response = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 AGX-Feasibility-Audit/1.0" },
      signal: AbortSignal.timeout(30_000),
    });
    const body = await response.json().catch(() => null);
    const result = body?.chart?.result?.[0];
    const quote = result?.indicators?.quote?.[0];
    const timestamps = result?.timestamp ?? [];
    const fields = ["open", "high", "low", "close", "volume"];
    const completeRows = timestamps.reduce((count, _timestamp, index) => (
      fields.every((field) => quote?.[field]?.[index] !== null && quote?.[field]?.[index] !== undefined)
        ? count + 1 : count
    ), 0);
    return {
      ticker,
      yahoo_symbol: yahooSymbol,
      sample: sample.has(ticker),
      http_status: response.status,
      supported: response.ok && Boolean(result) && completeRows > 0,
      row_count: timestamps.length,
      complete_ohlcv_row_count: completeRows,
      first_date: timestamps.length ? new Date(timestamps[0] * 1000).toISOString().slice(0, 10) : null,
      last_date: timestamps.length ? new Date(timestamps.at(-1) * 1000).toISOString().slice(0, 10) : null,
      has_ohlc: fields.slice(0, 4).every((field) => Array.isArray(quote?.[field])),
      has_volume: Array.isArray(quote?.volume),
      has_adjusted_close: Array.isArray(result?.indicators?.adjclose?.[0]?.adjclose),
      dividend_event_count: Object.keys(result?.events?.dividends ?? {}).length,
      split_event_count: Object.keys(result?.events?.splits ?? {}).length,
      error: body?.chart?.error?.description ?? (!response.ok ? `HTTP ${response.status}` : null),
      elapsed_ms: Date.now() - started,
    };
  } catch (error) {
    return {
      ticker,
      yahoo_symbol: yahooSymbol,
      sample: sample.has(ticker),
      http_status: null,
      supported: false,
      row_count: 0,
      complete_ohlcv_row_count: 0,
      first_date: null,
      last_date: null,
      has_ohlc: false,
      has_volume: false,
      has_adjusted_close: false,
      dividend_event_count: 0,
      split_event_count: 0,
      error: String(error),
      elapsed_ms: Date.now() - started,
    };
  }
}

async function mapWithConcurrency(items, concurrency, fn) {
  const results = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const index = next++;
      results[index] = await fn(items[index]);
    }
  }
  await Promise.all(Array.from({ length: concurrency }, worker));
  return results;
}

const egx30 = parseTickers(await readFile(resolve(root, "research/data/universe/EGX30.csv"), "utf8"));
const egx70 = parseTickers(await readFile(resolve(root, "research/data/universe/EGX70.csv"), "utf8"));
const tickers = [...egx30, ...egx70];
const results = await mapWithConcurrency(tickers, 3, probe);
const supported = results.filter((item) => item.supported);
const lastDateDistribution = Object.fromEntries(
  Object.entries(Object.groupBy(supported, (item) => item.last_date))
    .map(([date, items]) => [date, items.length]),
);
const artifact = {
  schema_version: "1.0.0",
  probed_at: new Date().toISOString(),
  endpoint: "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.CA?range=max&interval=1d&events=div%2Csplits",
  warning: "Technical reachability evidence only. This artifact does not grant a data license.",
  requested_count: results.length,
  supported_count: supported.length,
  coverage_percent: Number((supported.length / results.length * 100).toFixed(2)),
  sample_supported_count: results.filter((item) => item.sample && item.supported).length,
  last_date_distribution: lastDateDistribution,
  results,
};
await mkdir(outputDir, { recursive: true });
await writeFile(resolve(outputDir, "yahoo_live_probe.json"), `${JSON.stringify(artifact, null, 2)}\n`, "utf8");
console.log(JSON.stringify({
  requested_count: artifact.requested_count,
  supported_count: artifact.supported_count,
  coverage_percent: artifact.coverage_percent,
  sample_supported_count: artifact.sample_supported_count,
  missing: results.filter((item) => !item.supported).map((item) => ({ ticker: item.ticker, status: item.http_status, error: item.error })),
}, null, 2));
