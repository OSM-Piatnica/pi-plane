/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { renderTaggedText } from "@/helpers/tagged-text";
import { EstimateOutline } from "@makeplane/propel/icons";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";

type TIssueEstimateActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueEstimateActivity = observer(function IssueEstimateActivity(props: TIssueEstimateActivity) {
  const { activityId, showIssue = true, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  const message = activity.new_value
    ? showIssue
      ? t("activity_feed.issue.estimate.set_with_issue")
      : t("activity_feed.issue.estimate.set")
    : showIssue
      ? t("activity_feed.issue.estimate.removed_with_issue")
      : t("activity_feed.issue.estimate.removed");
  return (
    <IssueActivityBlockComponent
      icon={<EstimateOutline className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, {
        value: () => <>{activity.new_value ? activity.new_value : activity?.old_value}</>,
        issue: () => <IssueLink activityId={activityId} />,
      })}
    </IssueActivityBlockComponent>
  );
});
