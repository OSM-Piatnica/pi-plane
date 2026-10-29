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
import { Button } from "@makeplane/propel/components/button";
import { Icon } from "@makeplane/propel/components/icon";
import { TimeTrackingOutline } from "@makeplane/propel/icons";
// helpers
import { canViewWorklogsForRole } from "@/helpers/worklog";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import { WorklogModal } from "../worklog-modal";

type TIssueActivityWorklogCreateButton = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

/** "Log time" in the header of the activity: opens the entries of the work item. */
export const IssueActivityWorklogCreateButton = observer(function IssueActivityWorklogCreateButton(
  props: TIssueActivityWorklogCreateButton
) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  const [isModalOpen, setIsModalOpen] = useState(false);
  // store hooks
  const { getProjectById } = useProject();
  const { getProjectRoleByWorkspaceSlugAndProjectId } = useUserPermissions();
  // derived values
  const isTimeTrackingEnabled = Boolean(getProjectById(projectId)?.is_time_tracking_enabled);
  const canViewWorklogs = canViewWorklogsForRole(getProjectRoleByWorkspaceSlugAndProjectId(workspaceSlug, projectId));

  if (!isTimeTrackingEnabled || !canViewWorklogs) return <></>;

  return (
    <>
      <Button
        variant="secondary"
        size="sm"
        stretch="auto"
        onClick={() => setIsModalOpen(true)}
        disabled={disabled}
        icon={<Icon icon={TimeTrackingOutline} />}
        label={t("worklog.log_time")}
      />
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
