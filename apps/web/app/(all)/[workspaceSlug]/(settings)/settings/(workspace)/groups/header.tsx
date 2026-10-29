/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { WORKSPACE_SETTINGS } from "@plane/constants";
import { SettingsBreadcrumbHeader } from "@/components/settings/breadcrumb-header";
import { WORKSPACE_SETTINGS_ICONS } from "@/components/settings/workspace/sidebar/item-icon";

export function GroupsWorkspaceSettingsHeader() {
  return <SettingsBreadcrumbHeader item={WORKSPACE_SETTINGS.groups} Icon={WORKSPACE_SETTINGS_ICONS.groups} />;
}
