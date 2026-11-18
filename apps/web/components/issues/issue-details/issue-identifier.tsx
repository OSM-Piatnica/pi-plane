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
import { Logo } from "@plane/blocks/emoji-icon-picker";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { EpicOutline, WorkItemsOutline } from "@makeplane/propel/icons";
import type { TIssueIdentifierProps, TIssueIdentifierSize, TIssueTypeIdentifier, TLogoProps } from "@plane/types";
import { SwitcherIcon } from "@/components/common/switcher-label";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { getWorkItemTypeMarkKind } from "@/helpers/work-item-type-mark";
import { useWorkspaceIssueTypes } from "@/hooks/use-workspace-issue-types";
import { IdentifierText } from "@/components/issues/issue-detail/identifier-text";

const TYPE_MARK_SIZE: Record<TIssueIdentifierSize, number> = { xs: 14, sm: 14, md: 16, lg: 16 };

/** The mark of a work item type: the logo an admin picked, else a built-in one (Epic, general). */
const WorkItemTypeMark = observer(function WorkItemTypeMark(props: {
  issueTypeId: string;
  size?: TIssueIdentifierSize;
}) {
  const { issueTypeId, size = "md" } = props;
  const { workspaceSlug } = useParams();
  const { typeMap } = useWorkspaceIssueTypes(workspaceSlug?.toString());
  const issueType = typeMap[issueTypeId];
  if (!issueType) return null;

  const iconSize = TYPE_MARK_SIZE[size];
  const kind = getWorkItemTypeMarkKind(issueType);
  let mark;
  if (kind === "logo") mark = <Logo logo={issueType.logo_props as TLogoProps} size={iconSize} />;
  else if (kind === "epic") mark = <EpicOutline width={iconSize} height={iconSize} className="text-accent-primary" />;
  else mark = <WorkItemsOutline width={iconSize} height={iconSize} className="text-tertiary" />;

  return (
    <Tooltip label={issueType.name}>
      <span className="grid flex-shrink-0 place-items-center" aria-label={issueType.name}>
        {mark}
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

export const IssueTypeIdentifier = observer(function IssueTypeIdentifier(props: TIssueTypeIdentifier) {
  const { issueTypeId } = props;
  const { workspaceSlug } = useParams();
  const { typeMap, isLoading } = useWorkspaceIssueTypes(workspaceSlug?.toString());

  if (!issueTypeId || isLoading) return null;
  const issueType = typeMap[issueTypeId];
  if (!issueType) return null;

  return (
    <span className="inline-flex items-center gap-1 rounded border border-subtle bg-surface-2 px-1.5 py-0.5 text-11 text-secondary">
      <SwitcherIcon logo_props={issueType.logo_props} LabelIcon={Layers} size={10} />
      <span className="truncate">{issueType.name}</span>
    </span>
  );
});
