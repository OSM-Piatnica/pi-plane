/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  IGNORED_FILTERS_EVENT,
  IGNORED_FILTERS_NOTICE_INTERVAL_MS,
  announceIgnoredFilters,
  isIgnoredFilterNoticeDue,
  parseIgnoredFilters,
} from "@/helpers/ignored-filters.helper";

describe("parseIgnoredFilters", () => {
  it("reads the comma separated names of the header", () => {
    expect(parseIgnoredFilters("is_critical")).toEqual(["is_critical"]);
    expect(parseIgnoredFilters("is_critical, other_filter,is_critical")).toEqual(["is_critical", "other_filter"]);
  });

  it("drops what is not a filter name", () => {
    expect(parseIgnoredFilters("")).toEqual([]);
    expect(parseIgnoredFilters(undefined)).toEqual([]);
    expect(parseIgnoredFilters(42)).toEqual([]);
    expect(parseIgnoredFilters("<script>,is_critical,a b")).toEqual(["is_critical"]);
  });
});

describe("isIgnoredFilterNoticeDue", () => {
  it("is due the first time, then not again for a while, per filter", () => {
    const shown = new Map<string, number>();
    expect(isIgnoredFilterNoticeDue("is_critical", shown, 1000)).toBe(true);
    expect(isIgnoredFilterNoticeDue("is_critical", shown, 1000 + IGNORED_FILTERS_NOTICE_INTERVAL_MS - 1)).toBe(false);
    expect(isIgnoredFilterNoticeDue("other", shown, 2000)).toBe(true);
    expect(isIgnoredFilterNoticeDue("is_critical", shown, 1000 + IGNORED_FILTERS_NOTICE_INTERVAL_MS)).toBe(true);
  });
});

describe("announceIgnoredFilters", () => {
  const listen = () => {
    const received: string[][] = [];
    const handler = (event: Event) => received.push((event as CustomEvent<string[]>).detail);
    const target = new EventTarget();
    vi.stubGlobal("window", Object.assign(target, { dispatchEvent: target.dispatchEvent.bind(target) }));
    target.addEventListener(IGNORED_FILTERS_EVENT, handler);
    return received;
  };

  afterEach(() => vi.unstubAllGlobals());

  it("sends the names that a response header carries", () => {
    const received = listen();
    announceIgnoredFilters({ "x-ignored-filters": "is_critical" });
    expect(received).toEqual([["is_critical"]]);
  });

  it("says nothing when the header is missing or empty", () => {
    const received = listen();
    announceIgnoredFilters({});
    announceIgnoredFilters({ "x-ignored-filters": "" });
    announceIgnoredFilters(undefined);
    expect(received).toEqual([]);
  });
});
