/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Layers } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { renderTaggedText } from "@/helpers/tagged-text";
import {
  IssueActivityBlockComponent,
  IssueLink,
} from "@/components/issues/issue-detail/issue-activity/activity/actions";
import { SwitcherIcon } from "@/components/common/switcher-label";
import { useWorkspaceIssueTypes } from "@/hooks/use-workspace-issue-types";

export type TIssueTypeActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssueTypeActivity = observer(function IssueTypeActivity(props: TIssueTypeActivity) {
  const { activityId, showIssue = true, ends } = props;
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const { typeMap } = useWorkspaceIssueTypes(workspaceSlug?.toString(), false);

  const activity = getActivityById(activityId);
  if (!activity) return null;

  const oldType = activity.old_identifier ? typeMap[String(activity.old_identifier)] : undefined;
  const newType = activity.new_identifier ? typeMap[String(activity.new_identifier)] : undefined;

  const typeChip = (type: NonNullable<typeof oldType>) => (
    <span className="inline-flex items-center gap-1 rounded border border-subtle bg-surface-2 px-1 py-0.5 text-11">
      <SwitcherIcon logo_props={type.logo_props} LabelIcon={Layers} size={10} />
      {type.name}
    </span>
  );

  return (
    <IssueActivityBlockComponent
      icon={<Layers height={14} width={14} className="text-secondary" />}
      activityId={activityId}
      ends={ends}
    >
      <>
        {renderTaggedText(
          t("app_text.activity.issue_type_changed", {
            kind: oldType && newType ? "both" : oldType ? "from" : newType ? "to" : "other",
          }),
          { old: () => (oldType ? typeChip(oldType) : null), new: () => (newType ? typeChip(newType) : null) }
        )}
        {showIssue ? (
          <>
            {" "}
            {t("app_text.activity.on_work_item")} <IssueLink activityId={activityId} />
          </>
        ) : null}
      </>
    </IssueActivityBlockComponent>
  );
});
