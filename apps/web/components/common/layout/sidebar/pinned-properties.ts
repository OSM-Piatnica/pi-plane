/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** The stored pins as a clean list: local storage can hold anything, so drop what is not a string. */
export const sanitizePinnedKeys = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((key): key is string => typeof key === "string") : [];

/** The pins with `propertyKey` added, or removed when it was already pinned. */
export const togglePinnedKey = (pinnedKeys: string[], propertyKey: string): string[] =>
  pinnedKeys.includes(propertyKey) ? pinnedKeys.filter((key) => key !== propertyKey) : [...pinnedKeys, propertyKey];
