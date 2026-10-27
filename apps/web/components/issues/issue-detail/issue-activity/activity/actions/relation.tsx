/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { renderTaggedText } from "@/helpers/tagged-text";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useTimeLineRelationOptions } from "@/components/relations";
import type { TIssueRelationTypes } from "@plane/types";
//
import { IssueActivityBlockComponent } from "./";

type TIssueRelationActivity = { activityId: string; ends: "top" | "bottom" | undefined };

export const IssueRelationActivity = observer(function IssueRelationActivity(props: TIssueRelationActivity) {
  const { activityId, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);
  const ISSUE_RELATION_OPTIONS = useTimeLineRelationOptions();
  const isAdded = activity?.old_value === "";
  const getMessage = (): string | undefined => {
    switch (activity?.field) {
      case "blocking":
        return isAdded
          ? t("activity_feed.issue.relation.blocking.added")
          : t("activity_feed.issue.relation.blocking.removed");
      case "blocked_by":
        return isAdded
          ? t("activity_feed.issue.relation.blocked_by.added")
          : t("activity_feed.issue.relation.blocked_by.removed");
      case "duplicate":
        return isAdded
          ? t("activity_feed.issue.relation.duplicate.added")
          : t("activity_feed.issue.relation.duplicate.removed");
      case "implements":
        return isAdded
          ? t("activity_feed.issue.relation.implements.added")
          : t("activity_feed.issue.relation.implements.removed");
      case "implemented_by":
        return isAdded
          ? t("activity_feed.issue.relation.implemented_by.added")
          : t("activity_feed.issue.relation.implemented_by.removed");
      case "causes":
        return isAdded
          ? t("activity_feed.issue.relation.causes.added")
          : t("activity_feed.issue.relation.causes.removed");
      case "caused_by":
        return isAdded
          ? t("activity_feed.issue.relation.caused_by.added")
          : t("activity_feed.issue.relation.caused_by.removed");
      case "clones":
        return isAdded
          ? t("activity_feed.issue.relation.clones.added")
          : t("activity_feed.issue.relation.clones.removed");
      case "cloned_by":
        return isAdded
          ? t("activity_feed.issue.relation.cloned_by.added")
          : t("activity_feed.issue.relation.cloned_by.removed");
      case "tests":
        return isAdded
          ? t("activity_feed.issue.relation.tests.added")
          : t("activity_feed.issue.relation.tests.removed");
      case "tested_by":
        return isAdded
          ? t("activity_feed.issue.relation.tested_by.added")
          : t("activity_feed.issue.relation.tested_by.removed");
      case "start_before_finish":
        return isAdded
          ? t("activity_feed.issue.relation.start_before_finish.added")
          : t("activity_feed.issue.relation.start_before_finish.removed");
      case "finish_after_start":
        return isAdded
          ? t("activity_feed.issue.relation.finish_after_start.added")
          : t("activity_feed.issue.relation.finish_after_start.removed");
      case "relates_to":
        return isAdded
          ? t("activity_feed.issue.relation.relates_to.added")
          : t("activity_feed.issue.relation.relates_to.removed");
      case "start_before":
        return isAdded
          ? t("activity_feed.issue.relation.start_before.added")
          : t("activity_feed.issue.relation.start_before.removed");
      case "start_after":
        return isAdded
          ? t("activity_feed.issue.relation.start_after.added")
          : t("activity_feed.issue.relation.start_after.removed");
      case "finish_before":
        return isAdded
          ? t("activity_feed.issue.relation.finish_before.added")
          : t("activity_feed.issue.relation.finish_before.removed");
      case "finish_after":
        return isAdded
          ? t("activity_feed.issue.relation.finish_after.added")
          : t("activity_feed.issue.relation.finish_after.removed");
      default:
        return undefined;
    }
  };
  const message = getMessage();

  if (!activity) return <></>;
  return (
    <IssueActivityBlockComponent
      icon={activity.field ? ISSUE_RELATION_OPTIONS[activity.field as TIssueRelationTypes]?.icon(14) : <></>}
      activityId={activityId}
      ends={ends}
    >
      {message &&
        renderTaggedText(message, {
          value: () => (
            <span className="font-medium text-primary">
              {activity.old_value === "" ? activity.new_value : activity.old_value}
            </span>
          ),
        })}
    </IssueActivityBlockComponent>
  );
});
