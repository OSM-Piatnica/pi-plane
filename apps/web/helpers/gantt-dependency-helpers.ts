/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IGanttBlock, TIssueRelationTypes } from "@plane/types";
import type { TTimelineRelationType, TWorkItemTimelineDates } from "@plane/utils";
import { TIMELINE_RELATION_TYPES, isTimelineRelationSatisfied } from "@plane/utils";

export type TGanttDependencyEdge = {
  id: string;
  sourceId: string;
  targetId: string;
  relationType: TTimelineRelationType;
  isInvalid: boolean;
};

type TIssueDates = TWorkItemTimelineDates;

type TRelationMap = Record<string, Partial<Record<TIssueRelationTypes, string[]>> | undefined>;

/** Working days of lag of the relation `issueId <relationType> relatedId`; zero when none is known. */
export type TGetRelationLag = (issueId: string, relationType: TIssueRelationTypes, relatedId: string) => number;

const NO_LAG: TGetRelationLag = () => 0;

/** The weekend days of a work item's project, to count a relation's lag and 'must start after' in working days. */
export type TGetWeekendDays = (issueId: string) => readonly number[];

const NO_WEEKEND_DAYS: TGetWeekendDays = () => [];

export const isDependencyRelationInvalid = (
  relationType: TTimelineRelationType,
  sourceDates: TIssueDates,
  relatedDates: TIssueDates,
  lag = 0,
  sourceWeekendDays: readonly number[] = [],
  relatedWeekendDays: readonly number[] = []
): boolean =>
  !isTimelineRelationSatisfied(relationType, sourceDates, relatedDates, lag, sourceWeekendDays, relatedWeekendDays);

export const getDependencyArrowEndpoints = (
  relationType: TIssueRelationTypes,
  sourceId: string,
  relatedId: string
): { fromId: string; toId: string } => {
  switch (relationType) {
    case "blocked_by":
    case "finish_after":
    case "start_after":
    case "finish_after_start":
      return { fromId: relatedId, toId: sourceId };
    case "blocking":
    case "finish_before":
    case "start_before":
    case "start_before_finish":
    default:
      return { fromId: sourceId, toId: relatedId };
  }
};

export const buildGanttDependencyEdges = (
  blockIds: string[],
  relationMap: TRelationMap,
  getDates: (issueId: string) => TIssueDates | undefined,
  getLag: TGetRelationLag = NO_LAG,
  getWeekendDays: TGetWeekendDays = NO_WEEKEND_DAYS
): TGanttDependencyEdge[] => {
  const visible = new Set(blockIds);
  const edges: TGanttDependencyEdge[] = [];
  const seen = new Set<string>();

  for (const sourceId of blockIds) {
    const relations = relationMap[sourceId];
    if (!relations) continue;

    for (const relationType of TIMELINE_RELATION_TYPES) {
      const relatedIds = relations[relationType] ?? [];
      for (const relatedId of relatedIds) {
        if (!visible.has(relatedId)) continue;
        const { fromId, toId } = getDependencyArrowEndpoints(relationType, sourceId, relatedId);
        const edgeKey = `${fromId}->${toId}:${relationType}`;
        if (seen.has(edgeKey)) continue;
        seen.add(edgeKey);

        const sourceDates = getDates(sourceId);
        const relatedDates = getDates(relatedId);
        const isInvalid =
          !!sourceDates &&
          !!relatedDates &&
          isDependencyRelationInvalid(
            relationType,
            sourceDates,
            relatedDates,
            getLag(sourceId, relationType, relatedId),
            getWeekendDays(sourceId),
            getWeekendDays(relatedId)
          );

        edges.push({
          id: edgeKey,
          sourceId: fromId,
          targetId: toId,
          relationType,
          isInvalid,
        });
      }
    }
  }

  return edges;
};

export const wouldUpdatesViolateDependencies = (
  updates: { id: string; start_date?: string; target_date?: string }[],
  relationMap: TRelationMap,
  getDates: (issueId: string) => TIssueDates | undefined,
  getLag: TGetRelationLag = NO_LAG,
  getWeekendDays: TGetWeekendDays = NO_WEEKEND_DAYS
): boolean => {
  const proposed = new Map<string, TIssueDates>();
  for (const update of updates) {
    const current = getDates(update.id) ?? {};
    proposed.set(update.id, {
      start_date: update.start_date ?? current.start_date,
      target_date: update.target_date ?? current.target_date,
    });
  }

  const getMergedDates = (issueId: string) => proposed.get(issueId) ?? getDates(issueId);

  for (const update of updates) {
    const relations = relationMap[update.id];
    if (!relations) continue;
    const sourceDates = getMergedDates(update.id);
    if (!sourceDates) continue;

    for (const relationType of TIMELINE_RELATION_TYPES) {
      for (const relatedId of relations[relationType] ?? []) {
        const relatedDates = getMergedDates(relatedId);
        if (!relatedDates) continue;
        if (
          isDependencyRelationInvalid(
            relationType,
            sourceDates,
            relatedDates,
            getLag(update.id, relationType, relatedId),
            getWeekendDays(update.id),
            getWeekendDays(relatedId)
          )
        ) {
          return true;
        }
      }
    }

    for (const [otherId, otherRelations] of Object.entries(relationMap)) {
      if (!otherRelations || otherId === update.id) continue;
      for (const relationType of TIMELINE_RELATION_TYPES) {
        // react-doctor-disable-next-line js-set-map-lookups -- each array is searched once per iteration, so a Set would cost more than the scan
        if (!(otherRelations[relationType] ?? []).includes(update.id)) continue;
        const otherDates = getMergedDates(otherId);
        const thisDates = getMergedDates(update.id);
        if (!otherDates || !thisDates) continue;
        if (
          isDependencyRelationInvalid(
            relationType,
            otherDates,
            thisDates,
            getLag(otherId, relationType, update.id),
            getWeekendDays(otherId),
            getWeekendDays(update.id)
          )
        ) {
          return true;
        }
      }
    }
  }

  return false;
};

export const getBlockAnchorPoints = (
  block: IGanttBlock,
  blockIndex: number,
  blockHeight: number
): { left: { x: number; y: number }; right: { x: number; y: number } } | null => {
  if (!block.position) return null;
  const y = blockIndex * blockHeight + blockHeight / 2;
  return {
    left: { x: block.position.marginLeft, y },
    right: { x: block.position.marginLeft + block.position.width, y },
  };
};

export type TAnchorSide = "left" | "right";

/**
 * The edges of the two bars an arrow joins, as in a project plan: finish-to-start runs from the end of one bar to
 * the start of the next, start-to-start from start to start, finish-to-finish from end to end, and start-to-finish
 * from the start of the first bar to the end of the second. The same for both names of a relation.
 */
export const getDependencyAnchorSides = (relationType: TIssueRelationTypes): { from: TAnchorSide; to: TAnchorSide } => {
  switch (relationType) {
    case "start_before":
    case "start_after":
      return { from: "left", to: "left" };
    case "finish_before":
    case "finish_after":
      return { from: "right", to: "right" };
    case "start_before_finish":
    case "finish_after_start":
      return { from: "left", to: "right" };
    default:
      return { from: "right", to: "left" };
  }
};

export const buildDependencyPathD = (
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  fromSide: TAnchorSide = "right",
  toSide: TAnchorSide = "left"
): string => {
  const deltaX = Math.max(Math.abs(toX - fromX) * 0.4, 24);
  // the curve leaves a bar away from it, and arrives from the outside of the other
  const c1x = fromSide === "right" ? fromX + deltaX : fromX - deltaX;
  const c2x = toSide === "left" ? toX - deltaX : toX + deltaX;
  return `M ${fromX} ${fromY} C ${c1x} ${fromY}, ${c2x} ${toY}, ${toX} ${toY}`;
};
