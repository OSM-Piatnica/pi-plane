/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import type { TProjectDocumentSettings } from "@plane/types";
import {
  getDocumentLibraryErrorMessage,
  getProjectDocumentFormState,
  getProjectFolderPreview,
  isSharePointSiteUrl,
  normalizeFolderPath,
} from "@/helpers/document-library";

describe("normalizeFolderPath", () => {
  it("tidies slashes and spaces as the server does", () => {
    expect(normalizeFolderPath("")).toBe("");
    expect(normalizeFolderPath(undefined)).toBe("");
    expect(normalizeFolderPath(" /Pi-Plane//Docs/ ")).toBe("Pi-Plane/Docs");
    expect(normalizeFolderPath("Pi-Plane\\Docs")).toBe("Pi-Plane/Docs");
    expect(normalizeFolderPath(" Klienci / Opakowania 2027 ")).toBe("Klienci/Opakowania 2027");
    expect(normalizeFolderPath("Zażółć/gęślą")).toBe("Zażółć/gęślą");
  });

  it("refuses names SharePoint does not take", () => {
    for (const value of [
      "a/../b",
      "a/./b",
      "Docs:2027",
      "Q?",
      "a*b",
      "50%",
      "#1",
      "ends.",
      "~$lock",
      "con",
      "aux.txt",
    ]) {
      expect(normalizeFolderPath(value)).toBeNull();
    }
  });

  it("refuses too deep and too long paths", () => {
    expect(normalizeFolderPath(Array.from({ length: 21 }, () => "a").join("/"))).toBeNull();
    expect(normalizeFolderPath(Array.from({ length: 5 }, () => "x".repeat(100)).join("/"))).toBeNull();
    expect(normalizeFolderPath(Array.from({ length: 20 }, () => "a").join("/"))).not.toBeNull();
  });
});

describe("getProjectFolderPreview", () => {
  it("puts the project folder under the root folder", () => {
    expect(getProjectFolderPreview("Pi-Plane", "", "PACK")).toBe("Pi-Plane/PACK");
    expect(getProjectFolderPreview("", "", "PACK")).toBe("PACK");
    expect(getProjectFolderPreview("Pi-Plane", "Klienci/ACME", "PACK")).toBe("Pi-Plane/Klienci/ACME");
  });
});

describe("isSharePointSiteUrl", () => {
  it("accepts SharePoint Online sites only", () => {
    expect(isSharePointSiteUrl("https://contoso.sharepoint.com/sites/Projects")).toBe(true);
    expect(isSharePointSiteUrl(" https://contoso.sharepoint.com ")).toBe(true);
    expect(isSharePointSiteUrl("http://contoso.sharepoint.com/sites/Projects")).toBe(false);
    expect(isSharePointSiteUrl("https://example.com/sites/Projects")).toBe(false);
    expect(isSharePointSiteUrl("contoso.sharepoint.com")).toBe(false);
  });
});

const t = (key: string) => `t:${key}`;

describe("getDocumentLibraryErrorMessage", () => {
  it("translates known codes", () => {
    expect(getDocumentLibraryErrorMessage({ error: "x", error_code: "not_configured" }, t, "fallback")).toBe(
      "t:workspace_settings.settings.document_libraries.errors.not_configured"
    );
    expect(getDocumentLibraryErrorMessage({ error_code: "disabled" }, t, "fallback")).toBe(
      "t:workspace_settings.settings.document_libraries.errors.not_configured"
    );
  });

  it("falls back to the server's text, then the given text", () => {
    expect(getDocumentLibraryErrorMessage({ error: "Microsoft said no", error_code: "x" }, t, "fallback")).toBe(
      "Microsoft said no"
    );
    expect(getDocumentLibraryErrorMessage(undefined, t, "fallback")).toBe("fallback");
  });
});

describe("getProjectDocumentFormState", () => {
  const settings: TProjectDocumentSettings = {
    store: "workspace",
    library_id: null,
    folder: "",
    default_folder: "PACK",
    sharepoint_enabled: true,
    workspace_default: { id: "lib-1", name: "Documents" },
    libraries: [
      { id: "lib-1", name: "Documents", root_path: "Pi-Plane", web_url: "", is_default: true },
      { id: "lib-2", name: "Artwork", root_path: "", web_url: "", is_default: false },
    ],
    effective: { provider: "sharepoint", library: null, folder: "", folder_web_url: "", native_reason: "" },
    can_edit: true,
  };

  it("has nothing to save until something changes", () => {
    const state = getProjectDocumentFormState(settings, { store: "workspace", libraryId: "lib-1", folder: " / " });
    expect(state).toEqual({ folder: "", isChanged: false, canSave: false, rootPath: "Pi-Plane" });
  });

  it("previews the chosen library's root folder and saves a valid folder", () => {
    const state = getProjectDocumentFormState(settings, {
      store: "sharepoint",
      libraryId: "lib-2",
      folder: "Klienci/",
    });
    expect(state).toEqual({ folder: "Klienci", isChanged: true, canSave: true, rootPath: "" });
  });

  it("does not save an invalid folder, a missing library or without the right to edit", () => {
    expect(getProjectDocumentFormState(settings, { store: "workspace", libraryId: "", folder: "a:b" }).canSave).toBe(
      false
    );
    expect(getProjectDocumentFormState(settings, { store: "sharepoint", libraryId: "", folder: "" }).canSave).toBe(
      false
    );
    expect(
      getProjectDocumentFormState({ ...settings, can_edit: false }, { store: "native", libraryId: "", folder: "" })
        .canSave
    ).toBe(false);
  });
});
