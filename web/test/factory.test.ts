import { describe, expect, it } from "vitest";
import { ApiProvider } from "../src/data/ApiProvider";
import { createDataProvider } from "../src/data/factory";
import { StaticJsonProvider } from "../src/data/StaticJsonProvider";

describe("createDataProvider", () => {
  it("'static' returns a StaticJsonProvider", () => {
    expect(createDataProvider("static")).toBeInstanceOf(StaticJsonProvider);
  });

  it("'api' returns an ApiProvider", () => {
    expect(createDataProvider("api")).toBeInstanceOf(ApiProvider);
  });

  it("switching kinds requires only the config argument, no other code change", () => {
    const providers = (["static", "api"] as const).map((kind) => createDataProvider(kind));
    expect(providers[0]).toBeInstanceOf(StaticJsonProvider);
    expect(providers[1]).toBeInstanceOf(ApiProvider);
  });

  it("rejects an unknown provider kind", () => {
    // @ts-expect-error -- deliberately invalid input
    expect(() => createDataProvider("bogus")).toThrow(/Unknown VITE_DATA_PROVIDER/);
  });
});
