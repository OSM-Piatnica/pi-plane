/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import Link from "next/link";
// types
import type { TPageNavigationTabs } from "@plane/types";
// helpers
import { cn } from "@plane/utils";
import { useTranslation } from "@plane/i18n";

type TPageTabNavigation = {
  workspaceSlug: string;
  projectId: string;
  pageType: TPageNavigationTabs;
};

// pages tab options
const pageTabs: { key: TPageNavigationTabs; labelKey: string }[] = [
  {
    key: "public",
    labelKey: "public",
  },
  {
    key: "private",
    labelKey: "private",
  },
  {
    key: "archived",
    labelKey: "project_components.shared.archived",
  },
];

export function PageTabNavigation(props: TPageTabNavigation) {
  const { workspaceSlug, projectId, pageType } = props;
  const { t } = useTranslation();

  const handleTabClick = (e: React.MouseEvent<HTMLAnchorElement>, tabKey: TPageNavigationTabs) => {
    if (tabKey === pageType) e.preventDefault();
  };

  return (
    <div className="relative flex h-full items-center">
      {pageTabs.map((tab) => (
        <Link
          key={tab.key}
          href={`/${workspaceSlug}/projects/${projectId}/pages?type=${tab.key}`}
          onClick={(e) => handleTabClick(e, tab.key)}
          className="flex h-full flex-col"
        >
          <div
            className={cn(`flex flex-1 items-center justify-center px-4 text-13 font-medium transition-all`, {
              "text-accent-primary": tab.key === pageType,
            })}
          >
            {t(tab.labelKey)}
          </div>
          <div
            className={cn(`w-full rounded-t border-t-2 border-transparent transition-all`, {
              "border-accent-strong": tab.key === pageType,
            })}
          />
        </Link>
      ))}
    </div>
  );
}
