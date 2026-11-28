/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";

/**
 * Where the viewer gets a file from. The viewer does not know whether the bytes come from a work
 * item attachment, the document store (B3) or anywhere else: it takes either a URL or a function
 * that fetches the file, plus the file's mime type and name.
 *
 * - `url`: images are shown straight from it with `<img>`; PDFs are fetched from it.
 * - `fetchFile`: called once per open viewer; the result is never re-fetched while it is open.
 */
type TDocumentSourceBase = {
  /** Stable identity, used as a React key and to tell two sources apart in the compare picker. */
  id: string;
  /** File name shown in the header and used to guess the type when `mimeType` is missing. */
  name: string;
  /** Declared mime type; the viewer still checks the name's extension when it is empty or generic. */
  mimeType?: string;
  /** Where "Download" points. Defaults to `url` for URL sources. */
  downloadUrl?: string;
  /** A ready-made thumbnail (e.g. from SharePoint) shown for formats the viewer cannot render. */
  thumbnailUrl?: string;
  /** Secondary line under the name, e.g. "Version 2 · uploaded by …". */
  caption?: string;
};

export type TDocumentUrlSource = TDocumentSourceBase & { url: string; fetchFile?: undefined };

export type TDocumentFetchSource = TDocumentSourceBase & {
  url?: undefined;
  fetchFile: (signal: AbortSignal) => Promise<Blob | ArrayBuffer>;
};

export type TDocumentSource = TDocumentUrlSource | TDocumentFetchSource;

/** How the viewer renders a file: PDF through pdf.js, images through `<img>`, anything else not at all. */
export type TPreviewKind = "pdf" | "image" | "unsupported";

/** The size of the rendered page in CSS pixels and the scale it was drawn at. */
export type TRenderedPage = {
  /** 1-based page number; always 1 for images. */
  page: number;
  pageCount: number;
  scale: number;
  width: number;
  height: number;
};

/**
 * Renders a layer over the page, positioned to cover it exactly (`absolute inset-0`). Annotations
 * (C3) plug in here; coordinates relative to `width` and `height` scale with the page.
 */
export type TDocumentOverlayRenderer = (page: TRenderedPage) => ReactNode;
