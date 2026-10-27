/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  SIDEBAR_MAX_WIDTH,
  SIDEBAR_MIN_CHART_WIDTH,
  SIDEBAR_MIN_WIDTH,
  SIDEBAR_WIDTH,
  SIDEBAR_WIDTH_PROPERTY,
  SIDEBAR_WIDTH_STORAGE_KEY,
} from "../../components/gantt-chart/constants";
import {
  clampSidebarWidth,
  getSidebarMaxWidth,
  getSidebarWidth,
  getStoredSidebarWidth,
} from "../../components/gantt-chart/helpers/sidebar-width";
import { BaseTimeLineStore } from "../../store/timeline/base-timeline.store";

const memoryStorage = () => {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    removeItem: (key: string) => void data.delete(key),
  };
};

beforeEach(() => {
  // the saved width is read through `window.localStorage`
  const storage = memoryStorage();
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal("window", { localStorage: storage });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("sidebar width limits", () => {
  it("keeps the width between the minimum and the maximum", () => {
    expect(clampSidebarWidth(100)).toBe(SIDEBAR_MIN_WIDTH);
    expect(clampSidebarWidth(5000)).toBe(SIDEBAR_MAX_WIDTH);
    expect(clampSidebarWidth(400.4)).toBe(400);
  });

  it("leaves the chart its room in a narrow container", () => {
    expect(getSidebarMaxWidth(1600)).toBe(SIDEBAR_MAX_WIDTH);
    expect(getSidebarMaxWidth(900)).toBe(900 - SIDEBAR_MIN_CHART_WIDTH);
    // never below the minimum, even in a tiny container
    expect(getSidebarMaxWidth(300)).toBe(SIDEBAR_MIN_WIDTH);
    expect(clampSidebarWidth(700, 900)).toBe(660);
  });
});

describe("saved sidebar width", () => {
  it("is the default until the user chooses one", () => {
    expect(getStoredSidebarWidth()).toBe(SIDEBAR_WIDTH);
  });

  it("is read back, within the limits", () => {
    localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, JSON.stringify(480));
    expect(getStoredSidebarWidth()).toBe(480);
    localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, JSON.stringify(50));
    expect(getStoredSidebarWidth()).toBe(SIDEBAR_MIN_WIDTH);
  });

  it("falls back to the default for something that is not a width", () => {
    localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, JSON.stringify("wide"));
    expect(getStoredSidebarWidth()).toBe(SIDEBAR_WIDTH);
  });
});

describe("the live width", () => {
  it("is read from the container, and defaults without one", () => {
    expect(getSidebarWidth(null)).toBe(SIDEBAR_WIDTH);
    const container = {
      style: { getPropertyValue: (name: string) => (name === SIDEBAR_WIDTH_PROPERTY ? "512px" : "") },
    };
    expect(getSidebarWidth(container as unknown as HTMLElement)).toBe(512);
    expect(getSidebarWidth({ style: { getPropertyValue: () => "" } } as unknown as HTMLElement)).toBe(SIDEBAR_WIDTH);
  });
});

describe("timeline store sidebar width", () => {
  it("saves a chosen width and picks it up when the timeline opens again", () => {
    const store = new BaseTimeLineStore({} as never);
    expect(store.sidebarWidth).toBe(SIDEBAR_WIDTH);
    store.setSidebarWidth(500);
    expect(store.sidebarWidth).toBe(500);
    expect(JSON.parse(localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY) ?? "null")).toBe(500);
    store.setSidebarWidth(9999);
    expect(store.sidebarWidth).toBe(SIDEBAR_MAX_WIDTH);
    expect(new BaseTimeLineStore({} as never).sidebarWidth).toBe(SIDEBAR_MAX_WIDTH);
  });

  it("does not save a width that only came from a narrower container", () => {
    const store = new BaseTimeLineStore({} as never);
    store.setSidebarWidth(600);
    store.setSidebarWidth(300, false);
    expect(store.sidebarWidth).toBe(300);
    expect(JSON.parse(localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY) ?? "null")).toBe(600);
  });
});
