/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { renderTaggedText } from "@/helpers/tagged-text";
import { ChatOutline } from "@makeplane/propel/icons";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";

type TIssueLinkActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueLinkActivity = observer(function IssueLinkActivity(props: TIssueLinkActivity) {
  const { activityId, showIssue = false, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  const isCreated = activity.verb === "created";
  const isUpdated = activity.verb === "updated";
  const href = isCreated ? activity.new_value : activity.old_value;
  const message = isCreated
    ? showIssue
      ? t("activity_feed.issue.link.added_with_issue")
      : t("activity_feed.issue.link.added")
    : isUpdated
      ? showIssue
        ? t("activity_feed.issue.link.updated_with_issue")
        : t("activity_feed.issue.link.updated")
      : showIssue
        ? t("activity_feed.issue.link.removed_with_issue")
        : t("activity_feed.issue.link.removed");
  return (
    <IssueActivityBlockComponent
      icon={<ChatOutline width={14} height={14} className="text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, {
        link: (text) => (
          <a
            href={`${href}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
          >
            {text}
          </a>
        ),
        issue: () => <IssueLink activityId={activityId} />,
      })}
    </IssueActivityBlockComponent>
  );
});
