/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { ArrowNarrowLeftOutline, HomeOutline } from "@makeplane/propel/icons";
import { IconButton } from "@makeplane/propel/components/icon-button";
import { Icon } from "@makeplane/propel/components/icon";
// helpers
import { getWorkspaceHomeHref } from "@/helpers/home-navigation.helper";
// hooks
import { useUserSettings } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";

type Props = {
  /** Workspace to return to; falls back to the user's last workspace, then to the root route. */
  workspaceSlug?: string;
  /** "home" shows the home icon, "back" shows a back arrow labelled as returning to the workspace. */
  variant?: "home" | "back";
};

/**
 * Icon button that returns to the workspace home, for screens that hide the app sidebar.
 */
export const HomeButton = observer(function HomeButton(props: Props) {
  const { workspaceSlug, variant = "home" } = props;
  // router
  const router = useAppRouter();
  // store hooks
  const { data: currentUserSettings } = useUserSettings();
  // translation
  const { t } = useTranslation();
  // derived values
  const targetSlug =
    workspaceSlug ||
    currentUserSettings?.workspace?.last_workspace_slug ||
    currentUserSettings?.workspace?.fallback_workspace_slug;
  const isBack = variant === "back";

  return (
    <IconButton
      variant="ghost"
      size="sm"
      icon={<Icon icon={isBack ? ArrowNarrowLeftOutline : HomeOutline} />}
      aria-label={t(isBack ? "back_to_workspace" : "home.title")}
      onClick={() => router.push(getWorkspaceHomeHref(targetSlug))}
    />
  );
});
