/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useInstance } from "@/hooks/store/use-instance";

/**
 * Whether projects can be shared on the web (Space is part of the installation and switched on).
 * The sharing options are hidden while it is not. An answer without the setting counts as on.
 */
export const useSpaceEnabled = (): boolean => {
  const { config } = useInstance();
  return config?.is_space_enabled !== false;
};
