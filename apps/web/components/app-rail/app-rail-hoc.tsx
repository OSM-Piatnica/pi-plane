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
import type { AppSidebarItemData } from "@/components/sidebar/sidebar-item";
import { APP_RAIL_APP_ICONS } from "./registry-icons";
import { useAppRailApps } from "./use-app-rail-apps";

type WithDockItemsProps = {
  dockItems: (AppSidebarItemData & { shouldRender: boolean })[];
};

export function withDockItems<P extends WithDockItemsProps>(WrappedComponent: React.ComponentType<P>) {
  const ComponentWithDockItems = observer(function ComponentWithDockItems(props: Omit<P, keyof WithDockItemsProps>) {
    const { workspaceSlug } = useParams();
    const { t } = useTranslation();
    const { enabledApps, activeAppKey } = useAppRailApps();

    // one item per enabled app of the registry, in registry order (see docs/app-rail.md)
    const dockItems: (AppSidebarItemData & { shouldRender: boolean })[] = enabledApps.map((app) => {
      const Icon = APP_RAIL_APP_ICONS[app.key];
      return {
        label: t(app.i18n_label),
        icon: <Icon className="size-5" />,
        href: app.getHref(`${workspaceSlug}`),
        isActive: activeAppKey === app.key,
        shouldRender: true,
      };
    });

    return <WrappedComponent {...(props as P)} dockItems={dockItems} />;
  });

  return ComponentWithDockItems;
}
