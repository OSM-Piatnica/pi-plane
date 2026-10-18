/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { MarkType } from "@tiptap/pm/model";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clickHandler } from "./clickHandler";

vi.mock("@tiptap/core", () => ({
  getAttributes: () => ({}),
}));

type HandleClick = (view: unknown, pos: number, event: unknown) => boolean;

const getHandleClick = (): HandleClick => {
  const plugin = clickHandler({ type: { name: "link" } as MarkType });
  return plugin.props.handleClick as unknown as HandleClick;
};

// minimal stand-in for a click on an <a> inside the editor's root <div>
const makeClickEvent = (href: string, overrides: Record<string, unknown> = {}) => ({
  button: 0,
  target: { nodeName: "A", href, target: "_blank", parentNode: { nodeName: "DIV" } },
  ...overrides,
});

describe("clickHandler", () => {
  const open = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("window", { open });
  });

  afterEach(() => {
    open.mockReset();
    vi.unstubAllGlobals();
  });

  it.each([
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "about:blank",
  ])("does not open %j", (href) => {
    const result = getHandleClick()({ state: {} }, 0, makeClickEvent(href));
    expect(result).toBe(false);
    expect(open).not.toHaveBeenCalled();
  });

  it.each(["https://example.com/", "http://example.com/?q=javascript:alert(1)", "mailto:user@example.com"])(
    "opens %j",
    (href) => {
      const result = getHandleClick()({ state: {} }, 0, makeClickEvent(href));
      expect(result).toBe(true);
      expect(open).toHaveBeenCalledWith(href, "_blank", "noopener");
    }
  );

  it("ignores non-primary mouse buttons", () => {
    const result = getHandleClick()({ state: {} }, 0, makeClickEvent("https://example.com/", { button: 1 }));
    expect(result).toBe(false);
    expect(open).not.toHaveBeenCalled();
  });

  it("ignores clicks that are not on a link", () => {
    const event = makeClickEvent("https://example.com/", {
      target: { nodeName: "P", parentNode: { nodeName: "DIV" } },
    });
    expect(getHandleClick()({ state: {} }, 0, event)).toBe(false);
    expect(open).not.toHaveBeenCalled();
  });
});
