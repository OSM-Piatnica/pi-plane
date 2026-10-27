/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { PROJECT_SETTINGS } from "@plane/constants";
import { SettingsBreadcrumbHeader } from "@/components/settings/breadcrumb-header";
import { PROJECT_SETTINGS_ICONS } from "@/components/settings/project/sidebar/item-icon";

export function GeneralProjectSettingsHeader() {
  return <SettingsBreadcrumbHeader item={PROJECT_SETTINGS.general} Icon={PROJECT_SETTINGS_ICONS.general} />;
}
