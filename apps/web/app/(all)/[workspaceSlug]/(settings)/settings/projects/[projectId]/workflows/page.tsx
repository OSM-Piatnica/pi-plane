/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { ProjectWorkflowRoot } from "@/components/project-workflows";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import { ProjectSettingsFeatureControlItem } from "@/components/settings/project/content/feature-control-item";
import { RELATION_TOGGLE_DEFAULTS } from "@/helpers/relation-type-toggles";
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import type { Route } from "./+types/page";
import { WorkflowsProjectSettingsHeader } from "./header";

function WorkflowsSettingsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, projectId } = params;
  const { currentProjectDetails } = useProject();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { t } = useTranslation();

  const pageTitle = currentProjectDetails?.name ? `${currentProjectDetails?.name} - Workflows` : undefined;
  const canManageWorkflows = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);

  if (workspaceUserInfo && !canManageWorkflows) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<WorkflowsProjectSettingsHeader />}>
      <PageHead title={pageTitle} />
      <div className="w-full">
        <SettingsHeading
          title={t("project_settings.workflows.heading")}
          description={t("project_settings.workflows.description")}
        />
        <div className="mt-6">
          <ProjectWorkflowRoot workspaceSlug={workspaceSlug} projectId={projectId} />
        </div>
        <div className="mt-10">
          <SettingsHeading
            title={t("project_settings.workflows.rules.heading")}
            description={t("project_settings.workflows.rules.description")}
          />
          <div className="mt-6 flex flex-col gap-2">
            <ProjectSettingsFeatureControlItem
              title={t("project_settings.workflows.rules.parent_completion.title")}
              description={t("project_settings.workflows.rules.parent_completion.description")}
              featureProperty="is_parent_completion_rule_enabled"
              projectId={projectId}
              value={!!currentProjectDetails?.is_parent_completion_rule_enabled}
              workspaceSlug={workspaceSlug}
            />
            <ProjectSettingsFeatureControlItem
              title={t("project_settings.workflows.rules.blocked_status.title")}
              description={t("project_settings.workflows.rules.blocked_status.description")}
              featureProperty="is_blocked_status_rule_enabled"
              projectId={projectId}
              value={!!currentProjectDetails?.is_blocked_status_rule_enabled}
              workspaceSlug={workspaceSlug}
            />
            <ProjectSettingsFeatureControlItem
              title={t("project_settings.workflows.rules.assignee_edit.title")}
              description={t("project_settings.workflows.rules.assignee_edit.description")}
              featureProperty="is_assignee_edit_rule_enabled"
              projectId={projectId}
              value={!!currentProjectDetails?.is_assignee_edit_rule_enabled}
              workspaceSlug={workspaceSlug}
            />
          </div>
        </div>
        <div className="mt-10">
          <SettingsHeading
            title={t("project_settings.workflows.relation_types.heading")}
            description={t("project_settings.workflows.relation_types.description")}
          />
          <div className="mt-6 flex flex-col gap-2">
            <ProjectSettingsFeatureControlItem
              title={t("project_settings.workflows.relation_types.schedule.title")}
              description={t("project_settings.workflows.relation_types.schedule.description")}
              featureProperty="is_relation_schedule_enabled"
              projectId={projectId}
              value={
                currentProjectDetails?.is_relation_schedule_enabled ??
                RELATION_TOGGLE_DEFAULTS.is_relation_schedule_enabled
              }
              workspaceSlug={workspaceSlug}
            />
            <ProjectSettingsFeatureControlItem
              title={t("project_settings.workflows.relation_types.traceability.title")}
              description={t("project_settings.workflows.relation_types.traceability.description")}
              featureProperty="is_relation_traceability_enabled"
              projectId={projectId}
              value={
                currentProjectDetails?.is_relation_traceability_enabled ??
                RELATION_TOGGLE_DEFAULTS.is_relation_traceability_enabled
              }
              workspaceSlug={workspaceSlug}
            />
            <ProjectSettingsFeatureControlItem
              title={t("project_settings.workflows.relation_types.relates_to.title")}
              description={t("project_settings.workflows.relation_types.relates_to.description")}
              featureProperty="is_relation_relates_to_enabled"
              projectId={projectId}
              value={
                currentProjectDetails?.is_relation_relates_to_enabled ??
                RELATION_TOGGLE_DEFAULTS.is_relation_relates_to_enabled
              }
              workspaceSlug={workspaceSlug}
            />
            <ProjectSettingsFeatureControlItem
              title={t("project_settings.workflows.relation_types.duplicate.title")}
              description={t("project_settings.workflows.relation_types.duplicate.description")}
              featureProperty="is_relation_duplicate_enabled"
              projectId={projectId}
              value={
                currentProjectDetails?.is_relation_duplicate_enabled ??
                RELATION_TOGGLE_DEFAULTS.is_relation_duplicate_enabled
              }
              workspaceSlug={workspaceSlug}
            />
          </div>
        </div>
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(WorkflowsSettingsPage);
