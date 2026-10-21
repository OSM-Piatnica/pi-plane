/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it, vi } from "vitest";
import { guardQuickActionsClick } from "../../components/issues/issue-layouts/quick-action-dropdowns/click-guard";

const click = (targetIsInsideWrapper: boolean) => {
  const target = {} as Node;
  const event = {
    currentTarget: { contains: (node: Node) => targetIsInsideWrapper && node === target } as unknown as HTMLElement,
    target,
    stopPropagation: vi.fn(),
    preventDefault: vi.fn(),
  };
  guardQuickActionsClick(event);
  return event;
};

describe("guardQuickActionsClick", () => {
  it("keeps a click on the menu button from following the row link or opening the peek view", () => {
    const event = click(true);
    expect(event.stopPropagation).toHaveBeenCalledOnce();
    expect(event.preventDefault).toHaveBeenCalledOnce();
  });

  it("keeps a click inside a portalled modal from reaching the row, but lets its submit button submit", () => {
    const event = click(false);
    expect(event.stopPropagation).toHaveBeenCalledOnce();
    expect(event.preventDefault).not.toHaveBeenCalled();
  });
});
