export type TTimelineRelationType = "start_before" | "start_after" | "finish_before" | "finish_after";

export type TWorkItemTimelineDates = {
  start_date?: string | Date | null;
  target_date?: string | Date | null;
};

const toDate = (value: string | Date | null | undefined): Date | null => {
  if (value == null || value === "") return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : new Date(value.getFullYear(), value.getMonth(), value.getDate());
  }
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
};

const isOnOrBefore = (left: Date | null, right: Date | null): boolean => {
  if (!left || !right) return true;
  return left.getTime() <= right.getTime();
};

export const isStartBeforeSatisfied = (
  issueStart: string | Date | null | undefined,
  relatedStart: string | Date | null | undefined
): boolean => isOnOrBefore(toDate(issueStart), toDate(relatedStart));

export const isStartAfterSatisfied = (
  issueStart: string | Date | null | undefined,
  relatedStart: string | Date | null | undefined
): boolean => isStartBeforeSatisfied(relatedStart, issueStart);

export const isFinishBeforeSatisfied = (
  issueFinish: string | Date | null | undefined,
  relatedFinish: string | Date | null | undefined
): boolean => isOnOrBefore(toDate(issueFinish), toDate(relatedFinish));

export const isFinishAfterSatisfied = (
  issueFinish: string | Date | null | undefined,
  relatedFinish: string | Date | null | undefined
): boolean => isFinishBeforeSatisfied(relatedFinish, issueFinish);

export const isTimelineRelationSatisfied = (
  relationType: TTimelineRelationType,
  issueDates: TWorkItemTimelineDates,
  relatedDates: TWorkItemTimelineDates
): boolean => {
  switch (relationType) {
    case "start_before":
      return isStartBeforeSatisfied(issueDates.start_date, relatedDates.start_date);
    case "start_after":
      return isStartAfterSatisfied(issueDates.start_date, relatedDates.start_date);
    case "finish_before":
      return isFinishBeforeSatisfied(issueDates.target_date, relatedDates.target_date);
    case "finish_after":
      return isFinishAfterSatisfied(issueDates.target_date, relatedDates.target_date);
    default: {
      const _exhaustive: never = relationType;
      return _exhaustive;
    }
  }
};
