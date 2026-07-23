import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const fixturePath = path.resolve(__dirname, "fixtures/knowledge_store.json");
const emptyStorePath = path.resolve(__dirname, "fixtures/does_not_exist.json");

describe("GET /health", () => {
  it("returns ok", async () => {
    const app = buildApp(fixturePath);
    const response = await app.inject({ method: "GET", url: "/health" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({ status: "ok" });
  });
});

describe("GET /knowledge", () => {
  it("returns the latest revision of every knowledge object", async () => {
    const app = buildApp(fixturePath);
    const response = await app.inject({ method: "GET", url: "/knowledge" });
    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body).toHaveLength(1);
    expect(body[0].id).toBe("egx-test-knowledge");
    expect(body[0].version).toBe(2);
    expect(body[0].status).toBe("monitoring");
  });

  it("returns an empty array when the store file does not exist", async () => {
    const app = buildApp(emptyStorePath);
    const response = await app.inject({ method: "GET", url: "/knowledge" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual([]);
  });
});

describe("GET /knowledge/:id", () => {
  it("returns the latest revision for a known id", async () => {
    const app = buildApp(fixturePath);
    const response = await app.inject({ method: "GET", url: "/knowledge/egx-test-knowledge" });
    expect(response.statusCode).toBe(200);
    expect(response.json().version).toBe(2);
  });

  it("returns 404 for an unknown id", async () => {
    const app = buildApp(fixturePath);
    const response = await app.inject({ method: "GET", url: "/knowledge/does-not-exist" });
    expect(response.statusCode).toBe(404);
  });
});

describe("GET /knowledge/:id/revisions", () => {
  it("returns every revision in order", async () => {
    const app = buildApp(fixturePath);
    const response = await app.inject({
      method: "GET",
      url: "/knowledge/egx-test-knowledge/revisions",
    });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toHaveLength(2);
  });
});
