/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { TimeTrackingOutline } from "@makeplane/propel/icons";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
// helpers
import { canViewWorklogsForRole, formatWorklogDuration } from "@/helpers/worklog";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import { useWorklogs } from "@/hooks/use-worklogs";
// local imports
import { WorklogModal } from "../worklog-modal";

type TIssueWorklogProperty = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

/** The time logged on a work item, in its property list: shows the total and opens the entries. */
export const IssueWorklogProperty = observer(function IssueWorklogProperty(props: TIssueWorklogProperty) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  const [isModalOpen, setIsModalOpen] = useState(false);
  // store hooks
  const { getProjectById } = useProject();
  const { getProjectRoleByWorkspaceSlugAndProjectId } = useUserPermissions();
  // derived values
  const isTimeTrackingEnabled = Boolean(getProjectById(projectId)?.is_time_tracking_enabled);
  const canViewWorklogs = canViewWorklogsForRole(getProjectRoleByWorkspaceSlugAndProjectId(workspaceSlug, projectId));
  const isActive = isTimeTrackingEnabled && canViewWorklogs;
  const { totalDuration } = useWorklogs(workspaceSlug, projectId, issueId, isActive);

  if (!isActive) return <></>;

  return (
    <>
      <SidebarPropertyListItem icon={TimeTrackingOutline} label={t("time_tracking")}>
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="flex h-7.5 items-center rounded-sm px-2 text-body-xs-regular text-secondary hover:bg-layer-1"
        >
          {totalDuration > 0 ? formatWorklogDuration(totalDuration) : disabled ? "—" : t("worklog.log_time")}
        </button>
      </SidebarPropertyListItem>
      <WorklogModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        workspaceSlug={workspaceSlug}
        projectId={projectId}
        issueId={issueId}
        disabled={disabled}
      />
    </>
  );
});
