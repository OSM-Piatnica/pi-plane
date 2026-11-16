/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type {
  TIssueRelationTypes,
  TScheduleAnalysis,
  TScheduleAnalysisItem,
  TScheduleAnalysisScope,
} from "@plane/types";
import { EIssuesStoreType } from "@plane/types";
import { TIMELINE_RELATION_TYPES } from "@plane/utils";

/**
 * The critical path of the timeline is computed by the server (`plane.utils.schedule_analysis`); the web app only
 * decides when to ask again and what to highlight. These helpers hold that logic.
 */

type TScheduledWorkItem = {
  start_date?: string | null;
  finish_date?: string | null;
  target_date?: string | null;
  state_id?: string | null;
};

type TRelationMap = Record<string, Partial<Record<TIssueRelationTypes, string[]>> | undefined>;

/** The module or cycle a timeline is limited to; a project, view or epic timeline analyses the whole project. */
export const getScheduleAnalysisScope = (
  storeType: EIssuesStoreType,
  ids: { moduleId?: string; cycleId?: string }
): TScheduleAnalysisScope => {
  if (storeType === EIssuesStoreType.MODULE && ids.moduleId) return { module: ids.moduleId };
  if (storeType === EIssuesStoreType.CYCLE && ids.cycleId) return { cycle: ids.cycleId };
  return {};
};

/**
 * A string that changes whenever something the analysis depends on changes among the loaded work items: a start,
 * finish or due date, a state (completed and cancelled work items are fixed), a timeline relation or its lag.
 */
export const getScheduleAnalysisKey = (
  issueIds: string[],
  getIssue: (issueId: string) => TScheduledWorkItem | undefined,
  relationMap: TRelationMap,
  getLag: (issueId: string, relationType: TIssueRelationTypes, relatedId: string) => number
): string =>
  issueIds
    .map((issueId) => {
      const issue = getIssue(issueId);
      const relations = relationMap[issueId];
      const relationKey = relations
        ? TIMELINE_RELATION_TYPES.flatMap((relationType) =>
            (relations[relationType] ?? [])
              .toSorted()
              .map((relatedId) => `${relationType}>${relatedId}+${getLag(issueId, relationType, relatedId)}`)
          ).join(",")
        : "";
      return [
        issueId,
        issue?.start_date ?? "",
        issue?.finish_date ?? "",
        issue?.target_date ?? "",
        issue?.state_id ?? "",
        relationKey,
      ].join("|");
    })
    .join(";");

/** The analysed work item, when there is an analysis and it covers it. */
export const getScheduleAnalysisItem = (
  analysis: TScheduleAnalysis | undefined,
  issueId: string | undefined
): TScheduleAnalysisItem | undefined => (analysis && issueId ? analysis.items[issueId] : undefined);

export const isWorkItemCritical = (analysis: TScheduleAnalysis | undefined, issueId: string | undefined): boolean =>
  !!getScheduleAnalysisItem(analysis, issueId)?.is_critical;

/** A dependency line is on the critical path when the work items at both of its ends are. */
export const isDependencyCritical = (
  analysis: TScheduleAnalysis | undefined,
  edge: { sourceId: string; targetId: string }
): boolean => isWorkItemCritical(analysis, edge.sourceId) && isWorkItemCritical(analysis, edge.targetId);

export type TScheduleAnalysisNotice = "truncated" | "cycles";

/** What a person should know about the limits of an analysis, next to the toggle. */
export const getScheduleAnalysisNotices = (analysis: TScheduleAnalysis | undefined): TScheduleAnalysisNotice[] => {
  if (!analysis) return [];
  const notices: TScheduleAnalysisNotice[] = [];
  if (analysis.truncated) notices.push("truncated");
  if (analysis.cycles.length > 0) notices.push("cycles");
  return notices;
};
