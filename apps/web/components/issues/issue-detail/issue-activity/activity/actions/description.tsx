/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { renderTaggedText } from "@/helpers/tagged-text";
import { AlignLeftOutline } from "@makeplane/propel/icons";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";

type TIssueDescriptionActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueDescriptionActivity = observer(function IssueDescriptionActivity(props: TIssueDescriptionActivity) {
  const { activityId, showIssue = true, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  const message = showIssue
    ? t("activity_feed.issue.description.updated_with_issue")
    : t("activity_feed.issue.description.updated");
  return (
    <IssueActivityBlockComponent
      icon={<AlignLeftOutline width={14} height={14} className="text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, { issue: () => <IssueLink activityId={activityId} /> })}
    </IssueActivityBlockComponent>
  );
});
