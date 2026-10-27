/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { WORKSPACE_SETTINGS } from "@plane/constants";
import { SettingsBreadcrumbHeader } from "@/components/settings/breadcrumb-header";
import { WORKSPACE_SETTINGS_ICONS } from "@/components/settings/workspace/sidebar/item-icon";

export function ProjectTemplatesSettingsHeader() {
  return (
    <SettingsBreadcrumbHeader
      item={WORKSPACE_SETTINGS["project-templates"]}
      Icon={WORKSPACE_SETTINGS_ICONS["project-templates"]}
    />
  );
}
