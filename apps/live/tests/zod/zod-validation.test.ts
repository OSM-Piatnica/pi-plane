/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@plane/editor/server", () => ({
  convertHTMLDocumentToAllFormats: vi.fn(() => ({ description_json: { type: "doc" }, description_binary: "AAEC" })),
}));
vi.mock("@plane/logger", () => ({ logger: { error: vi.fn(), info: vi.fn(), warn: vi.fn() } }));

const makeRes = () => {
  const res = { status: vi.fn(), json: vi.fn() };
  res.status.mockReturnValue(res);
  res.json.mockReturnValue(res);
  return res;
};

describe("document conversion request validation", () => {
  it("answers 400 with the path and message of each invalid field", async () => {
    const { DocumentController } = await import("@/controllers/document.controller");
    const res = makeRes();
    await new DocumentController().convertDocument(
      { body: { description_html: "", variant: "nope" } } as never,
      res as never
    );
    expect(res.status).toHaveBeenCalledWith(400);
    const { context } = res.json.mock.calls[0][0] as {
      context: { validationErrors: { path: string; message: string }[] };
    };
    const byPath = Object.fromEntries(context.validationErrors.map((e) => [e.path, e.message]));
    expect(byPath.variant).toBeTypeOf("string");
    expect(byPath.description_html).toBeTypeOf("string");
  });

  it("converts a valid body", async () => {
    const { DocumentController } = await import("@/controllers/document.controller");
    const res = makeRes();
    await new DocumentController().convertDocument(
      { body: { description_html: "<p>hello</p>", variant: "rich" } } as never,
      res as never
    );
    expect(res.status).toHaveBeenCalledWith(200);
    expect(res.json).toHaveBeenCalledWith({ description_json: { type: "doc" }, description_binary: "AAEC" });
  });
});

describe("environment validation", () => {
  const original = { ...process.env };
  afterEach(() => {
    process.env = { ...original };
    vi.resetModules();
    vi.restoreAllMocks();
  });

  it("reads defaults and turns the numeric settings into numbers", async () => {
    process.env.API_BASE_URL = "http://api:8000";
    process.env.LIVE_SERVER_SECRET_KEY = "secret";
    delete process.env.COMPRESSION_LEVEL;
    process.env.REDIS_PORT = "6380";
    vi.resetModules();
    const { env } = await import("@/env");
    expect(env.PORT).toBe("3000");
    expect(env.COMPRESSION_LEVEL).toBe(6);
    expect(env.REDIS_PORT).toBe(6380);
  });

  it("exits when the API URL is not a URL", async () => {
    process.env.API_BASE_URL = "not a url";
    process.env.LIVE_SERVER_SECRET_KEY = "secret";
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const exit = vi.spyOn(process, "exit").mockImplementation((() => undefined) as never);
    vi.resetModules();
    await import("@/env").catch(() => undefined);
    expect(exit).toHaveBeenCalledWith(1);
    expect(String((console.error as unknown as { mock: { calls: unknown[][] } }).mock.calls[0]?.[1])).toContain(
      "API_BASE_URL must be a valid URL"
    );
  });
});
