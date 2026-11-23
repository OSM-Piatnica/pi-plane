/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * Modified by Okręgowa Spółdzielnia Mleczarska w Piątnicy in 2026.
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { EIssueServiceType } from "@plane/types";
import { BLOCK_HEIGHT } from "@/components/gantt-chart/constants";
import {
  buildDependencyPathD,
  buildGanttDependencyEdges,
  getDependencyAnchorSides,
  getBlockAnchorPoints,
} from "@/helpers/gantt-dependency-helpers";
import { isDependencyCritical } from "@/helpers/schedule-analysis.helper";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useGetIssueWeekendDays } from "@/hooks/use-project-weekend-days";
import { useScheduleAnalysis } from "@/hooks/use-schedule-analysis";
import { useTimeLineChartStore } from "@/hooks/use-timeline-chart";

type Props = {
  isEpic?: boolean;
};

const DEP_STROKE = "var(--txt-secondary)";
const DEP_MARKER = "color-mix(in srgb, var(--txt-secondary) 72%, black)";
const DEP_STROKE_INVALID = "#DC2626";
const DEP_MARKER_INVALID = "#B91C1C";
// the critical path: the colour of the frame around critical bars, and a heavier line
const DEP_STROKE_CRITICAL = "var(--border-danger-strong, #DC2626)";
const DEP_WIDTH = 2;
const DEP_WIDTH_CRITICAL = 3.5;

export const TimelineDependencyPaths = observer(function TimelineDependencyPaths(_props: Props) {
  const { blockIds, getBlockById, isDependencyEnabled } = useTimeLineChartStore();
  const { isCriticalPathEnabled, scheduleAnalysis } = useScheduleAnalysis();
  const {
    relation,
    issue: { getIssueById },
  } = useIssueDetail(EIssueServiceType.ISSUES);
  const getWeekendDays = useGetIssueWeekendDays();

  if (!isDependencyEnabled || !blockIds?.length) return null;

  const relationMap = relation.relationMap;
  const getDates = (issueId: string) => {
    const issue = getIssueById(issueId);
    const block = getBlockById(issueId);
    return {
      start_date: issue?.start_date ?? block?.start_date ?? null,
      // dependencies follow the schedule (start and finish) only; the due date never takes part. The
      // block's bar end is the finish date for work items.
      finish_date: issue?.finish_date ?? block?.target_date ?? null,
    };
  };

  const edges = buildGanttDependencyEdges(blockIds, relationMap, getDates, relation.getRelationLag, getWeekendDays);
  if (!edges.length) return null;

  const indexById = new Map(blockIds.map((id, index) => [id, index]));

  return (
    <svg className="pointer-events-none absolute inset-0 z-[6] h-full w-full overflow-visible">
      <defs>
        <marker id="gantt-dep-arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={DEP_MARKER} />
        </marker>
        <marker id="gantt-dep-arrow-invalid" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={DEP_MARKER_INVALID} />
        </marker>
        {/* sized in user space: the heavier line must not scale the arrow head up */}
        <marker
          id="gantt-dep-arrow-critical"
          markerUnits="userSpaceOnUse"
          markerWidth="12"
          markerHeight="12"
          refX="10"
          refY="5"
          orient="auto"
        >
          <path d="M0,0 L10,5 L0,10 Z" fill={DEP_STROKE_CRITICAL} />
        </marker>
      </defs>
      {edges.map((edge) => {
        const fromBlock = getBlockById(edge.sourceId);
        const toBlock = getBlockById(edge.targetId);
        const fromIndex = indexById.get(edge.sourceId);
        const toIndex = indexById.get(edge.targetId);
        if (!fromBlock || !toBlock || fromIndex === undefined || toIndex === undefined) return null;

        const fromAnchor = getBlockAnchorPoints(fromBlock, fromIndex, BLOCK_HEIGHT);
        const toAnchor = getBlockAnchorPoints(toBlock, toIndex, BLOCK_HEIGHT);
        if (!fromAnchor || !toAnchor) return null;

        const sides = getDependencyAnchorSides(edge.relationType);
        const from = fromAnchor[sides.from];
        const to = toAnchor[sides.to];
        const d = buildDependencyPathD(from.x, from.y, to.x, to.y, sides.from, sides.to);
        // a broken rule stays red and thin: it is not part of a path that holds
        const isCritical = isCriticalPathEnabled && !edge.isInvalid && isDependencyCritical(scheduleAnalysis, edge);
        const stroke = edge.isInvalid ? DEP_STROKE_INVALID : isCritical ? DEP_STROKE_CRITICAL : DEP_STROKE;
        const marker = edge.isInvalid
          ? "gantt-dep-arrow-invalid"
          : isCritical
            ? "gantt-dep-arrow-critical"
            : "gantt-dep-arrow";
        return (
          <path
            key={edge.id}
            d={d}
            fill="none"
            stroke={stroke}
            strokeWidth={isCritical ? DEP_WIDTH_CRITICAL : DEP_WIDTH}
            markerEnd={`url(#${marker})`}
            data-critical={isCritical || undefined}
          />
        );
      })}
    </svg>
  );
});
