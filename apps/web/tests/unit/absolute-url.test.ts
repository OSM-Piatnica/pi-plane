/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";

import { toAbsoluteURL } from "@/helpers/absolute-url";

describe("toAbsoluteURL", () => {
  it("puts a relative path on the origin", () => {
    expect(toAbsoluteURL("/api/assets/v2/static/abc/", "https://plane.example.com")).toBe(
      "https://plane.example.com/api/assets/v2/static/abc/"
    );
  });

  it("leaves a full URL as it is", () => {
    expect(toAbsoluteURL("https://cdn.example.com/a.png", "https://plane.example.com")).toBe(
      "https://cdn.example.com/a.png"
    );
    expect(toAbsoluteURL("http://localhost:8000/api/x/", "https://plane.example.com")).toBe(
      "http://localhost:8000/api/x/"
    );
  });

  it("keeps the port of the origin", () => {
    expect(toAbsoluteURL("/a/b", "http://localhost:8080")).toBe("http://localhost:8080/a/b");
  });

  it("gives the path back when there is no origin to put it on", () => {
    expect(toAbsoluteURL("/a/b", "")).toBe("/a/b");
  });
});
