/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Marks a cycle column that cannot take a drop because the cycle is completed. The column is built
 * where no translation is available, so the drag overlay turns this marker into the message.
 */
export const COMPLETED_CYCLE_DROP_ERROR = "completed_cycle";

/**
 * The title to show for a group-by column. The empty "None" group is built where no translation is
 * available, so it is recognised by its id and translated here.
 */
export const getGroupColumnName = (column: { id: string; name: string }, t: (key: string) => string): string =>
  column.id === "None" ? t("common.none") : column.name;
