/** One-off page/schema probe. No third-party OHLCV rows are persisted. */

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "../..");
const outputDir = resolve(root, "docs/evidence/egx-price-feasibility-2026-07-26");

function tickers(csv) {
  return csv.trim().split(/\r?\n/).slice(1).map((line) => line.split(",", 1)[0]);
}

async function request(symbol) {
  const url = `https://stockanalysis.com/quote/egx/${symbol}/history/`;
  try {
    const response = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 AGX-Feasibility-Audit/1.0" },
      signal: AbortSignal.timeout(30_000),
    });
    const html = await response.text();
    const hasSchema = /Historical Stock Price Data|Stock Price History/.test(html)
      && /data:\[\{a:[^}]+c:[^}]+h:[^}]+l:[^}]+o:[^}]+t:"\d{4}-\d{2}-\d{2}"[^}]+v:/.test(html);
    const dates = [...html.matchAll(/t:"(\d{4}-\d{2}-\d{2})"/g)].map((match) => match[1]);
    return {
      symbol, url, http_status: response.status,
      supported: response.ok && hasSchema,
      visible_row_count: new Set(dates).size,
      newest_visible_date: dates[0] ?? null,
      oldest_visible_date: dates.at(-1) ?? null,
      has_ohlcv_schema: hasSchema,
    };
  } catch (error) {
    return { symbol, url, http_status: null, supported: false, visible_row_count: 0,
      newest_visible_date: null, oldest_visible_date: null, has_ohlcv_schema: false,
      error: String(error) };
  }
}

async function probe(ticker) {
  const primary = await request(ticker);
  if (primary.supported) return { ticker, ...primary };
  const fallback = await request(`${ticker}.CA`);
  return { ticker, ...fallback, attempted_symbols: [ticker, `${ticker}.CA`] };
}

async function mapLimited(items, concurrency, fn) {
  const output = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (cursor < items.length) {
      const index = cursor++;
      output[index] = await fn(items[index]);
    }
  }
  await Promise.all(Array.from({ length: concurrency }, worker));
  return output;
}

const universe = [
  ...tickers(await readFile(resolve(root, "research/data/universe/EGX30.csv"), "utf8")),
  ...tickers(await readFile(resolve(root, "research/data/universe/EGX70.csv"), "utf8")),
];
const results = await mapLimited(universe, 3, probe);
const supported = results.filter((result) => result.supported);
const artifact = {
  schema_version: "1.0.0",
  probed_at: new Date().toISOString(),
  warning: "Technical page/schema evidence only. No price rows are retained and this is not a license grant.",
  requested_count: results.length,
  supported_count: supported.length,
  coverage_percent: Number((supported.length / results.length * 100).toFixed(2)),
  results,
};
await mkdir(outputDir, { recursive: true });
await writeFile(resolve(outputDir, "stockanalysis_live_probe.json"), `${JSON.stringify(artifact, null, 2)}\n`, "utf8");
console.log(JSON.stringify({
  requested_count: artifact.requested_count,
  supported_count: artifact.supported_count,
  coverage_percent: artifact.coverage_percent,
  missing: results.filter((result) => !result.supported).map((result) => result.ticker),
}, null, 2));
