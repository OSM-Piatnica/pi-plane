/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { setPromiseToast } from "@plane/blocks/toast";
import { useTranslation } from "@plane/i18n";
import { Switch } from "@makeplane/propel/components/switch";
// components
import { SettingsBoxedControlItem } from "@/components/settings/boxed-control-item";
// hooks
import { useProjectIssueTypes } from "@/hooks/use-project-issue-types";
// services
import { IssueTypeService } from "@/services/issue-type.service";

const issueTypeService = new IssueTypeService();

type Props = {
  projectId: string;
  workspaceSlug: string;
};

/** Epics are on in a project when a work item type marked as an Epic is linked to it. */
export const ProjectSettingsEpicsControlItem = observer(function ProjectSettingsEpicsControlItem(props: Props) {
  const { projectId, workspaceSlug } = props;
  // states
  const [isUpdating, setIsUpdating] = useState(false);
  // hooks
  const { t } = useTranslation();
  const { types, isLoading, mutate } = useProjectIssueTypes(workspaceSlug, projectId);
  // derived values
  const isEnabled = types.some((row) => row.issue_type_detail?.is_epic);

  const handleToggle = () => {
    setIsUpdating(true);
    const request = isEnabled
      ? issueTypeService.disableProjectEpics(workspaceSlug, projectId)
      : issueTypeService.enableProjectEpics(workspaceSlug, projectId);
    const updatePromise = request.then(() => mutate()).finally(() => setIsUpdating(false));

    setPromiseToast(updatePromise, {
      loading: t("project_components.features.updating"),
      success: {
        title: t("toast.success"),
        message: () => t("project_components.features.updated"),
      },
      error: {
        title: t("toast.error"),
        message: () => t("project_components.features.update_error"),
      },
    });
  };

  return (
    <SettingsBoxedControlItem
      title={t("project_settings.features.epics.toggle_title")}
      description={t("project_settings.features.epics.toggle_description")}
      control={
        <Switch
          size="sm"
          checked={isEnabled}
          onCheckedChange={handleToggle}
          disabled={isLoading || isUpdating}
          aria-label={t("project_settings.features.epics.toggle_title")}
        />
      }
    />
  );
});
