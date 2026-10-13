/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { useState, useRef, forwardRef } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { MoreHorizontal } from "lucide-react";
// plane imports
import { useOutsideClickDetector } from "@plane/hooks";
import { useTranslation } from "@plane/i18n";
import { Popover } from "@plane/propel/popover";
import type { TIssue } from "@plane/types";
import { ControlLink } from "@plane/ui";
import { cn, generateWorkItemLink } from "@plane/utils";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssues } from "@/hooks/store/use-issues";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import useIssuePeekOverviewRedirection from "@/hooks/use-issue-peek-overview-redirection";
import { usePlatformOS } from "@/hooks/use-platform-os";
// plane web components
import { calendarLayerState } from "@/store/issue/helpers/calendar-layers";
import { IssueIdentifier } from "@/plane-web/components/issues/issue-details/issue-identifier";
// local components
import { WorkItemPreviewCard } from "../../preview-card";
import { getIssueDateStatuses } from "../utils";
import type { TRenderQuickActions } from "../list/list-view-types";
import type { CalendarStoreType } from "./base-calendar-root";

type Props = {
  issue: TIssue;
  /** The day tile this block is rendered in (yyyy-mm-dd). */
  date?: string;
  quickActions: TRenderQuickActions;
  isDragging?: boolean;
  isEpic?: boolean;
};

export const CalendarIssueBlock = observer(
  forwardRef(function CalendarIssueBlock(props: Props, ref: React.ForwardedRef<HTMLAnchorElement>) {
    const { issue, date, quickActions, isDragging = false, isEpic = false } = props;
    const { t } = useTranslation();
    const calendarLayer = calendarLayerState.layer;
    // states
    const [isMenuActive, setIsMenuActive] = useState(false);
    // refs
    const blockRef = useRef(null);
    const menuActionRef = useRef<HTMLDivElement | null>(null);
    // hooks
    const { workspaceSlug } = useParams();
    const { getProjectStates } = useProjectState();
    const { getIsIssuePeeked } = useIssueDetail();
    const { handleRedirection } = useIssuePeekOverviewRedirection(isEpic);
    const { isMobile } = usePlatformOS();
    const storeType = useIssueStoreType() as CalendarStoreType;
    const { issuesFilter } = useIssues(storeType);
    const { getProjectIdentifierById, getProjectById } = useProject();

    const stateColor = getProjectStates(issue?.project_id)?.find((state) => state?.id == issue?.state_id)?.color || "";
    const projectIdentifier = getProjectIdentifierById(issue?.project_id);

    // handlers
    const handleIssuePeekOverview = (workItem: TIssue) =>
      handleRedirection(workspaceSlug.toString(), workItem, isMobile);

    useOutsideClickDetector(menuActionRef, () => setIsMenuActive(false));

    const customActionButton = (
      <div
        ref={menuActionRef}
        role="presentation"
        className={`w-full cursor-pointer rounded-sm p-1 text-placeholder hover:bg-layer-1 ${
          isMenuActive ? "bg-layer-1-active text-primary" : "text-secondary"
        }`}
        onClick={() => setIsMenuActive(!isMenuActive)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") setIsMenuActive(!isMenuActive);
        }}
      >
        <MoreHorizontal className="h-3.5 w-3.5" />
      </div>
    );

    const isMenuActionRefAboveScreenBottom =
      menuActionRef?.current && menuActionRef?.current?.getBoundingClientRect().bottom < window.innerHeight - 220;

    const placement = isMenuActionRefAboveScreenBottom ? "bottom-end" : "top-end";

    const workItemLink = generateWorkItemLink({
      workspaceSlug: workspaceSlug?.toString(),
      projectId: issue?.project_id,
      issueId: issue?.id,
      projectIdentifier,
      sequenceId: issue?.sequence_id,
      isEpic,
      isArchived: !!issue?.archived_at,
    });

    // distinct labelling per layer: a deadline is a "Due" chip, a scheduled item marks its finish day
    const stateGroup = getProjectStates(issue?.project_id)?.find((state) => state?.id == issue?.state_id)?.group;
    const isOverdue = getIssueDateStatuses(issue, stateGroup, getProjectById(issue?.project_id)?.timezone).overdue;
    const layerMarker =
      calendarLayer === "deadlines"
        ? {
            label: t("issue.dates.calendar.due_marker"),
            className: isOverdue ? "bg-danger-subtle text-danger-primary" : "bg-layer-2 text-secondary",
          }
        : date && issue.finish_date && issue.finish_date.slice(0, 10) === date
          ? { label: t("issue.dates.calendar.finish_marker"), className: "bg-accent-primary/10 text-accent-primary" }
          : null;

    return (
      <Popover delay={100} openOnHover>
        <Popover.Button
          className="w-full"
          render={
            <ControlLink
              id={`issue-${issue.id}`}
              href={workItemLink}
              onClick={() => handleIssuePeekOverview(issue)}
              className="block w-full rounded-sm border-b border-subtle text-13 text-primary hover:border-subtle-1 md:border-[1px]"
              disabled={!!issue?.tempId || isMobile}
              ref={ref}
            >
              <>
                {issue?.tempId !== undefined && (
                  <div className="absolute top-0 left-0 z-[99999] h-full w-full animate-pulse bg-surface-1/20" />
                )}

                <div
                  ref={blockRef}
                  className={cn(
                    "group/calendar-block flex h-10 w-full items-center justify-between gap-1.5 rounded-sm px-4 py-1.5 md:h-8 md:px-1",
                    {
                      "border-accent-strong bg-surface-2 shadow-raised-200": isDragging,
                      "bg-surface-1 hover:bg-surface-2": !isDragging,
                      "border border-accent-strong hover:border-accent-strong": getIsIssuePeeked(issue.id),
                    }
                  )}
                >
                  <div className="flex h-full items-center gap-1.5 truncate">
                    <span
                      className="h-full w-0.5 flex-shrink-0 rounded-sm"
                      style={{
                        backgroundColor: stateColor,
                      }}
                    />
                    {issue.project_id && (
                      <IssueIdentifier
                        issueId={issue.id}
                        projectId={issue.project_id}
                        size="xs"
                        variant="tertiary"
                        displayProperties={issuesFilter?.issueFilters?.displayProperties}
                      />
                    )}
                    <div className="truncate text-13 font-medium md:text-11 md:font-regular">{issue.name}</div>
                  </div>
                  {layerMarker && (
                    <span
                      className={cn(
                        "flex-shrink-0 rounded-sm px-1 text-10 font-medium group-hover/calendar-block:hidden",
                        layerMarker.className
                      )}
                    >
                      {layerMarker.label}
                    </span>
                  )}
                  <div
                    className={cn("size-5 flex-shrink-0", {
                      "hidden group-hover/calendar-block:block": !isMobile,
                      block: isMenuActive,
                    })}
                    role="presentation"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                    onKeyDown={(e) => e.stopPropagation()}
                  >
                    {quickActions({
                      issue,
                      parentRef: blockRef,
                      customActionButton,
                      placement,
                    })}
                  </div>
                </div>
              </>
            </ControlLink>
          }
        />
        <Popover.Panel side="bottom" align="start">
          <>
            {issue.project_id && (
              <WorkItemPreviewCard
                projectId={issue.project_id}
                stateDetails={{
                  id: issue.state_id ?? undefined,
                }}
                workItem={issue}
              />
            )}
          </>
        </Popover.Panel>
      </Popover>
    );
  })
);

CalendarIssueBlock.displayName = "CalendarIssueBlock";
