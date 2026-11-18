/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { Pin } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import { usePropertyListContext } from "./collapsible-property-list";

type TSidebarPropertyListItemProps = {
  icon: React.FC<{ className?: string }>;
  label: string;
  children: ReactNode;
  appendElement?: ReactNode;
  childrenClassName?: string;
  /**
   * Stable id of the property. Inside a collapsible property list it lets the user pin the property, so it stays
   * visible while the list is collapsed. Without it the property can't be pinned and is hidden when collapsed.
   */
  propertyKey?: string;
};

export function SidebarPropertyListItem(props: TSidebarPropertyListItemProps) {
  const { icon: Icon, label, children, appendElement, childrenClassName, propertyKey } = props;
  const { t } = useTranslation();
  const propertyList = usePropertyListContext();
  const isPinned = Boolean(propertyKey && propertyList?.pinnedKeys.includes(propertyKey));

  if (propertyList?.isCollapsed && !isPinned) return null;

  return (
    <div className="group/property flex items-start gap-2">
      <div className="flex min-h-7.5 w-30 shrink-0 items-center gap-1.5 text-body-xs-regular text-tertiary">
        <Icon className="size-4 shrink-0" />
        <span className="min-w-0 whitespace-normal">{label}</span>
        {appendElement}
      </div>
      <div className={cn("flex grow flex-wrap items-center gap-1", childrenClassName)}>{children}</div>
      {propertyKey && propertyList && (
        <button
          type="button"
          onClick={() => propertyList.togglePin(propertyKey)}
          aria-pressed={isPinned}
          aria-label={isPinned ? t("unpin") : t("pin")}
          title={isPinned ? t("unpin") : t("pin")}
          className={cn(
            "flex size-7.5 shrink-0 items-center justify-center rounded-sm text-tertiary hover:bg-layer-1 hover:text-primary focus-visible:opacity-100",
            isPinned ? "text-accent-primary" : "opacity-0 group-hover/property:opacity-100"
          )}
        >
          <Pin className={cn("size-3.5", { "fill-current": isPinned })} />
        </button>
      )}
    </div>
  );
}
