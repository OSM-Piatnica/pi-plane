/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { TPage, TPageExtended } from "@plane/types";
import type { RootStore } from "@/plane-web/store/root.store";
import type { TBasePageServices } from "@/store/pages/base-page";

export type TExtendedPageInstance = TPageExtended & {
  asJSONExtended: TPageExtended;
};

export class ExtendedBasePage implements TExtendedPageInstance {
  // oxlint-disable-next-line no-useless-constructor, @typescript-eslint/no-unused-vars -- deliberate extension-point constructor kept for override parity
  constructor(store: RootStore, page: TPage, services: TBasePageServices) {}

  get asJSONExtended(): TExtendedPageInstance["asJSONExtended"] {
    return {};
  }
}
