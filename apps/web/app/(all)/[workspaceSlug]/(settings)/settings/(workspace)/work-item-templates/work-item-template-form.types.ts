import type { TIssue } from "@plane/types";

export type TWorkItemTemplateFormFields = {
  templateName: string;
  templateNote: string;
  projectId: string | null;
  workItemName: string;
  workItemDescriptionPlain: string;
} & Pick<
  TIssue,
  | "type_id"
  | "state_id"
  | "priority"
  | "assignee_ids"
  | "label_ids"
  | "cycle_id"
  | "module_ids"
  | "estimate_point"
  | "start_date"
  | "target_date"
>;
