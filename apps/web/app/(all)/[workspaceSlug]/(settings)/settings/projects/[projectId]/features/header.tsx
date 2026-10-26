/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { PROJECT_SETTINGS } from "@plane/constants";
import { SettingsBreadcrumbHeader } from "@/components/settings/breadcrumb-header";
import { PROJECT_SETTINGS_ICONS } from "@/components/settings/project/sidebar/item-icon";

export function FeaturesProjectSettingsHeader() {
  return <SettingsBreadcrumbHeader item={PROJECT_SETTINGS.features} Icon={PROJECT_SETTINGS_ICONS.features} />;
}
