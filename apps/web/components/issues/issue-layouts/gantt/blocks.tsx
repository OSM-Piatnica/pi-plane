/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { Popover, PopoverContent, PopoverTrigger } from "@makeplane/propel/components/popover";
import { Tooltip } from "@makeplane/propel/components/tooltip";
import { ControlLink } from "@plane/blocks/layout";
import { useTranslation } from "@plane/i18n";
import type { TTimelineColorBy } from "@plane/types";
import { GANTT_TIMELINE_TYPE } from "@plane/types";
import { findTotalDaysInRange, generateWorkItemLink } from "@plane/utils";
// components
import { getTimelineDatesText } from "@/components/gantt-chart/blocks/due-marker";
import { SIDEBAR_WIDTH_VAR } from "@/components/gantt-chart/constants";
import { isBlockRolledUp } from "@/components/gantt-chart/views/helpers";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssues } from "@/hooks/store/use-issues";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import useIssuePeekOverviewRedirection from "@/hooks/use-issue-peek-overview-redirection";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { useChartPalette } from "@/hooks/use-chart-palette";
import { useTimeLineChart } from "@/hooks/use-timeline-chart";
import { IssueIdentifier } from "@/components/issues/issue-details/issue-identifier";
import { IssueStats } from "@/components/issues/issue-layouts/issue-stats";
// local imports
import { WorkItemPreviewCard } from "../../preview-card";
import { getBlockViewDetails } from "../utils";
import { getBarColor } from "./bar-color";
import type { GanttStoreType } from "./base-gantt-root";

type Props = {
  issueId: string;
  isEpic?: boolean;
};

type TGanttBlockProps = Props & {
  colorBy?: TTimelineColorBy;
};

export const IssueGanttBlock = observer(function IssueGanttBlock(props: TGanttBlockProps) {
  const { issueId, isEpic, colorBy } = props;
  // router
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug?.toString();
  // store hooks
  const { getProjectStates } = useProjectState();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  // hooks
  const { getProjectIdentifierById } = useProject();
  const { isMobile } = usePlatformOS();
  const chartPalette = useChartPalette();
  const { handleRedirection } = useIssuePeekOverviewRedirection(isEpic);
  const { getBlockById } = useTimeLineChart(GANTT_TIMELINE_TYPE.ISSUE);
  const { t } = useTranslation();

  // derived values
  const issueDetails = getIssueById(issueId);
  const isRolledUp = isBlockRolledUp(getBlockById(issueId));
  const stateDetails =
    issueDetails && getProjectStates(issueDetails?.project_id)?.find((state) => state?.id == issueDetails?.state_id);

  const barColor = getBarColor({
    colorBy,
    stateColor: stateDetails?.color,
    projectIdentifier: getProjectIdentifierById(issueDetails?.project_id),
    sequenceId: issueDetails?.sequence_id,
    palette: chartPalette,
  });

  // the bar spans start to finish; the due date is a separate deadline marker and never part of the bar
  const { blockStyle } = getBlockViewDetails(
    { start_date: issueDetails?.start_date, target_date: issueDetails?.finish_date },
    barColor ?? ""
  );

  const handleIssuePeekOverview = () => handleRedirection(workspaceSlug, issueDetails, isMobile);

  const duration = findTotalDaysInRange(issueDetails?.start_date, issueDetails?.finish_date) || 0;

  const hasStart = !!issueDetails?.start_date;
  const hasFinish = !!issueDetails?.finish_date;

  // only a start or only a finish: a labeled marker, never a bar with an invented end
  if (hasStart !== hasFinish && !isRolledUp) {
    return (
      <Tooltip
        disabled={isMobile}
        layout="stacked"
        label={getTimelineDatesText(
          {
            start: issueDetails?.start_date,
            finish: issueDetails?.finish_date,
            due: issueDetails?.target_date,
          },
          t
        )}
      >
        <div
          id={`issue-${issueId}`}
          className="relative flex h-full w-full cursor-pointer items-center justify-center"
          // oxlint-disable-next-line prefer-tag-over-role -- the marker holds block content a <button> cannot contain
          role="button"
          tabIndex={0}
          onClick={handleIssuePeekOverview}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") handleIssuePeekOverview();
          }}
        >
          <div className="h-3.5 w-3.5 rotate-45 rounded-xs" style={{ backgroundColor: barColor }} />
          <div
            className={`absolute flex max-w-[260px] items-center gap-1 truncate text-13 whitespace-nowrap text-primary ${
              hasStart ? "left-full pl-2" : "right-full pr-2"
            }`}
          >
            <span className="rounded-sm bg-layer-1 px-1 text-11 font-medium text-secondary">
              {hasStart ? t("issue.dates.timeline.start_only") : t("issue.dates.timeline.finish_only")}
            </span>
            <span className="truncate">{issueDetails?.name}</span>
          </div>
        </div>
      </Tooltip>
    );
  }

  return (
    <Popover>
      <PopoverTrigger
        openOnHover
        delay={100}
        render={
          // react-doctor-disable-next-line click-events-have-key-events, no-static-element-interactions -- render target of PopoverTrigger, which supplies the interactive role, focus and keyboard handling
          <div // oxlint-disable-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- same reason
            id={`issue-${issueId}`}
            className="space-between relative flex h-full w-full cursor-pointer items-center rounded-sm"
            style={blockStyle}
            onClick={handleIssuePeekOverview}
          >
            <div className="absolute top-0 left-0 h-full w-full bg-surface-1/50" />
            {isRolledUp && (
              // hatched like a rolled-up bar in project plans: the dates come from the work items below
              <div
                aria-hidden
                title={t("timeline_rollup.rolled_up_bar")}
                className="absolute top-0 left-0 h-full w-full rounded-sm border border-dashed border-strong"
                style={{
                  backgroundImage:
                    "repeating-linear-gradient(135deg, transparent 0 5px, rgba(128, 128, 128, 0.28) 5px 10px)",
                }}
              />
            )}
            <div
              className="sticky w-auto flex-1 truncate overflow-hidden px-2.5 py-1 text-13 text-primary"
              style={{ left: SIDEBAR_WIDTH_VAR }}
            >
              {issueDetails?.name}
            </div>
            {isEpic && (
              <IssueStats
                issueId={issueId}
                className="sticky mx-2 w-auto flex-shrink-0 justify-end truncate overflow-hidden font-medium text-primary"
                showProgressText={duration >= 2}
              />
            )}
          </div>
        }
      />
      <PopoverContent side="bottom" align="start" sideOffset={8}>
        {issueDetails && issueDetails?.project_id && (
          <WorkItemPreviewCard
            projectId={issueDetails.project_id}
            stateDetails={{
              id: issueDetails.state_id ?? undefined,
            }}
            workItem={issueDetails}
          />
        )}
      </PopoverContent>
    </Popover>
  );
});

// rendering issues on gantt sidebar
export const IssueGanttSidebarBlock = observer(function IssueGanttSidebarBlock(props: Props) {
  const { issueId, isEpic = false } = props;
  // router
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug?.toString();
  // store hooks
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { isMobile } = usePlatformOS();
  const storeType = useIssueStoreType() as GanttStoreType;
  const { issuesFilter } = useIssues(storeType);
  const { getProjectIdentifierById } = useProject();

  // handlers
  const { handleRedirection } = useIssuePeekOverviewRedirection(isEpic);

  // derived values
  const issueDetails = getIssueById(issueId);
  const projectIdentifier = getProjectIdentifierById(issueDetails?.project_id);

  const handleIssuePeekOverview = (e: any) => {
    e.stopPropagation(true);
    e.preventDefault();
    handleRedirection(workspaceSlug, issueDetails, isMobile);
  };

  const workItemLink = generateWorkItemLink({
    workspaceSlug,
    projectId: issueDetails?.project_id,
    issueId,
    projectIdentifier,
    sequenceId: issueDetails?.sequence_id,
    isEpic,
  });

  return (
    <ControlLink
      id={`issue-${issueId}`}
      href={workItemLink}
      onClick={handleIssuePeekOverview}
      className="line-clamp-1 w-full cursor-pointer text-13 text-primary"
      disabled={!!issueDetails?.tempId}
    >
      <div className="relative flex h-full w-full cursor-pointer items-center gap-2">
        {issueDetails?.project_id && (
          <IssueIdentifier
            issueId={issueDetails.id}
            projectId={issueDetails.project_id}
            size="xs"
            variant="tertiary"
            displayProperties={issuesFilter?.issueFilters?.displayProperties}
          />
        )}
        <Tooltip label={issueDetails?.name ?? ""} layout="stacked" disabled={isMobile}>
          <span className="flex-grow truncate text-13 font-medium">{issueDetails?.name}</span>
        </Tooltip>
      </div>
    </ControlLink>
  );
});
