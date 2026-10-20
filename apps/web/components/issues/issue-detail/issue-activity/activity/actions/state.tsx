/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { getStateName } from "@plane/utils";
import { renderTaggedText } from "@/helpers/tagged-text";
// hooks
import { StateOutline } from "@makeplane/propel/icons";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";
// icons

type TIssueStateActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueStateActivity = observer(function IssueStateActivity(props: TIssueStateActivity) {
  const { activityId, showIssue = true, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  const message = showIssue ? t("activity_feed.issue.state.set_with_issue") : t("activity_feed.issue.state.set");
  return (
    <IssueActivityBlockComponent
      icon={<StateOutline className="h-4 w-4 flex-shrink-0 text-secondary" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, {
        value: () => <span className="font-medium text-primary">{getStateName(activity.new_value ?? "", t)}</span>,
        issue: () => <IssueLink activityId={activityId} />,
      })}
    </IssueActivityBlockComponent>
  );
});
