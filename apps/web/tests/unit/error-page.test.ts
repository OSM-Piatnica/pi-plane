/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { buildErrorDetails, createErrorReference, describeError, scrubPath } from "../../app/error/error-details";
import { getErrorKind, getErrorStatus } from "../../app/error/error-kind";

// the shape React Router gives an error response (what `isRouteErrorResponse` recognises)
const routeError = (status: number, statusText = "") => ({ status, statusText, data: "", internal: true });

describe("getErrorKind", () => {
  it("says access for 401 and 403, not found for 404 and server for 5xx", () => {
    expect(getErrorKind({ response: { status: 403 } }, true)).toBe("access");
    expect(getErrorKind({ response: { status: 401 } }, true)).toBe("access");
    expect(getErrorKind({ status: 404 }, true)).toBe("not_found");
    expect(getErrorKind({ response: { status: 502 } }, true)).toBe("server");
  });

  it("reads the status of a route error response", () => {
    expect(getErrorStatus(routeError(403, "Forbidden"))).toBe(403);
    expect(getErrorKind(routeError(403, "Forbidden"), true)).toBe("access");
    expect(getErrorKind(routeError(404, "Not Found"), true)).toBe("not_found");
    expect(getErrorKind(routeError(503, "Service Unavailable"), true)).toBe("server");
  });

  it("says offline when the browser is offline, whatever the error", () => {
    expect(getErrorKind(new Error("anything"), false)).toBe("offline");
    expect(getErrorKind(new TypeError("Failed to fetch"), false)).toBe("offline");
  });

  it("says server when a request got no answer although the browser is online", () => {
    expect(getErrorKind(new TypeError("Failed to fetch"), true)).toBe("server");
    expect(getErrorKind(Object.assign(new Error("Network Error"), { isAxiosError: true }), true)).toBe("server");
  });

  it("says generic for everything else", () => {
    expect(getErrorKind(new Error("Cannot read properties of undefined"), true)).toBe("generic");
    expect(getErrorKind(undefined, true)).toBe("generic");
    expect(getErrorKind(routeError(400), true)).toBe("generic");
  });
});

describe("getErrorKind without a browser", () => {
  it("does not take a missing online flag for offline", () => {
    // Node and old browsers have no navigator.onLine: only an explicit false is offline
    expect(getErrorKind(new Error("boom"))).toBe("generic");
  });
});

describe("createErrorReference", () => {
  it("is two groups of four characters from an unambiguous alphabet", () => {
    for (let index = 0; index < 50; index++)
      expect(createErrorReference()).toMatch(/^[A-HJKMNP-Z2-9]{4}-[A-HJKMNP-Z2-9]{4}$/);
  });

  it("is made of the bytes it is given", () => {
    expect(createErrorReference(() => new Uint8Array([0, 1, 2, 3, 4, 5, 6, 7]))).toBe("ABCD-EFGH");
  });
});

describe("scrubPath", () => {
  it("drops the query string and the fragment", () => {
    expect(scrubPath("/acme/projects?token=abc&x=1#top")).toBe("/acme/projects");
  });

  it("replaces record ids", () => {
    expect(scrubPath("/acme/projects/0b4f1d2a-3c4e-4f5a-8b9c-0d1e2f3a4b5c/issues")).toBe("/acme/projects/:id/issues");
  });
});

describe("describeError", () => {
  it("keeps the name, shortens the message and removes emails and ids", () => {
    const error = new Error(`User ana@example.com 0b4f1d2a-3c4e-4f5a-8b9c-0d1e2f3a4b5c ${"x".repeat(500)}`);
    const { name, message } = describeError(error);
    expect(name).toBe("Error");
    expect(message).toContain("[email]");
    expect(message).toContain(":id");
    expect(message).not.toContain("ana@example.com");
    expect(message.length).toBeLessThanOrEqual(300);
  });

  it("copes with things that are not errors", () => {
    expect(describeError(null).name).toBe("null");
    expect(describeError(undefined).name).toBe("undefined");
    expect(describeError("boom")).toEqual({ name: "string", message: "boom" });
  });
});

describe("buildErrorDetails", () => {
  it("has the reference, time, page, kind and error, and no stack trace", () => {
    const error = new TypeError("x is not a function");
    const details = buildErrorDetails({
      reference: "7K2M-9QXD",
      kind: "generic",
      error,
      path: "/acme/projects/0b4f1d2a-3c4e-4f5a-8b9c-0d1e2f3a4b5c?secret=1",
      time: new Date("2026-11-24T20:00:00Z"),
    });
    expect(details.split("\n")).toEqual([
      "Pi-Plane error 7K2M-9QXD",
      "Time: 2026-11-24T20:00:00.000Z",
      "Page: /acme/projects/:id",
      "Kind: generic",
      "Error: TypeError: x is not a function",
    ]);
  });

  it("names the HTTP status when there is one", () => {
    const details = buildErrorDetails({
      reference: "AAAA-BBBB",
      kind: "access",
      error: { response: { status: 403 } },
      path: "/a",
      time: new Date(0),
    });
    expect(details).toContain("Kind: access (HTTP 403)");
  });
});

describe("the error page keys", () => {
  const english = JSON.parse(
    readFileSync(resolve(import.meta.dirname, "../../../../packages/i18n/src/locales/en/common.json"), "utf8")
  ) as Record<string, any>;

  it("has an English text for every key the page asks for (so the fallback text is never the only copy)", () => {
    const source = readFileSync(resolve(import.meta.dirname, "../../app/error/prod.tsx"), "utf8");
    const keys = [...source.matchAll(/"((?:app_text|common)\.[a-z_.]+)"/g)].map((match) => match[1]);
    const missing = keys.filter(
      (key) => key.split(".").reduce((node: any, part) => node?.[part], english) === undefined
    );
    // `common.copied` lives under the `common` object of common.json, the rest under `app_text`
    expect(missing).toEqual([]);
  });
});
