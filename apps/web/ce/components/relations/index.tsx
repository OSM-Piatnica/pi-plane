import { CircleDot, XCircle } from "lucide-react";
import { CalendarAfterIcon, CalendarBeforeIcon, RelatedIcon, DuplicatePropertyIcon } from "@plane/propel/icons";
import type { TRelationObject } from "@/components/issues/issue-detail-widgets/relations";
import type { TIssueRelationTypes } from "../../types";

export * from "./activity";

export const ISSUE_RELATION_OPTIONS: Record<TIssueRelationTypes, TRelationObject> = {
  relates_to: {
    key: "relates_to",
    i18n_label: "issue.relation.relates_to",
    className: "bg-layer-1 text-secondary",
    icon: (size) => <RelatedIcon height={size} width={size} className="text-secondary" />,
    placeholder: "Add related work items",
  },
  duplicate: {
    key: "duplicate",
    i18n_label: "issue.relation.duplicate",
    className: "bg-layer-1 text-secondary",
    icon: (size) => <DuplicatePropertyIcon width={size} height={size} className="text-secondary" />,
    placeholder: "None",
  },
  blocked_by: {
    key: "blocked_by",
    i18n_label: "issue.relation.blocked_by",
    className: "bg-danger-subtle text-danger-primary",
    icon: (size) => <CircleDot size={size} className="text-secondary" />,
    placeholder: "None",
  },
  blocking: {
    key: "blocking",
    i18n_label: "issue.relation.blocking",
    className: "bg-yellow-500/20 text-yellow-700",
    icon: (size) => <XCircle size={size} className="text-secondary" />,
    placeholder: "None",
  },
  start_before: {
    key: "start_before",
    i18n_label: "issue.relation.start_before",
    className: "bg-accent-primary/10 text-accent-primary",
    icon: (size) => <CalendarBeforeIcon width={size} height={size} className="text-secondary" />,
    placeholder: "None",
  },
  start_after: {
    key: "start_after",
    i18n_label: "issue.relation.start_after",
    className: "bg-accent-primary/10 text-accent-primary",
    icon: (size) => <CalendarAfterIcon width={size} height={size} className="text-secondary" />,
    placeholder: "None",
  },
  finish_before: {
    key: "finish_before",
    i18n_label: "issue.relation.finish_before",
    className: "bg-accent-primary/10 text-accent-primary",
    icon: (size) => <CalendarBeforeIcon width={size} height={size} className="text-secondary" />,
    placeholder: "None",
  },
  finish_after: {
    key: "finish_after",
    i18n_label: "issue.relation.finish_after",
    className: "bg-accent-primary/10 text-accent-primary",
    icon: (size) => <CalendarAfterIcon width={size} height={size} className="text-secondary" />,
    placeholder: "None",
  },
};

export const useTimeLineRelationOptions = () => ISSUE_RELATION_OPTIONS;
