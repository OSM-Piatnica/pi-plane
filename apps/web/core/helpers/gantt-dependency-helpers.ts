import type { IGanttBlock, TIssueRelationTypes } from "@plane/types";

const GANTT_DEPENDENCY_RELATION_TYPES: TIssueRelationTypes[] = [
  "blocked_by",
  "blocking",
  "start_before",
  "start_after",
  "finish_before",
  "finish_after",
];

export type TGanttDependencyEdge = {
  id: string;
  sourceId: string;
  targetId: string;
  relationType: TIssueRelationTypes;
  isInvalid: boolean;
};

type TIssueDates = {
  start_date?: string | null;
  target_date?: string | null;
};

type TRelationMap = Record<string, Partial<Record<TIssueRelationTypes, string[]>> | undefined>;

const parseDateKey = (value?: string | null): string | null => {
  if (!value) return null;
  const isoDay = /^(\d{4}-\d{2}-\d{2})/.exec(value);
  if (isoDay) return isoDay[1];
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const isStrictlyBefore = (left: string, right: string) => left < right;

export const isDependencyRelationInvalid = (
  relationType: TIssueRelationTypes,
  sourceDates: TIssueDates,
  relatedDates: TIssueDates
): boolean => {
  const sourceStart = parseDateKey(sourceDates.start_date);
  const sourceTarget = parseDateKey(sourceDates.target_date);
  const relatedStart = parseDateKey(relatedDates.start_date);
  const relatedTarget = parseDateKey(relatedDates.target_date);

  switch (relationType) {
    case "blocked_by":
      if (!relatedTarget || !sourceStart) return false;
      return !isStrictlyBefore(relatedTarget, sourceStart);
    case "blocking":
      if (!sourceTarget || !relatedStart) return false;
      return !isStrictlyBefore(sourceTarget, relatedStart);
    case "finish_before":
      if (!sourceTarget || !relatedStart) return false;
      return !isStrictlyBefore(sourceTarget, relatedStart);
    case "finish_after":
      if (!relatedTarget || !sourceStart) return false;
      return !isStrictlyBefore(relatedTarget, sourceStart);
    case "start_before":
      if (!sourceStart || !relatedStart) return false;
      return !isStrictlyBefore(sourceStart, relatedStart);
    case "start_after":
      if (!relatedStart || !sourceStart) return false;
      return !isStrictlyBefore(relatedStart, sourceStart);
    default:
      return false;
  }
};

export const getDependencyArrowEndpoints = (
  relationType: TIssueRelationTypes,
  sourceId: string,
  relatedId: string
): { fromId: string; toId: string } => {
  switch (relationType) {
    case "blocked_by":
    case "finish_after":
    case "start_after":
      return { fromId: relatedId, toId: sourceId };
    case "blocking":
    case "finish_before":
    case "start_before":
    default:
      return { fromId: sourceId, toId: relatedId };
  }
};

export const buildGanttDependencyEdges = (
  blockIds: string[],
  relationMap: TRelationMap,
  getDates: (issueId: string) => TIssueDates | undefined
): TGanttDependencyEdge[] => {
  const visible = new Set(blockIds);
  const edges: TGanttDependencyEdge[] = [];
  const seen = new Set<string>();

  for (const sourceId of blockIds) {
    const relations = relationMap[sourceId];
    if (!relations) continue;

    for (const relationType of GANTT_DEPENDENCY_RELATION_TYPES) {
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
          !!sourceDates && !!relatedDates && isDependencyRelationInvalid(relationType, sourceDates, relatedDates);

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
  getDates: (issueId: string) => TIssueDates | undefined
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

    for (const relationType of GANTT_DEPENDENCY_RELATION_TYPES) {
      for (const relatedId of relations[relationType] ?? []) {
        const relatedDates = getMergedDates(relatedId);
        if (!relatedDates) continue;
        if (isDependencyRelationInvalid(relationType, sourceDates, relatedDates)) {
          return true;
        }
      }
    }

    for (const [otherId, otherRelations] of Object.entries(relationMap)) {
      if (!otherRelations || otherId === update.id) continue;
      for (const relationType of GANTT_DEPENDENCY_RELATION_TYPES) {
        if (!(otherRelations[relationType] ?? []).includes(update.id)) continue;
        const otherDates = getMergedDates(otherId);
        const thisDates = getMergedDates(update.id);
        if (!otherDates || !thisDates) continue;
        if (isDependencyRelationInvalid(relationType, otherDates, thisDates)) {
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

export const buildDependencyPathD = (fromX: number, fromY: number, toX: number, toY: number): string => {
  const deltaX = Math.max(Math.abs(toX - fromX) * 0.4, 24);
  const c1x = fromX + deltaX;
  const c2x = toX - deltaX;
  return `M ${fromX} ${fromY} C ${c1x} ${fromY}, ${c2x} ${toY}, ${toX} ${toY}`;
};
