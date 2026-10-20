/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// store
import type { TPageInstance } from "@/store/pages/base-page";

export type TPageCollaboratorsListProps = {
  page: TPageInstance;
};

// oxlint-disable-next-line no-empty-pattern -- extension-point stub; props intentionally unused in CE
export function PageCollaboratorsList({}: TPageCollaboratorsListProps) {
  return null;
}
