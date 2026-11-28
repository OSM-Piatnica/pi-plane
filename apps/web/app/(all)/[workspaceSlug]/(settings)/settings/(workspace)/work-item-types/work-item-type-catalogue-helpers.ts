/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueTypeCatalogueEntry } from "@plane/types";

/** The entries the workspace does not have yet: what the catalogue dialog selects at first. */
export const getNewCatalogueKeys = (entries: Pick<TIssueTypeCatalogueEntry, "key" | "existing_type_id">[]) =>
  entries.filter((entry) => !entry.existing_type_id).map((entry) => entry.key);

/** `selected` with `key` added or taken away. */
export const toggleCatalogueKey = (selected: string[], key: string): string[] =>
  selected.includes(key) ? selected.filter((item) => item !== key) : [...selected, key];
