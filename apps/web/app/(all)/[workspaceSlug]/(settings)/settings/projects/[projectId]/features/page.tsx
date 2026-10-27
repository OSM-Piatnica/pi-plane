/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { IProject } from "@plane/types";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import { ProjectSettingsFeatureControlItem } from "@/components/settings/project/content/feature-control-item";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import type { Route } from "./+types/page";
import { FeaturesProjectSettingsHeader } from "./header";

type TFeature = {
  i18nPrefix: string;
  property: keyof Pick<
    IProject,
    "cycle_view" | "module_view" | "issue_views_view" | "page_view" | "inbox_view" | "is_time_tracking_enabled"
  >;
};

const FEATURES: TFeature[] = [
  { i18nPrefix: "project_settings.features.cycles", property: "cycle_view" },
  { i18nPrefix: "project_settings.features.modules", property: "module_view" },
  { i18nPrefix: "project_settings.features.views", property: "issue_views_view" },
  { i18nPrefix: "project_settings.features.pages", property: "page_view" },
  { i18nPrefix: "project_settings.features.intake", property: "inbox_view" },
  { i18nPrefix: "project_settings.features.time_tracking", property: "is_time_tracking_enabled" },
];

function FeaturesSettingsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, projectId } = params;
  // store hooks
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentProjectDetails } = useProject();
  // translation
  const { t } = useTranslation();
  // derived values
  const pageTitle = currentProjectDetails?.name
    ? `${currentProjectDetails?.name} settings - ${t("common.features")}`
    : undefined;
  const canPerformProjectAdminActions = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);

  if (workspaceUserInfo && !canPerformProjectAdminActions) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<FeaturesProjectSettingsHeader />}>
      <PageHead title={pageTitle} />
      <section className="w-full">
        <SettingsHeading title={t("common.features")} description={t("project_create.features.description")} />
        <div className="mt-7 flex flex-col gap-2">
          {FEATURES.map((feature) => (
            <ProjectSettingsFeatureControlItem
              key={feature.property}
              title={t(`${feature.i18nPrefix}.toggle_title`)}
              description={t(`${feature.i18nPrefix}.toggle_description`)}
              featureProperty={feature.property}
              projectId={projectId}
              value={!!currentProjectDetails?.[feature.property]}
              workspaceSlug={workspaceSlug}
            />
          ))}
        </div>
      </section>
    </SettingsContentWrapper>
  );
}

export default observer(FeaturesSettingsPage);
