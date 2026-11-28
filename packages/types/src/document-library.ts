/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Where the bytes of a document live (docs/document-store.md). */
export type TDocumentProvider = "native" | "sharepoint";

/** A SharePoint document library of a workspace (docs/document-libraries.md). */
export type TDocumentLibrary = {
  id: string;
  name: string;
  provider: TDocumentProvider;
  site_id: string;
  drive_id: string;
  /** Folder inside the library, "/"-separated; "" is the root of the library */
  root_path: string;
  web_url: string;
  /** The SharePoint address of the root folder */
  folder_web_url: string;
  is_default: boolean;
  created_at: string;
  document_count?: number;
  /** Projects that chose this library */
  project_count?: number;
};

export type TDocumentLibraries = {
  /** SharePoint is switched on and configured in God Mode */
  sharepoint_enabled: boolean;
  /** Where new documents go when a project does not choose */
  default_provider: TDocumentProvider;
  native: { is_default: boolean };
  libraries: TDocumentLibrary[];
};

export type TDocumentSiteDrive = {
  id: string;
  name: string;
  web_url: string;
  drive_type: string;
  /** Root folders of this library that are already libraries of the workspace */
  used_root_paths: string[];
};

export type TDocumentSite = {
  site: { id: string; name: string; web_url: string };
  drives: TDocumentSiteDrive[];
};

export type TDocumentLibraryCreate = {
  site_url: string;
  drive_id: string;
  name?: string;
  root_path?: string;
  is_default?: boolean;
};

export type TDocumentLibraryUpdate = Partial<Pick<TDocumentLibrary, "name" | "root_path" | "is_default">>;

/** Where new documents of a project go: the workspace default, Pi-Plane storage, or a library of the workspace. */
export type TProjectDocumentStore = "workspace" | "native" | "sharepoint";

/** Why new documents go to Pi-Plane storage. */
export type TDocumentNativeReason = "" | "chosen" | "no_library" | "sharepoint_off";

export type TProjectDocumentSettings = {
  store: TProjectDocumentStore;
  library_id: string | null;
  /** The project's folder under the library's root folder; "" means the project identifier */
  folder: string;
  default_folder: string;
  sharepoint_enabled: boolean;
  workspace_default: { id: string; name: string } | null;
  libraries: Pick<TDocumentLibrary, "id" | "name" | "root_path" | "web_url" | "is_default">[];
  effective: {
    provider: TDocumentProvider;
    library: { id: string; name: string } | null;
    /** The project's folder from the root of the library */
    folder: string;
    folder_web_url: string;
    native_reason: TDocumentNativeReason;
  };
  can_edit: boolean;
};

export type TProjectDocumentSettingsUpdate = {
  store: TProjectDocumentStore;
  library_id?: string | null;
  folder?: string;
};

export type TProjectDocumentFolder = {
  exists: boolean;
  /** The folder's address, or the library's root folder while the folder does not exist yet */
  web_url: string;
  folder: string;
};
