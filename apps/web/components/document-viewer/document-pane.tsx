/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { RefObject } from "react";
import type { PDFDocumentProxy, PDFPageProxy } from "pdfjs-dist";
import { useTranslation } from "@plane/i18n";
import { DocumentPaneToolbar } from "./document-pane-toolbar";
import type { TZoom } from "./document-pane-toolbar";
import { clampPage, getFitScale } from "./helpers";
import type { TSize } from "./helpers";
import type { TDocumentOverlayRenderer, TDocumentSource, TRenderedPage } from "./types";
import { useLoadedDocument } from "./use-loaded-document";
import type { TLoadedDocument } from "./use-loaded-document";
import { useCtrlWheelZoom, usePdfPage, usePdfPageCanvas } from "./use-pdf-page";

type TDocumentPaneProps = {
  source: TDocumentSource;
  /** Renders over the page; annotations (C3) go here. */
  renderOverlay?: TDocumentOverlayRenderer;
};

const useElementSize = (element: HTMLElement | null): TSize => {
  const [size, setSize] = useState<TSize>({ width: 0, height: 0 });
  useEffect(() => {
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setSize((previous) => (previous.width === width && previous.height === height ? previous : { width, height }));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);
  return size;
};

/** The status line under the page, as a translation key, or undefined when there is nothing to say. */
const getMessageKey = (loaded: TLoadedDocument, failed: boolean, ready: boolean): string | undefined => {
  if (failed) return "document_viewer.error";
  if (loaded.status === "unsupported") return "document_viewer.unsupported";
  if (!ready) return "document_viewer.loading";
  return undefined;
};

/** Size of the page at 100 %: from pdf.js for PDFs, from the loaded <img> for images. */
const getNaturalSize = (
  pdf: PDFDocumentProxy | undefined,
  pdfPage: PDFPageProxy | undefined,
  imageSize: TSize | undefined
): TSize | undefined => {
  if (!pdf) return imageSize;
  if (!pdfPage) return undefined;
  const box = pdfPage.getViewport({ scale: 1 });
  return { width: box.width, height: box.height };
};

/** The display scale and, once both the page and the visible area have a size, the rendered page. */
const getGeometry = (
  natural: TSize | undefined,
  area: TSize,
  zoom: TZoom,
  page: number,
  pageCount: number
): { scale: number; rendered: TRenderedPage | undefined } => {
  if (!natural) return { scale: zoom.fit ? 1 : zoom.scale, rendered: undefined };
  const scale = zoom.fit ? getFitScale(area, natural) : zoom.scale;
  if (area.width <= 0) return { scale, rendered: undefined };
  return {
    scale,
    rendered: { page, pageCount, scale, width: natural.width * scale, height: natural.height * scale },
  };
};

type TDocumentStageProps = {
  loaded: Extract<TLoadedDocument, { status: "pdf" | "image" }>;
  name: string;
  canvasRef: RefObject<HTMLCanvasElement | null>;
  /** The page's rendered size; undefined while it is not known yet (the stage stays hidden). */
  rendered: TRenderedPage | undefined;
  renderOverlay?: TDocumentOverlayRenderer;
  onImageSize: (size: TSize) => void;
  onError: () => void;
};

/** The page itself: a canvas for PDFs, an <img> for images, and the overlay layer above it. */
function DocumentStage(props: TDocumentStageProps) {
  const { loaded, name, canvasRef, rendered, renderOverlay, onImageSize, onError } = props;
  return (
    <div
      className="relative mx-auto shrink-0 bg-white shadow-raised-200"
      style={rendered ? { width: rendered.width, height: rendered.height } : { visibility: "hidden" }}
    >
      {loaded.status === "pdf" ? (
        <canvas ref={canvasRef} className="block size-full" />
      ) : (
        // SVG is shown through <img> only, never inlined, so it cannot run scripts.
        <img
          src={loaded.src}
          alt={name}
          draggable={false}
          className="block size-full max-w-none object-fill"
          onLoad={(event) => {
            const { naturalWidth, naturalHeight } = event.currentTarget;
            // An SVG without intrinsic size reports 0; give it a square box rather than none.
            onImageSize({ width: naturalWidth || 1000, height: naturalHeight || 1000 });
          }}
          onError={onError}
        />
      )}
      {rendered && renderOverlay && <div className="absolute inset-0">{renderOverlay(rendered)}</div>}
    </div>
  );
}

/**
 * One document panel: zoom (minus, plus, fit, 100 %, Ctrl + wheel), page picker for PDFs, and a
 * scrollable stage that holds the rendered page and an optional overlay layer. Each panel keeps its
 * own page and zoom, so two of them compare independently.
 */
export function DocumentPane(props: TDocumentPaneProps) {
  const { source, renderOverlay } = props;
  const { t } = useTranslation();
  const loaded = useLoadedDocument(source);
  const [viewport, setViewport] = useState<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const area = useElementSize(viewport);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState<TZoom>({ fit: true });
  const [imageSize, setImageSize] = useState<TSize | undefined>(undefined);
  const [renderFailed, setRenderFailed] = useState(false);
  const fail = useCallback(() => setRenderFailed(true), []);

  const pdf = loaded.status === "pdf" ? loaded.pdf : undefined;
  const pageCount = pdf?.numPages ?? 1;
  const currentPage = clampPage(page, pageCount);
  const pdfPage = usePdfPage(pdf, currentPage, fail);

  const { scale, rendered } = getGeometry(getNaturalSize(pdf, pdfPage, imageSize), area, zoom, currentPage, pageCount);
  const ready = Boolean(rendered);

  usePdfPageCanvas(canvasRef, pdfPage, scale, ready, fail);
  const zoomTo = useCallback((next: number) => setZoom({ fit: false, scale: next }), []);
  useCtrlWheelZoom(viewport, scale, zoomTo);

  const changePage = (delta: number) => {
    setPage(clampPage(currentPage + delta, pageCount));
    viewport?.scrollTo(0, 0);
  };

  const failed = loaded.status === "error" || renderFailed;
  const messageKey = getMessageKey(loaded, failed, ready);

  return (
    <section className="flex h-full min-h-0 min-w-0 flex-col" aria-label={source.name}>
      <DocumentPaneToolbar
        scale={scale}
        zoom={zoom}
        ready={ready}
        disabled={!ready || failed}
        onZoomChange={setZoom}
        pages={pdf ? { current: currentPage, count: pageCount, onChange: changePage } : undefined}
      />

      {/* The scroll region is focusable so keyboard users can scroll a zoomed page. */}
      <div
        ref={setViewport}
        // oxlint-disable-next-line jsx-a11y/no-noninteractive-tabindex
        tabIndex={0}
        aria-label={t("document_viewer.viewport_label", { name: source.name })}
        className="relative min-h-0 flex-1 overflow-auto bg-layer-1 p-5"
      >
        {loaded.status === "unsupported" && source.thumbnailUrl && (
          <img src={source.thumbnailUrl} alt={source.name} className="mx-auto max-h-full max-w-full object-contain" />
        )}
        {!failed && (loaded.status === "pdf" || loaded.status === "image") && (
          <DocumentStage
            loaded={loaded}
            name={source.name}
            canvasRef={canvasRef}
            rendered={rendered}
            renderOverlay={renderOverlay}
            onImageSize={setImageSize}
            onError={fail}
          />
        )}
      </div>
      {messageKey && (
        <p role="status" className="border-t border-subtle px-3 py-2 text-12 text-secondary">
          {t(messageKey)}
        </p>
      )}
    </section>
  );
}
