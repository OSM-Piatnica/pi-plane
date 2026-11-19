/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

// hoc/withDockItems.tsx
import React from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { useTranslation } from "@plane/i18n";
import { getAppRailDockItems } from "@plane/utils";
import type { AppSidebarItemData } from "@/components/sidebar/sidebar-item";
import { APP_RAIL_APP_ICONS } from "./registry-icons";
import { useAppRailApps } from "./use-app-rail-apps";

type WithDockItemsProps = {
  dockItems: (AppSidebarItemData & { shouldRender: boolean; key?: string })[];
};

export function withDockItems<P extends WithDockItemsProps>(WrappedComponent: React.ComponentType<P>) {
  const ComponentWithDockItems = observer(function ComponentWithDockItems(props: Omit<P, keyof WithDockItemsProps>) {
    const { workspaceSlug } = useParams();
    const { t } = useTranslation();
    const appRailState = useAppRailApps();

    // one item per enabled app the user did not hide, in the user's order (see docs/app-rail.md)
    const dockItems: WithDockItemsProps["dockItems"] = getAppRailDockItems(appRailState, `${workspaceSlug}`).map(
      (item) => {
        const Icon = APP_RAIL_APP_ICONS[item.key];
        return {
          key: item.key,
          label: t(item.i18n_label),
          icon: <Icon className="size-5" />,
          href: item.href,
          isActive: item.isActive,
          shouldRender: true,
        };
      }
    );

    return <WrappedComponent {...(props as P)} dockItems={dockItems} />;
  });

  return ComponentWithDockItems;
}
