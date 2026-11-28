/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { PDFDocumentProxy } from "pdfjs-dist";

// pdf.js is loaded on first use only, so it stays out of the main bundle. The legacy build is
// used because the modern one relies on very recent JavaScript (Map.getOrInsertComputed,
// Math.sumPrecise) that current Safari and older Chromium releases lack.
type TPdfjs = typeof import("pdfjs-dist/legacy/build/pdf.mjs");

let pdfjsPromise: Promise<TPdfjs> | undefined;

export const loadPdfjs = (): Promise<TPdfjs> => {
  pdfjsPromise ??= Promise.all([
    import("pdfjs-dist/legacy/build/pdf.mjs"),
    import("pdfjs-dist/legacy/build/pdf.worker.min.mjs?url"),
  ])
    .then(([pdfjs, worker]) => {
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
      return pdfjs;
    })
    .catch((error: unknown) => {
      // Let the next open try again (e.g. after a deploy replaced the chunk).
      pdfjsPromise = undefined;
      throw error;
    });
  return pdfjsPromise;
};

/**
 * Base URL of the pdf.js data files (CMaps, standard fonts, ICC profiles, wasm decoders). The
 * `pdfjsAssets` Vite plugin copies them to `pdfjs/<version>/` next to the app's own assets.
 */
export const getPdfjsDataUrl = (version: string, folder: "cmaps" | "iccs" | "standard_fonts" | "wasm"): string =>
  new URL(`${import.meta.env.BASE_URL}pdfjs/${version}/${folder}/`, window.location.origin).href;

/** Opens a PDF from its bytes. The caller owns the returned document and must `destroy()` it. */
export const openPdf = async (data: ArrayBuffer): Promise<PDFDocumentProxy> => {
  const pdfjs = await loadPdfjs();
  return pdfjs.getDocument({
    data: new Uint8Array(data),
    cMapUrl: getPdfjsDataUrl(pdfjs.version, "cmaps"),
    iccUrl: getPdfjsDataUrl(pdfjs.version, "iccs"),
    standardFontDataUrl: getPdfjsDataUrl(pdfjs.version, "standard_fonts"),
    wasmUrl: getPdfjsDataUrl(pdfjs.version, "wasm"),
    // Viewing only: no form scripting, no XFA forms.
    enableXfa: false,
  }).promise;
};

/** Frees a document and its worker-side state (pdf.js 6 moved `destroy()` to the loading task). */
export const destroyPdf = (pdf: PDFDocumentProxy): void => {
  pdf.loadingTask.destroy().catch(() => undefined);
};

export const isRenderingCancelled = (error: unknown): boolean =>
  error instanceof Error && error.name === "RenderingCancelledException";
