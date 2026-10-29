/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { LucideIcon } from "lucide-react";
import { BuildingOutline, ExportOutline, MembersOutline, WebhooksOutline } from "@makeplane/propel/icons";
// plane imports
import type { ISvgIcons } from "@plane/blocks/icons";
import type { TWorkspaceSettingsTabs } from "@plane/types";
import { ArrowDownToLine, FolderKanban, Layers, LayoutTemplate, Network } from "lucide-react";

export const WORKSPACE_SETTINGS_ICONS: Record<TWorkspaceSettingsTabs, LucideIcon | React.FC<ISvgIcons>> = {
  general: BuildingOutline,
  members: MembersOutline,
  groups: Network,
  export: ExportOutline,
  import: ArrowDownToLine,
  "work-item-templates": LayoutTemplate,
  "work-item-types": Layers,
  "project-templates": FolderKanban,
  webhooks: WebhooksOutline,
};
