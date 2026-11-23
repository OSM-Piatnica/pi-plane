/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { getShiftCause } from "@/helpers/reschedule";
import { renderTaggedText } from "@/helpers/tagged-text";
import { CalendarOutline } from "@makeplane/propel/icons";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useLocalizedDates } from "@/hooks/use-localized-dates";
// components
import { IssueActivityBlockComponent, IssueLink, ShiftCauseLink } from "./";
// helpers

type TIssueStartDateActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueStartDateActivity = observer(function IssueStartDateActivity(props: TIssueStartDateActivity) {
  const { activityId, showIssue = true, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();
  const { formatDate } = useLocalizedDates();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  // moved along with the work item it depends on: the entry names that one (there is no variant naming this one too)
  const cause = activity.new_value ? getShiftCause(activity) : undefined;
  const message = cause
    ? t("activity_feed.issue.start_date.shifted")
    : activity.new_value
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
        value: () => <span className="font-medium text-primary">{formatDate(activity.new_value)}</span>,
        issue: () => <IssueLink activityId={activityId} />,
        cause: () => <ShiftCauseLink cause={cause} />,
      })}
    </IssueActivityBlockComponent>
  );
});
