/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { getFileExtension } from "@plane/utils";
import { isRenderingCancelled } from "./pdfjs";
import type { TDocumentSource } from "./types";
import { useLoadedDocument } from "./use-loaded-document";

type TDocumentThumbnailProps = {
  source: TDocumentSource;
  /** Longest side of the rendered thumbnail in CSS pixels. */
  size?: number;
};

/**
 * The first page of a PDF, or the image itself, scaled into a square box. Formats the viewer
 * cannot render show the source's own thumbnail when it has one, and the extension otherwise.
 */
export function DocumentThumbnail(props: TDocumentThumbnailProps) {
  const { source, size = 160 } = props;
  const loaded = useLoadedDocument(source);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [failed, setFailed] = useState(false);
  const pdf = loaded.status === "pdf" ? loaded.pdf : undefined;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!pdf || !canvas) return;
    let cancel: (() => void) | undefined;
    let cancelled = false;
    pdf
      .getPage(1)
      .then((page) => {
        if (cancelled) return;
        const natural = page.getViewport({ scale: 1 });
        const scale = (size * (window.devicePixelRatio || 1)) / Math.max(natural.width, natural.height);
        const viewport = page.getViewport({ scale });
        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        const task = page.render({ canvas, viewport });
        cancel = () => task.cancel();
        return task.promise;
      })
      .catch((error: unknown) => {
        if (!cancelled && !isRenderingCancelled(error)) setFailed(true);
      });
    return () => {
      cancelled = true;
      cancel?.();
    };
  }, [pdf, size]);

  const box = "flex items-center justify-center overflow-hidden rounded-sm border border-subtle bg-layer-1";
  const fallback = (
    <span className="text-11 font-medium text-tertiary uppercase">{getFileExtension(source.name) || "?"}</span>
  );

  let content = fallback;
  if (!failed && loaded.status === "pdf")
    content = <canvas ref={canvasRef} className="max-h-full max-w-full object-contain" />;
  else if (!failed && loaded.status === "image")
    content = (
      <img
        src={loaded.src}
        alt=""
        className="max-h-full max-w-full object-contain"
        loading="lazy"
        onError={() => setFailed(true)}
      />
    );
  else if (loaded.status === "unsupported" && source.thumbnailUrl)
    content = <img src={source.thumbnailUrl} alt="" className="max-h-full max-w-full object-contain" loading="lazy" />;

  return (
    <div className={box} style={{ width: size, height: size }} aria-hidden>
      {content}
    </div>
  );
}
