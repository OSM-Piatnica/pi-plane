/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Maciej Szymczak and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { TimeTrackingOutline } from "@makeplane/propel/icons";
import type { TIssueActivityComment } from "@plane/types";
// components
import { IssueActivityBlockComponent } from "@/components/issues/issue-detail/issue-activity/activity/actions";
// helpers
import { renderTaggedText } from "@/helpers/tagged-text";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";

type TIssueActivityWorklog = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  activityComment: TIssueActivityComment;
  ends?: "top" | "bottom";
};

const value = (text: string) => <span className="font-medium text-primary">{text}</span>;

/** An entry of the activity feed: time was logged on the work item, changed or removed. */
export const IssueActivityWorklog = observer(function IssueActivityWorklog(props: TIssueActivityWorklog) {
  const { activityComment, ends } = props;
  const { t } = useTranslation();
  // store hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  // derived values
  const activity = getActivityById(activityComment.id);

  if (!activity) return <></>;

  const message =
    activity.verb === "created"
      ? t("worklog.logged", { duration: activity.new_value ?? "" })
      : activity.verb === "updated"
        ? t("worklog.updated", { from: activity.old_value ?? "", to: activity.new_value ?? "" })
        : t("worklog.removed", { duration: activity.old_value ?? "" });

  return (
    <IssueActivityBlockComponent
      icon={<TimeTrackingOutline width={14} height={14} className="text-secondary" aria-hidden="true" />}
      activityId={activityComment.id}
      ends={ends}
    >
      {renderTaggedText(message, { value, old: value, new: value })}
    </IssueActivityBlockComponent>
  );
});
