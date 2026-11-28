/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TInitiativeHealth, TInitiativeStatus } from "@plane/types";

export type TInitiativeStatusOption = { key: TInitiativeStatus; i18n_label: string; color: string };
export type TInitiativeHealthOption = { key: TInitiativeHealth; i18n_label: string; color: string };

/** The statuses of a goal or an initiative, in their natural order; the API has the same list */
export const INITIATIVE_STATUSES: readonly TInitiativeStatusOption[] = [
  { key: "planned", i18n_label: "initiatives.status.planned", color: "#3f76ff" },
  { key: "active", i18n_label: "initiatives.status.active", color: "#f39e1f" },
  { key: "paused", i18n_label: "initiatives.status.paused", color: "#525252" },
  { key: "completed", i18n_label: "initiatives.status.completed", color: "#16a34a" },
  { key: "cancelled", i18n_label: "initiatives.status.cancelled", color: "#ef4444" },
];

/** How it is going; an initiative without a status update has no health yet */
export const INITIATIVE_HEALTHS: readonly TInitiativeHealthOption[] = [
  { key: "on_track", i18n_label: "initiatives.health.on_track", color: "#16a34a" },
  { key: "at_risk", i18n_label: "initiatives.health.at_risk", color: "#f39e1f" },
  { key: "off_track", i18n_label: "initiatives.health.off_track", color: "#ef4444" },
];
