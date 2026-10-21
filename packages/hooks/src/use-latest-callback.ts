/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useLayoutEffect, useRef } from "react";

/**
 * A function with a stable identity that always calls the latest `callback`, for handlers registered once
 * in an effect (document listeners, drag-and-drop targets) that must not re-subscribe on every render.
 *
 * Use this instead of `useEffectEvent` for such handlers: inside a mobx `observer` component the Effect
 * Event keeps the callback from the first render, so it reads stale props and state.
 */
export const useLatestCallback = <Args extends unknown[], Result>(
  callback: (...args: Args) => Result
): ((...args: Args) => Result) => {
  const callbackRef = useRef(callback);
  useLayoutEffect(() => {
    callbackRef.current = callback;
  });
  return useCallback((...args: Args) => callbackRef.current(...args), []);
};
