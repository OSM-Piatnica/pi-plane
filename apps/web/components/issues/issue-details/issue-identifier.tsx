/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import type { TIssueIdentifierProps, TIssueIdentifierSize, TIssueTypeIdentifier } from "@plane/types";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { useWorkspaceIssueTypes } from "@/hooks/use-workspace-issue-types";
import { IdentifierText } from "@/components/issues/issue-detail/identifier-text";
import { WorkItemTypeMarkIcon } from "./work-item-type-mark-icon";

const TYPE_MARK_SIZE: Record<TIssueIdentifierSize, number> = { xs: 14, sm: 14, md: 16, lg: 16 };

/** The mark of a work item type with its name as the tooltip: one component draws a type wherever it is shown. */
const WorkItemTypeMark = observer(function WorkItemTypeMark(props: {
  issueTypeId: string;
  size?: TIssueIdentifierSize;
}) {
  const { issueTypeId, size = "md" } = props;
  const { workspaceSlug } = useParams();
  const { typeMap } = useWorkspaceIssueTypes(workspaceSlug?.toString());
  const issueType = typeMap[issueTypeId];
  if (!issueType) return null;

  return (
    <Tooltip label={issueType.name}>
      <span className="grid flex-shrink-0 place-items-center" aria-label={issueType.name}>
        <WorkItemTypeMarkIcon issueType={issueType} size={TYPE_MARK_SIZE[size]} />
      </span>
    </Tooltip>
  );
});

export const IssueIdentifier = observer(function IssueIdentifier(props: TIssueIdentifierProps) {
  const { projectId, variant, size, displayProperties, enableClickToCopyIdentifier = false } = props;
  const { getProjectIdentifierById, getProjectById } = useProject();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const isUsingStoreData = "issueId" in props;
  const issue = isUsingStoreData ? getIssueById(props.issueId) : null;
  const projectIdentifier = isUsingStoreData ? getProjectIdentifierById(projectId) : props.projectIdentifier;
  const issueSequenceId = isUsingStoreData ? issue?.sequence_id : props.issueSequenceId;
  const issueTypeId = isUsingStoreData ? issue?.type_id : props.issueTypeId;
  const shouldRenderIssueID = displayProperties ? displayProperties.key : true;
  // The type mark follows its own display property, so it is only offered where the layout has the property, and
  // only in projects that use work item types
  const shouldRenderIssueType =
    !!issueTypeId &&
    !!displayProperties &&
    displayProperties.issue_type !== false &&
    !!getProjectById(projectId)?.is_issue_type_enabled;

  if (!shouldRenderIssueID && !shouldRenderIssueType) return null;

  const identifier = `${projectIdentifier}-${issueSequenceId}`;

  return (
    <div className="flex shrink-0 items-center gap-1.5">
      {shouldRenderIssueType && issueTypeId && <WorkItemTypeMark issueTypeId={issueTypeId} size={size} />}
      {shouldRenderIssueID && (
        <IdentifierText
          identifier={identifier}
          enableClickToCopyIdentifier={enableClickToCopyIdentifier}
          variant={variant}
          size={size}
        />
      )}
    </div>
  );
});

/** The type of a work item on its own, where no identifier is shown (drafts): the same mark as the identifier's. */
export const IssueTypeIdentifier = observer(function IssueTypeIdentifier(props: TIssueTypeIdentifier) {
  const { issueTypeId, size = "sm" } = props;
  if (!issueTypeId) return null;
  return <WorkItemTypeMark issueTypeId={issueTypeId} size={size} />;
});
