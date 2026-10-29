/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { PriorityIcon, StateGroupIcon } from "@plane/blocks/icons";
import { useTranslation } from "@plane/i18n";
import type { TIssue, TStateGroups } from "@plane/types";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { getStateName } from "@plane/utils";
import { IssueIdentifier } from "@/components/issues/issue-details/issue-identifier";
// local imports
import { WorkItemPreviewCardDate } from "./date";

type Props = {
  projectId: string;
  stateDetails: {
    group?: TStateGroups;
    id?: string;
    name?: string;
  };
  workItem: Pick<
    TIssue,
    "id" | "name" | "sequence_id" | "priority" | "start_date" | "finish_date" | "target_date" | "type_id"
  >;
};

export const WorkItemPreviewCard = observer(function WorkItemPreviewCard(props: Props) {
  const { projectId, stateDetails, workItem } = props;
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const { getProjectIdentifierById } = useProject();
  const { getStateById } = useProjectState();
  // derived values
  const projectIdentifier = getProjectIdentifierById(projectId);
  const fallbackStateDetails = stateDetails.id ? getStateById(stateDetails.id) : undefined;
  const stateGroup = stateDetails?.group ?? fallbackStateDetails?.group ?? "backlog";
  const rawStateName = stateDetails?.name ?? fallbackStateDetails?.name;
  const stateName = rawStateName ? getStateName(rawStateName, t) : rawStateName;

  return (
    <div className="w-72 space-y-2">
      <div className="flex items-center justify-between gap-3 text-secondary">
        <IssueIdentifier
          size="xs"
          variant="secondary"
          projectId={projectId}
          projectIdentifier={projectIdentifier}
          issueSequenceId={workItem.sequence_id}
          issueTypeId={workItem.type_id}
        />
        <div className="flex shrink-0 items-center gap-1">
          <StateGroupIcon stateGroup={stateGroup} className="size-3 shrink-0" />
          <p className="text-11 font-medium">{stateName}</p>
        </div>
      </div>
      <div>
        <h6 className="text-13 wrap-break-word">{workItem.name}</h6>
      </div>
      <div className="flex h-5 items-center gap-1">
        <PriorityIcon priority={workItem.priority} />
        <WorkItemPreviewCardDate
          startDate={workItem.start_date}
          stateGroup={stateGroup}
          finishDate={workItem.finish_date ?? null}
          targetDate={workItem.target_date}
        />
      </div>
    </div>
  );
});
