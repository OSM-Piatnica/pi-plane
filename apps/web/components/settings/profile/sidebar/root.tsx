/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { ScrollArea } from "@makeplane/propel/components/scroll-area";
import type { TProfileSettingsTabs } from "@plane/types";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// components
import { HomeButton } from "@/components/common/home-button";
// local imports
import { ProfileSettingsSidebarHeader } from "./header";
import { ProfileSettingsSidebarItemCategories } from "./item-categories";

type Props = {
  activeTab: TProfileSettingsTabs;
  className?: string;
  /** Show a way back to the workspace; only for the standalone page, the modal has its own close button. */
  showBackToWorkspace?: boolean;
  updateActiveTab: (tab: TProfileSettingsTabs) => void;
};

export function ProfileSettingsSidebarRoot(props: Props) {
  const { activeTab, className, showBackToWorkspace = false, updateActiveTab } = props;
  // translation
  const { t } = useTranslation();

  return (
    <div
      className={cn(
        "flex shrink-0 flex-col overflow-hidden border-r border-r-subtle bg-surface-2 px-3 py-4",
        className
      )}
    >
      <ScrollArea orientation="vertical">
        {showBackToWorkspace && (
          <div className="mb-3 flex items-center gap-1 text-body-md-medium">
            <HomeButton variant="back" />
            <p>{t("back_to_workspace")}</p>
          </div>
        )}
        <ProfileSettingsSidebarHeader />
        <ProfileSettingsSidebarItemCategories activeTab={activeTab} updateActiveTab={updateActiveTab} />
      </ScrollArea>
    </div>
  );
}
