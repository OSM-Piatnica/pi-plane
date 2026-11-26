/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { MembersOutline } from "@makeplane/propel/icons";
import { isRaciRole } from "@plane/utils";
// helpers
import { renderTaggedText } from "@/helpers/tagged-text";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// local imports
import { IssueActivityBlockComponent } from "./helpers/activity-block";

type TIssueRaciActivity = { activityId: string; ends: "top" | "bottom" | undefined };

/**
 * A department got, changed or lost a RACI role on the work item. The department is named as it was at the time
 * (the activity keeps its label); the role is stored by its neutral name and shown in the reader's language.
 */
export const IssueRaciActivity = observer(function IssueRaciActivity(props: TIssueRaciActivity) {
  const { activityId, ends } = props;
  // hooks
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { t } = useTranslation();

  const activity = getActivityById(activityId);
  if (!activity) return <></>;

  const oldRole = isRaciRole(activity.old_value) ? activity.old_value : null;
  const newRole = isRaciRole(activity.new_value) ? activity.new_value : null;
  const message = !oldRole
    ? t("raci.activity.set")
    : !newRole
      ? t("raci.activity.removed")
      : t("raci.activity.changed");
  const roleName = (role: typeof oldRole) => (role ? t(`raci.roles.${role}.name`) : "");

  return (
    <IssueActivityBlockComponent
      icon={<MembersOutline className="size-3.5 text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      {renderTaggedText(message, {
        department: () => <span className="font-medium text-primary">{activity.comment}</span>,
        old_role: () => <span className="font-medium text-primary">{roleName(oldRole)}</span>,
        new_role: () => <span className="font-medium text-primary">{roleName(newRole)}</span>,
      })}
    </IssueActivityBlockComponent>
  );
});
