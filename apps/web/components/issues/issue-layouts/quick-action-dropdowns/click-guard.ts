/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { MouseEvent } from "react";

/**
 * Click handler for the element that wraps a row's quick-action menu inside a clickable row (a link or a
 * card that opens the peek view).
 *
 * The menu renders its modals (make a copy, delete, ...) as React children, and React bubbles a click
 * inside a portalled modal up the React tree to this wrapper. Every click is kept from reaching the row,
 * so a press in a modal does not open the peek view. The default action is only cancelled for clicks that
 * are also inside the wrapper in the DOM (the menu button, which would otherwise follow the row's link):
 * cancelling a click inside a modal stopped its submit button from submitting the form.
 */
export const guardQuickActionsClick = (
  e: Pick<MouseEvent<HTMLElement>, "currentTarget" | "target" | "stopPropagation" | "preventDefault">
) => {
  e.stopPropagation();
  if (e.currentTarget.contains(e.target as Node)) e.preventDefault();
};
