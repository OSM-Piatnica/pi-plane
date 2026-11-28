/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TProjectDocumentSettings, TProjectDocumentStore } from "@plane/types";

/** The SWR key of the document libraries of a workspace (workspace settings). */
export const getDocumentLibrariesKey = (workspaceSlug: string) => `WORKSPACE_DOCUMENT_LIBRARIES_${workspaceSlug}`;
/** The SWR key of where new documents of a project go (project settings). */
export const getProjectDocumentSettingsKey = (workspaceSlug: string, projectId: string) =>
  `PROJECT_DOCUMENT_SETTINGS_${workspaceSlug}_${projectId}`;

export const DOCUMENT_LIBRARY_NAME_MAX_LENGTH = 255;
const FOLDER_MAX_LENGTH = 400;
const FOLDER_MAX_SEGMENTS = 20;
// What SharePoint does not take in a name; the server checks the same (plane.utils.document_store.libraries)
const FORBIDDEN_CHARACTERS = /["*:<>?|#%]/;
const RESERVED_NAMES = new Set([
  ".lock",
  "con",
  "prn",
  "aux",
  "nul",
  "desktop.ini",
  ...Array.from({ length: 10 }, (_, n) => `com${n}`),
  ...Array.from({ length: 10 }, (_, n) => `lpt${n}`),
]);

const hasControlCharacter = (text: string) =>
  Array.from(text).some((char) => {
    const code = char.charCodeAt(0);
    return code < 32 || code === 127;
  });

const isFolderNameAllowed = (segment: string) => {
  const lower = segment.toLowerCase();
  const stem = lower.includes(".") ? lower.slice(0, lower.lastIndexOf(".")) : lower;
  return !(
    segment === "." ||
    segment === ".." ||
    FORBIDDEN_CHARACTERS.test(segment) ||
    hasControlCharacter(segment) ||
    segment.endsWith(".") ||
    lower.startsWith("~$") ||
    lower.startsWith("_vti_") ||
    RESERVED_NAMES.has(lower) ||
    RESERVED_NAMES.has(stem)
  );
};

/**
 * A folder path as the server keeps it ("A/B/C": no leading, trailing or doubled "/", each part trimmed), or null
 * when SharePoint would not take it. The server checks again; this only lets the form say so before saving.
 */
export function normalizeFolderPath(value: string | null | undefined): string | null {
  const segments = (value ?? "")
    .replace(/\\/g, "/")
    .split("/")
    .map((segment) => segment.trim())
    .filter(Boolean);
  if (segments.length > FOLDER_MAX_SEGMENTS) return null;
  if (!segments.every(isFolderNameAllowed)) return null;
  const path = segments.join("/");
  return path.length > FOLDER_MAX_LENGTH ? null : path;
}

/** The folder of a project from the root of the library: the library's root folder, then the project's folder. */
export function getProjectFolderPreview(rootPath: string, folder: string, projectIdentifier: string): string {
  return [rootPath, folder || projectIdentifier].filter(Boolean).join("/");
}

export type TProjectDocumentForm = { store: TProjectDocumentStore; libraryId: string; folder: string };

/**
 * What the project's Documents form can do with its current values: the folder as it would be saved (null when
 * SharePoint would not take it), whether anything changed against the saved settings, whether it can be saved, and
 * the root folder of the library the documents would go to (for the preview).
 */
export function getProjectDocumentFormState(settings: TProjectDocumentSettings, form: TProjectDocumentForm) {
  const folder = normalizeFolderPath(form.folder);
  const isChanged =
    form.store !== settings.store ||
    (form.store === "sharepoint" && form.libraryId !== (settings.library_id ?? "")) ||
    (form.store !== "native" && folder !== settings.folder);
  const canSave =
    settings.can_edit && isChanged && folder !== null && (form.store !== "sharepoint" || form.libraryId !== "");
  const libraryId = form.store === "sharepoint" ? form.libraryId : settings.workspace_default?.id;
  const rootPath = settings.libraries.find((library) => library.id === libraryId)?.root_path ?? "";
  return { folder, isChanged, canSave, rootPath };
}

/** Whether a pasted address looks like a SharePoint Online site; the server decides. */
export function isSharePointSiteUrl(value: string): boolean {
  try {
    const url = new URL(value.trim());
    return url.protocol === "https:" && /^[a-z0-9-]+\.sharepoint\.com$/i.test(url.hostname);
  } catch {
    return false;
  }
}

// Answers of the server the interface says in the person's language; others show the server's own message
const ERROR_KEYS: Record<string, string> = {
  not_configured: "workspace_settings.settings.document_libraries.errors.not_configured",
  disabled: "workspace_settings.settings.document_libraries.errors.not_configured",
  invalid_site_url: "workspace_settings.settings.document_libraries.errors.invalid_site_url",
  site_access_denied: "workspace_settings.settings.document_libraries.errors.site_access_denied",
  site_not_found: "workspace_settings.settings.document_libraries.errors.site_not_found",
  library_not_found: "workspace_settings.settings.document_libraries.errors.library_not_found",
  library_exists: "workspace_settings.settings.document_libraries.errors.library_exists",
  invalid_folder: "workspace_settings.settings.document_libraries.errors.invalid_folder",
  throttled: "workspace_settings.settings.document_libraries.errors.throttled",
  timeout: "workspace_settings.settings.document_libraries.errors.timeout",
  transport_error: "workspace_settings.settings.document_libraries.errors.timeout",
};

export type TDocumentLibraryError = { error?: string; error_code?: string } | undefined | null;

/** What to tell the person about a failed request: an i18n key when the code is known, else the server's text. */
export function getDocumentLibraryErrorMessage(error: unknown, t: (key: string) => string, fallback: string): string {
  const data = error as TDocumentLibraryError;
  const key = data?.error_code ? ERROR_KEYS[data.error_code] : undefined;
  if (key) return t(key);
  return data?.error || fallback;
}
