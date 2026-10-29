/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { renderTaggedText } from "@/helpers/tagged-text";
import { PriorityOutline } from "@makeplane/propel/icons";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";

type TIssuePriorityActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssuePriorityActivity = observer(function IssuePriorityActivity(props: TIssuePriorityActivity) {
  const { activityId, showIssue = true, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  const message = showIssue ? t("activity_feed.issue.priority.set_with_issue") : t("activity_feed.issue.priority.set");
  return (
    <IssueActivityBlockComponent
      icon={<PriorityOutline className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, {
        value: () => <span className="font-medium text-primary">{activity.new_value}</span>,
        issue: () => <IssueLink activityId={activityId} />,
      })}
    </IssueActivityBlockComponent>
  );
});
