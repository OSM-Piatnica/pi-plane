import type { TWorkItemFilterExpression } from "@plane/types";

export type IssueExportProviderOption = {
  provider: string;
  delimiter?: "," | ";";
};

export type IssueExportFormPayload = {
  provider: IssueExportProviderOption;
  project: string[];
  filters: TWorkItemFilterExpression;
};

export function buildIssueExportPayload(formData: IssueExportFormPayload) {
  return {
    provider: formData.provider.provider,
    project: formData.project,
    multiple: formData.project.length > 1,
    rich_filters: formData.filters,
    ...(formData.provider.provider === "csv" && formData.provider.delimiter
      ? { delimiter: formData.provider.delimiter }
      : {}),
  };
}

export type ProjectExportRequestOptions = {
  provider: string;
  delimiter?: "," | ";";
  includeWorkItems?: boolean;
};

export function buildProjectExportRequestBody(projectIds: string[], options: ProjectExportRequestOptions) {
  return {
    provider: options.provider,
    project: projectIds,
    include_work_items: Boolean(options.includeWorkItems),
    ...(options.provider === "csv" && options.delimiter ? { delimiter: options.delimiter } : {}),
  };
}
