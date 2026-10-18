/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { renderTaggedText } from "@/helpers/tagged-text";
// hooks
import { ModuleOutline } from "@makeplane/propel/icons";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent } from "./";
// icons

type TIssueModuleActivity = { activityId: string; ends: "top" | "bottom" | undefined };

export const IssueModuleActivity = observer(function IssueModuleActivity(props: TIssueModuleActivity) {
  const { activityId, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;

  const message =
    activity.verb === "created"
      ? t("activity_feed.issue.module.added")
      : activity.verb === "updated"
        ? t("activity_feed.issue.module.set")
        : t("activity_feed.issue.module.removed");
  return (
    <IssueActivityBlockComponent
      icon={<ModuleOutline className="h-4 w-4 flex-shrink-0 text-secondary" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, {
        module: () => (
          <a
            href={`/${activity.workspace_detail?.slug}/projects/${activity.project}/modules/${activity.verb === "created" || activity.verb === "updated" ? activity.new_identifier : activity.old_identifier}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 truncate font-medium text-primary hover:underline"
          >
            <span className="truncate">
              {activity.verb === "created" || activity.verb === "updated" ? activity.new_value : activity.old_value}
            </span>
          </a>
        ),
      })}
    </IssueActivityBlockComponent>
  );
});
