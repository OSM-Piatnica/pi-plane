/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TSubmitShortcutEvent = {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
  /** Something below the form already handled the key (an editor leaving a code block, say). */
  defaultPrevented: boolean;
  /** An input method editor is composing text; Enter then confirms the composition. */
  isComposing: boolean;
};

/** Ctrl+Enter or Cmd+Enter, on its own, and not already taken by whatever has the focus. */
export const isSubmitShortcut = (event: TSubmitShortcutEvent): boolean =>
  event.key === "Enter" &&
  (event.ctrlKey || event.metaKey) &&
  !event.altKey &&
  !event.shiftKey &&
  !event.defaultPrevented &&
  !event.isComposing;
