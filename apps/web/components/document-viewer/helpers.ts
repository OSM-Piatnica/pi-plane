/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TPreviewKind } from "./types";

// Behaviour follows the Studio opakowań v5 prototype (art-viewer.js): zoom steps of 25 %, from
// 25 % to 400 %, "Fit" leaves a 20 px margin on every side, and a rendered canvas never exceeds
// 8192 px per side or 16 megapixels.

export const ZOOM_STEP = 0.25;
export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 4;
/** Space kept around the page in "Fit", on both axes together (20 px per side). */
export const FIT_MARGIN = 40;
const MIN_FIT_SCALE = 0.02;
const MAX_CANVAS_SIDE = 8192;
const MAX_CANVAS_PIXELS = 16_000_000;

const IMAGE_MIME_TYPES: Record<string, string[]> = {
  "image/jpeg": ["jpg", "jpeg"],
  "image/jpg": ["jpg", "jpeg"],
  "image/png": ["png"],
  "image/webp": ["webp"],
  "image/gif": ["gif"],
  // SVG is only ever rendered through <img>, which runs no scripts and loads nothing external.
  "image/svg+xml": ["svg"],
};
const IMAGE_EXTENSIONS = new Set(Object.values(IMAGE_MIME_TYPES).flat());
const GENERIC_MIME_TYPES = new Set(["", "application/octet-stream", "binary/octet-stream"]);

const extensionOf = (name: string): string => {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot + 1).toLowerCase() : "";
};

/**
 * How a file is previewed. The declared mime type decides when it is specific; when it is missing
 * or generic, the name's extension does. A specific type that is neither a PDF nor a known image
 * (an Office file, a PSD, TIFF, AI) is not previewed, whatever the extension says.
 */
export const getPreviewKind = (mimeType: string | undefined, name: string): TPreviewKind => {
  const type = (mimeType ?? "").split(";")[0].trim().toLowerCase();
  if (!GENERIC_MIME_TYPES.has(type)) {
    if (type === "application/pdf") return "pdf";
    if (type in IMAGE_MIME_TYPES) return "image";
    return "unsupported";
  }
  const extension = extensionOf(name);
  if (extension === "pdf") return "pdf";
  if (IMAGE_EXTENSIONS.has(extension)) return "image";
  return "unsupported";
};

export const isPreviewable = (mimeType: string | undefined, name: string): boolean =>
  getPreviewKind(mimeType, name) !== "unsupported";

export type TSize = { width: number; height: number };

/** The scale at which the whole page fits the visible area, margin included. */
export const getFitScale = (area: TSize, natural: TSize): number => {
  if (natural.width <= 0 || natural.height <= 0) return 1;
  const scale = Math.min((area.width - FIT_MARGIN) / natural.width, (area.height - FIT_MARGIN) / natural.height);
  return Number.isFinite(scale) ? Math.max(MIN_FIT_SCALE, scale) : 1;
};

export const clampZoom = (zoom: number): number => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));

/** One zoom step from the current scale; from "Fit" it starts at the fitted scale. */
export const stepZoom = (currentScale: number, direction: 1 | -1): number =>
  clampZoom(currentScale + direction * ZOOM_STEP);

/**
 * The pixel density to draw a PDF page at: the display scale times the device pixel ratio, capped
 * so the canvas stays within what browsers can allocate.
 */
export const getRenderResolution = (scale: number, devicePixelRatio: number, natural: TSize): number => {
  const wanted = scale * (devicePixelRatio > 0 ? devicePixelRatio : 1);
  if (natural.width <= 0 || natural.height <= 0) return wanted;
  return Math.min(
    wanted,
    MAX_CANVAS_SIDE / natural.width,
    MAX_CANVAS_SIDE / natural.height,
    Math.sqrt(MAX_CANVAS_PIXELS / (natural.width * natural.height))
  );
};

export const clampPage = (page: number, pageCount: number): number =>
  Math.min(Math.max(1, Math.trunc(page) || 1), Math.max(1, pageCount));

/** Whole percent shown in the zoom read-out. */
export const toPercent = (scale: number): number => Math.round(scale * 100);

/**
 * Credentials mode for fetching a file. The API sets its session cookie on its own origin; when that
 * is the page's origin, `same-origin` sends the cookie to the API and not to the storage the API
 * redirects to, which then needs no credentialed CORS. A separate API origin (local development)
 * needs `include`.
 */
export const getFetchCredentials = (url: string, pageOrigin: string): RequestCredentials => {
  try {
    return new URL(url, pageOrigin).origin === pageOrigin ? "same-origin" : "include";
  } catch {
    return "same-origin";
  }
};
