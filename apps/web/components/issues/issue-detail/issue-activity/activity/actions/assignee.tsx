/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { renderTaggedText } from "@/helpers/tagged-text";
// icons
import { MembersOutline } from "@makeplane/propel/icons";
// hooks;
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";

type TIssueAssigneeActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueAssigneeActivity = observer(function IssueAssigneeActivity(props: TIssueAssigneeActivity) {
  const { activityId, ends, showIssue = true } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  const message =
    activity.old_value === ""
      ? showIssue
        ? t("activity_feed.issue.assignee.added_with_issue")
        : t("activity_feed.issue.assignee.added")
      : showIssue
        ? t("activity_feed.issue.assignee.removed_with_issue")
        : t("activity_feed.issue.assignee.removed");
  return (
    <IssueActivityBlockComponent
      icon={<MembersOutline className="h-3.5 w-3.5 flex-shrink-0 text-secondary" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, {
        user: () => (
          <a
            href={`/${activity.workspace_detail?.slug}/profile/${activity.new_identifier ?? activity.old_identifier}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center font-medium text-primary capitalize hover:underline"
          >
            {activity.new_value && activity.new_value !== "" ? activity.new_value : activity.old_value}
          </a>
        ),
        issue: () => <IssueLink activityId={activityId} />,
      })}
    </IssueActivityBlockComponent>
  );
});
