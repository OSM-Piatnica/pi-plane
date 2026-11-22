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
  TScheduleCriticalLink,
} from "@plane/types";
import { EIssuesStoreType } from "@plane/types";
import { TIMELINE_RELATION_TYPES } from "@plane/utils";
import type { TTimelineRelationType } from "@plane/utils";

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

/**
 * The analysed work item, when there is an analysis and it covers it. A truncated analysis describes a cut-off part of
 * the plan, so it covers nothing.
 */
export const getScheduleAnalysisItem = (
  analysis: TScheduleAnalysis | undefined,
  issueId: string | undefined
): TScheduleAnalysisItem | undefined =>
  analysis && !analysis.truncated && issueId ? analysis.items[issueId] : undefined;

export const isWorkItemCritical = (analysis: TScheduleAnalysis | undefined, issueId: string | undefined): boolean =>
  !!getScheduleAnalysisItem(analysis, issueId)?.is_critical;

// a relation type as stored on either work item, as the rule seen from the predecessor (the server's `relation_type`)
const PREDECESSOR_RULE: Record<TTimelineRelationType, TScheduleCriticalLink["relation_type"]> = {
  blocked_by: "blocking",
  blocking: "blocking",
  start_before: "start_before",
  start_after: "start_before",
  finish_before: "finish_before",
  finish_after: "finish_before",
  start_before_finish: "start_before_finish",
  finish_after_start: "start_before_finish",
};

const linkKey = (source: string, target: string, rule: string) => `${source}>${target}:${rule}`;

// one lookup per answer: every dependency line asks, on every render of the timeline
const criticalLinkKeysCache = new WeakMap<TScheduleAnalysis, Set<string>>();
const getCriticalLinkKeys = (analysis: TScheduleAnalysis): Set<string> => {
  let keys = criticalLinkKeysCache.get(analysis);
  if (!keys) {
    keys = new Set(
      (analysis.critical_links ?? []).map((link) => linkKey(link.source, link.target, link.relation_type))
    );
    criticalLinkKeysCache.set(analysis, keys);
  }
  return keys;
};

/**
 * A dependency line is on the critical path when the server lists it as critical: it drives its successor. A line
 * between two critical work items that leaves the successor room is not. `sourceId` is the predecessor.
 */
export const isDependencyCritical = (
  analysis: TScheduleAnalysis | undefined,
  edge: { sourceId: string; targetId: string; relationType: TTimelineRelationType }
): boolean =>
  !!analysis &&
  !analysis.truncated &&
  getCriticalLinkKeys(analysis).has(linkKey(edge.sourceId, edge.targetId, PREDECESSOR_RULE[edge.relationType]));

export type TScheduleAnalysisNotice = "truncated" | "cycles" | "inverted";

/** What a person should know about the limits of an analysis, next to the toggle. */
export const getScheduleAnalysisNotices = (analysis: TScheduleAnalysis | undefined): TScheduleAnalysisNotice[] => {
  if (!analysis) return [];
  const notices: TScheduleAnalysisNotice[] = [];
  if (analysis.truncated) notices.push("truncated");
  if (analysis.cycles.length > 0) notices.push("cycles");
  if ((analysis.inverted_count ?? 0) > 0) notices.push("inverted");
  return notices;
};

/**
 * The ids of the work items in a layout, whether it is a plain list of ids, grouped by one property (list, kanban) or
 * by two (kanban with sub-groups). A work item in several groups, such as one with two labels, counts once.
 */
export const flattenIssueIds = (grouped: unknown): string[] => {
  const ids = new Set<string>();
  const collect = (value: unknown) => {
    if (Array.isArray(value)) {
      for (const entry of value) if (typeof entry === "string") ids.add(entry);
    } else if (value && typeof value === "object") {
      Object.values(value).forEach(collect);
    }
  };
  collect(grouped);
  return [...ids];
};
