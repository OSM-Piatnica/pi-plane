export const MAX_PROJECT_CSV_SIZE_BYTES = 15 * 1024 * 1024;

export type TProjectCsvImportResult = {
  message: string;
  projects: {
    project_id: string;
    project_identifier: string;
    project_name: string;
    created_states: number;
    created_labels: number;
    created_work_items?: number;
    warnings: string[];
  }[];
  warnings: string[];
  history_id: string;
};

export function isValidProjectImportFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".csv");
}

export function isValidProjectImportSize(file: File, maxBytes = MAX_PROJECT_CSV_SIZE_BYTES): boolean {
  return file.size <= maxBytes;
}

export function downloadBlob(blob: Blob, filename: string): void {
  let typedBlob = blob;
  if (filename.toLowerCase().endsWith(".csv") && blob.type !== "text/csv") {
    typedBlob = new Blob([blob], { type: "text/csv;charset=utf-8" });
  }
  const url = window.URL.createObjectURL(typedBlob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.URL.revokeObjectURL(url);
}

export function getProjectImportLink(workspaceSlug: string, projectId: string): string {
  return `/${workspaceSlug}/projects/${projectId}/issues`;
}
