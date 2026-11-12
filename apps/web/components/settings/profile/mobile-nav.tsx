/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "react-router";
// plane imports
import { PROFILE_SETTINGS } from "@plane/constants";
import type { TProfileSettingsTabs } from "@plane/types";
import { cn } from "@plane/utils";
// components
import { SettingsMobileNav } from "@/components/settings/mobile/nav";
// hooks
import { useUserSettings } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
// local imports
import { ProfileSettingsSidebarRoot } from "./sidebar";

/** The profile tabs as the dropdown of the mobile nav; picking a tab closes it. */
const ProfileSettingsMobileMenu = observer(function ProfileSettingsMobileMenu({ className }: { className?: string }) {
  // router
  const router = useAppRouter();
  const { profileTabId } = useParams();
  // store hooks
  const { toggleSidebar } = useUserSettings();

  return (
    <ProfileSettingsSidebarRoot
      activeTab={profileTabId as TProfileSettingsTabs}
      className={cn("w-[250px]", className)}
      showBackToWorkspace
      updateActiveTab={(tab) => {
        toggleSidebar(true);
        router.push(`/settings/profile/${tab}`);
      }}
    />
  );
});

/** Below `md` the profile settings sidebar does not fit next to the content, so it moves into this menu. */
export function ProfileSettingsMobileNav({ activeTab }: { activeTab: TProfileSettingsTabs }) {
  return (
    <SettingsMobileNav
      hamburgerContent={ProfileSettingsMobileMenu}
      activePath={PROFILE_SETTINGS[activeTab].i18n_label}
    />
  );
}
