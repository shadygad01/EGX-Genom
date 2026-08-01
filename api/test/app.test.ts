import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const fixturePath = path.resolve(__dirname, "fixtures/knowledge_store.json");
const emptyStorePath = path.resolve(__dirname, "fixtures/does_not_exist.json");
const eventsFixturePath = path.resolve(__dirname, "fixtures/events_store.json");
const runsFixturePath = path.resolve(__dirname, "fixtures/runs_store.json");
const artifactsFixtureDir = path.resolve(__dirname, "fixtures/dashboard");
const emptyArtifactsDir = path.resolve(__dirname, "fixtures/does_not_exist_dir");

function testApp(overrides: Partial<Parameters<typeof buildApp>[0]> = {}) {
  return buildApp({
    knowledgeStorePath: fixturePath,
    eventsStorePath: emptyStorePath,
    runsStorePath: emptyStorePath,
    artifactsDir: emptyArtifactsDir,
    decisionDataDir: null,
    universeSeedDir: path.resolve(__dirname, "fixtures"),
    researchDir: path.resolve(__dirname, "../.."),
    ...overrides,
  });
}

describe("GET /health", () => {
  it("returns ok", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/health" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({ status: "ok" });
  });
});

describe("GET /knowledge", () => {
  it("returns the latest revision of every knowledge object", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/knowledge" });
    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body).toHaveLength(1);
    expect(body[0].id).toBe("egx-test-knowledge");
    expect(body[0].version).toBe(2);
    expect(body[0].status).toBe("monitoring");
  });

  it("returns an empty array when the store file does not exist", async () => {
    const app = testApp({ knowledgeStorePath: emptyStorePath });
    const response = await app.inject({ method: "GET", url: "/knowledge" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual([]);
  });
});

describe("GET /knowledge/:id", () => {
  it("returns the latest revision for a known id", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/knowledge/egx-test-knowledge" });
    expect(response.statusCode).toBe(200);
    expect(response.json().version).toBe(2);
  });

  it("returns 404 for an unknown id", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/knowledge/does-not-exist" });
    expect(response.statusCode).toBe(404);
  });
});

describe("GET /knowledge/:id/revisions", () => {
  it("returns every revision in order", async () => {
    const app = testApp();
    const response = await app.inject({
      method: "GET",
      url: "/knowledge/egx-test-knowledge/revisions",
    });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toHaveLength(2);
  });
});

describe("GET /events", () => {
  it("returns the latest revision of every event", async () => {
    const app = testApp({ eventsStorePath: eventsFixturePath });
    const response = await app.inject({ method: "GET", url: "/events" });
    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body).toHaveLength(1);
    expect(body[0].id).toBe("evt-test");
  });

  it("returns an empty array when the store file does not exist", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/events" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual([]);
  });
});

describe("GET /runtime-metrics", () => {
  it("returns the latest revision of every run record", async () => {
    const app = testApp({ runsStorePath: runsFixturePath });
    const response = await app.inject({ method: "GET", url: "/runtime-metrics" });
    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body).toHaveLength(1);
    expect(body[0].status).toBe("succeeded");
  });
});

describe("dashboard artifact routes", () => {
  it("GET /patterns returns [] when no artifact directory exists", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/patterns" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual([]);
  });

  it("GET /recommendations returns [] when no artifact directory exists", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/recommendations" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual([]);
  });

  it("GET /market-state returns null when no artifact directory exists", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/market-state" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toBeNull();
  });

  it("GET /universe returns null when no artifact directory exists", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/universe" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toBeNull();
  });

  it("GET /system-status returns null when no artifact directory exists", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/system-status" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toBeNull();
  });

  it("GET /source-registry reads the generated artifact file", async () => {
    const app = testApp({ artifactsDir: artifactsFixtureDir });
    const response = await app.inject({ method: "GET", url: "/source-registry" });
    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body).toHaveLength(1);
    expect(body[0].id).toBe("stooq");
  });

  it("GET /publication-gate fails closed to null when no report exists", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/publication-gate" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toBeNull();
  });

  it("GET /ticker-data-gaps returns an honest empty list when absent", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/ticker-data-gaps" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual([]);
  });

  it("GET /financial-coverage returns null when the report is absent", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/financial-coverage" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toBeNull();
  });

  it("GET /market-breadth returns null when the report is absent", async () => {
    const app = testApp();
    const response = await app.inject({ method: "GET", url: "/market-breadth" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toBeNull();
  });
});

describe("POST /decisions", () => {
  it("reports 501 when DECISION_DATA_DIR is unconfigured, never guessing a directory", async () => {
    const app = testApp();
    const response = await app.inject({
      method: "POST",
      url: "/decisions",
      payload: { date: "2026-06-14" },
    });
    expect(response.statusCode).toBe(501);
    expect(response.json().error).toMatch(/DECISION_DATA_DIR/);
  });

  it("rejects a missing/malformed date before ever configuring a run", async () => {
    const app = testApp({ decisionDataDir: "/tmp/does-not-matter" });
    const response = await app.inject({
      method: "POST",
      url: "/decisions",
      payload: { date: "not-a-date" },
    });
    expect(response.statusCode).toBe(400);
  });

  it("rejects a malformed position entry", async () => {
    const app = testApp({ decisionDataDir: "/tmp/does-not-matter" });
    const response = await app.inject({
      method: "POST",
      url: "/decisions",
      payload: { date: "2026-06-14", positions: { COMI: { held: "yes" } } },
    });
    expect(response.statusCode).toBe(400);
  });

  it("rejects a ticker key that isn't a plain identifier", async () => {
    const app = testApp({ decisionDataDir: "/tmp/does-not-matter" });
    const response = await app.inject({
      method: "POST",
      url: "/decisions",
      payload: { date: "2026-06-14", positions: { "../etc/passwd": { held: true } } },
    });
    expect(response.statusCode).toBe(400);
  });
});
