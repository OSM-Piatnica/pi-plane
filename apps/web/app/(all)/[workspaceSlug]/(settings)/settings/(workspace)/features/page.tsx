/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { setToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import type { TWorkspaceFeatureKey } from "@plane/types";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { LogoSpinner } from "@/components/common/logo-spinner";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import { getWorkspaceFeaturesPageAccess } from "@/components/settings/workspace/features-access";
import { WorkspaceFeaturesList } from "@/components/settings/workspace/features-list";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useUserPermissions } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
import { useWorkspaceFeatures } from "@/hooks/use-workspace-features";
import type { Route } from "./+types/page";
import { FeaturesWorkspaceSettingsHeader } from "./header";

/**
 * Workspace settings, Features: the switches a workspace admin uses to turn parts of the product
 * on or off for the workspace (see `docs/workspace-features.md`). While no feature is available
 * the page has no navigation entry, and its address leads back to the general settings.
 */
function WorkspaceFeaturesSettingsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { t } = useTranslation();
  const router = useAppRouter();
  const { getWorkspaceRoleByWorkspaceSlug } = useUserPermissions();
  const { currentWorkspace } = useWorkspace();
  const { features, availableFeatures, updateFeature } = useWorkspaceFeatures();

  const hasFeatures = availableFeatures.length > 0;
  // wait for the membership to load, so an admin never sees "not authorised" for a moment
  const access = getWorkspaceFeaturesPageAccess(getWorkspaceRoleByWorkspaceSlug(workspaceSlug));

  useEffect(() => {
    if (!hasFeatures) router.replace(`/${workspaceSlug}/settings/`);
  }, [hasFeatures, router, workspaceSlug]);

  if (!hasFeatures) return null;
  if (access === "loading")
    return (
      <div className="flex w-full justify-center py-8">
        <LogoSpinner />
      </div>
    );
  if (access === "denied") return <NotAuthorizedView section="settings" className="h-auto" />;

  const handleToggle = (key: TWorkspaceFeatureKey, isEnabled: boolean) => {
    updateFeature(workspaceSlug, key, isEnabled).catch(() =>
      setToast({ type: "error", title: t("toast.error"), message: t("something_went_wrong_please_try_again") })
    );
  };

  const pageTitle = currentWorkspace?.name ? `${currentWorkspace.name} - ${t("common.features")}` : undefined;

  return (
    <SettingsContentWrapper header={<FeaturesWorkspaceSettingsHeader />}>
      <PageHead title={pageTitle} />
      <div className="w-full">
        <SettingsHeading title={t("common.features")} description={t("workspace_features.description")} />
        <WorkspaceFeaturesList features={availableFeatures} flags={features} onToggle={handleToggle} />
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(WorkspaceFeaturesSettingsPage);
