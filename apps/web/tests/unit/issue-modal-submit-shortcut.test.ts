/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TSubmitShortcutEvent } from "@/components/issues/issue-modal/submit-shortcut";
import { isSubmitShortcut } from "@/components/issues/issue-modal/submit-shortcut";

const press = (overrides: Partial<TSubmitShortcutEvent> = {}): TSubmitShortcutEvent => ({
  key: "Enter",
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  shiftKey: false,
  defaultPrevented: false,
  isComposing: false,
  ...overrides,
});

describe("create work item shortcut", () => {
  it("submits on Ctrl+Enter and on Cmd+Enter", () => {
    expect(isSubmitShortcut(press({ ctrlKey: true }))).toBe(true);
    expect(isSubmitShortcut(press({ metaKey: true }))).toBe(true);
  });

  it("leaves a plain Enter to the field (a new line in the description)", () => {
    expect(isSubmitShortcut(press())).toBe(false);
  });

  it("ignores other keys and other modifier combinations", () => {
    expect(isSubmitShortcut(press({ key: "s", ctrlKey: true }))).toBe(false);
    expect(isSubmitShortcut(press({ ctrlKey: true, shiftKey: true }))).toBe(false);
    expect(isSubmitShortcut(press({ metaKey: true, altKey: true }))).toBe(false);
  });

  it("does not take a key something else has already handled", () => {
    expect(isSubmitShortcut(press({ ctrlKey: true, defaultPrevented: true }))).toBe(false);
  });

  it("does not submit while an input method is composing text", () => {
    expect(isSubmitShortcut(press({ ctrlKey: true, isComposing: true }))).toBe(false);
  });
});
