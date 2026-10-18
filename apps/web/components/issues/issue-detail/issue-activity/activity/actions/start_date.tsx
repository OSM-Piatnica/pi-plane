/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { renderTaggedText } from "@/helpers/tagged-text";
import { CalendarOutline } from "@makeplane/propel/icons";
// hooks
import { renderFormattedDate } from "@plane/utils";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";
// helpers

type TIssueStartDateActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueStartDateActivity = observer(function IssueStartDateActivity(props: TIssueStartDateActivity) {
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
      ? t("activity_feed.issue.start_date.set_with_issue")
      : t("activity_feed.issue.start_date.set")
    : showIssue
      ? t("activity_feed.issue.start_date.removed_with_issue")
      : t("activity_feed.issue.start_date.removed");
  return (
    <IssueActivityBlockComponent
      icon={<CalendarOutline width={14} height={14} className="text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, {
        value: () => <span className="font-medium text-primary">{renderFormattedDate(activity.new_value)}</span>,
        issue: () => <IssueLink activityId={activityId} />,
      })}
    </IssueActivityBlockComponent>
  );
});
