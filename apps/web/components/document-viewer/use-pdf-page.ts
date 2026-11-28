/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";
import { getRenderResolution, stepZoom } from "./helpers";
import { isRenderingCancelled } from "./pdfjs";

/** The page object of `pageNumber`, or undefined while it loads (never a stale page). */
export const usePdfPage = (
  pdf: PDFDocumentProxy | undefined,
  pageNumber: number,
  onError: () => void
): PDFPageProxy | undefined => {
  const [pdfPage, setPdfPage] = useState<PDFPageProxy | undefined>(undefined);
  useEffect(() => {
    if (!pdf) return;
    let cancelled = false;
    const load = async () => {
      try {
        const proxy = await pdf.getPage(pageNumber);
        if (!cancelled) setPdfPage(proxy);
      } catch {
        if (!cancelled) onError();
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
    // onError only reports; a new function must not reload the page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pdf, pageNumber]);
  return pdf && pdfPage?.pageNumber === pageNumber ? pdfPage : undefined;
};

/** Draws a PDF page into the canvas at `scale`; a newer draw cancels the one in progress. */
export const usePdfPageCanvas = (
  canvasRef: RefObject<HTMLCanvasElement | null>,
  page: PDFPageProxy | undefined,
  scale: number,
  enabled: boolean,
  onError: () => void
) => {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!page || !canvas || !enabled) return;
    const box = page.getViewport({ scale: 1 });
    const resolution = getRenderResolution(scale, window.devicePixelRatio, { width: box.width, height: box.height });
    const viewport = page.getViewport({ scale: resolution });
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const task = page.render({ canvas, viewport });
    task.promise.catch((error: unknown) => {
      if (!isRenderingCancelled(error)) onError();
    });
    return () => task.cancel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasRef, page, scale, enabled]);
};

/**
 * Ctrl (or Cmd) + wheel zooms the element by one step. It needs a non-passive listener to stop the
 * browser's own page zoom.
 */
export const useCtrlWheelZoom = (element: HTMLElement | null, scale: number, onZoom: (scale: number) => void) => {
  const latest = useRef({ scale, onZoom });
  useEffect(() => {
    latest.current = { scale, onZoom };
  }, [scale, onZoom]);
  useEffect(() => {
    if (!element) return;
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      latest.current.onZoom(stepZoom(latest.current.scale, event.deltaY < 0 ? 1 : -1));
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, [element]);
};
