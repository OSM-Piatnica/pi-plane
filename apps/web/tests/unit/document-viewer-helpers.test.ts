/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import {
  clampPage,
  clampZoom,
  getFetchCredentials,
  getFitScale,
  getPreviewKind,
  getRenderResolution,
  isPreviewable,
  MAX_ZOOM,
  MIN_ZOOM,
  stepZoom,
  toPercent,
} from "@/components/document-viewer/helpers";
import {
  attachmentToDocumentSource,
  isAttachmentPreviewable,
} from "@/components/issues/attachment/attachment-document-source";
import type { TIssueAttachment } from "@plane/types";

describe("getPreviewKind", () => {
  it("previews PDFs and the raster formats of the prototype", () => {
    expect(getPreviewKind("application/pdf", "art.pdf")).toBe("pdf");
    expect(getPreviewKind("image/jpeg", "a.jpg")).toBe("image");
    expect(getPreviewKind("image/png", "a.png")).toBe("image");
    expect(getPreviewKind("image/webp", "a.webp")).toBe("image");
  });

  it("shows SVG as an image (rendered through <img> only)", () => {
    expect(getPreviewKind("image/svg+xml", "logo.svg")).toBe("image");
  });

  it("does not preview other specific types, whatever the extension says", () => {
    expect(getPreviewKind("image/tiff", "scan.tif")).toBe("unsupported");
    expect(getPreviewKind("application/postscript", "art.ai")).toBe("unsupported");
    expect(getPreviewKind("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "x.pdf")).toBe(
      "unsupported"
    );
  });

  it("falls back to the extension when the type is missing or generic", () => {
    expect(getPreviewKind(undefined, "Brief.PDF")).toBe("pdf");
    expect(getPreviewKind("", "photo.JPEG")).toBe("image");
    expect(getPreviewKind("application/octet-stream", "photo.webp")).toBe("image");
    expect(getPreviewKind("application/octet-stream", "design.psd")).toBe("unsupported");
    expect(getPreviewKind(undefined, "README")).toBe("unsupported");
  });

  it("ignores mime type parameters and case", () => {
    expect(getPreviewKind("Application/PDF; charset=binary", "x")).toBe("pdf");
  });

  it("isPreviewable mirrors getPreviewKind", () => {
    expect(isPreviewable("application/pdf", "a.pdf")).toBe(true);
    expect(isPreviewable("text/plain", "a.txt")).toBe(false);
  });
});

describe("zoom", () => {
  it("fits the page into the area minus a 20 px margin per side", () => {
    expect(getFitScale({ width: 440, height: 1040 }, { width: 400, height: 500 })).toBe(1);
    expect(getFitScale({ width: 1040, height: 540 }, { width: 1000, height: 1000 })).toBe(0.5);
  });

  it("keeps a minimum fit scale for tiny areas and survives empty sizes", () => {
    expect(getFitScale({ width: 0, height: 0 }, { width: 1000, height: 1000 })).toBe(0.02);
    expect(getFitScale({ width: 500, height: 500 }, { width: 0, height: 0 })).toBe(1);
  });

  it("steps by 25 % within 25 % and 400 %", () => {
    expect(stepZoom(1, 1)).toBe(1.25);
    expect(stepZoom(1, -1)).toBe(0.75);
    expect(stepZoom(0.3, -1)).toBe(MIN_ZOOM);
    expect(stepZoom(3.9, 1)).toBe(MAX_ZOOM);
    expect(clampZoom(10)).toBe(MAX_ZOOM);
    expect(toPercent(0.856)).toBe(86);
  });

  it("caps the canvas resolution at 8192 px per side and 16 megapixels", () => {
    const a4 = { width: 595, height: 842 };
    expect(getRenderResolution(1, 2, a4)).toBe(2);
    // 4x zoom on a 3x display would be 7140 x 10104 px: capped by the 8192 px side first.
    expect(getRenderResolution(4, 3, a4)).toBeCloseTo(Math.min(8192 / 842, Math.sqrt(16_000_000 / (595 * 842))));
    expect(getRenderResolution(1, 0, a4)).toBe(1);
  });
});

describe("clampPage", () => {
  it("keeps the page within the document", () => {
    expect(clampPage(0, 5)).toBe(1);
    expect(clampPage(6, 5)).toBe(5);
    expect(clampPage(3, 5)).toBe(3);
    expect(clampPage(Number.NaN, 5)).toBe(1);
    expect(clampPage(2, 0)).toBe(1);
  });
});

describe("getFetchCredentials", () => {
  it("sends cookies only to the page's own origin when the API shares it", () => {
    expect(getFetchCredentials("/api/assets/x", "https://plane.example")).toBe("same-origin");
    expect(getFetchCredentials("https://plane.example/api/x", "https://plane.example")).toBe("same-origin");
  });

  it("includes credentials for a separate API origin", () => {
    expect(getFetchCredentials("http://localhost:8000/api/x", "http://localhost:3000")).toBe("include");
  });
});

const attachment = (name: string, type?: string): TIssueAttachment => ({
  id: "a1",
  attributes: { name, size: 10, type },
  asset_url: "https://plane.example/api/assets/v2/workspaces/w/projects/p/issues/i/attachments/a1/",
  issue_id: "i",
  updated_at: "2026-11-28T00:00:00Z",
  updated_by: "u",
  created_by: "u",
});

describe("attachment sources", () => {
  it("uses the attachment endpoint as the viewer URL and the declared mime type", () => {
    expect(attachmentToDocumentSource(attachment("art.pdf", "application/pdf"))).toEqual({
      id: "a1",
      name: "art.pdf",
      mimeType: "application/pdf",
      url: "https://plane.example/api/assets/v2/workspaces/w/projects/p/issues/i/attachments/a1/",
    });
  });

  it("previews PDFs and images only", () => {
    expect(isAttachmentPreviewable(attachment("art.pdf", "application/pdf"))).toBe(true);
    expect(isAttachmentPreviewable(attachment("photo.png"))).toBe(true);
    expect(isAttachmentPreviewable(attachment("sheet.xlsx", "application/vnd.ms-excel"))).toBe(false);
  });
});
