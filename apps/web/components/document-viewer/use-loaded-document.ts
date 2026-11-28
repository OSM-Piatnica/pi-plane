/**
 * Copyright (c) 2026-present Okręgowa Spółdzielnia Mleczarska w Piątnicy
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { getFetchCredentials, getPreviewKind } from "./helpers";
import { destroyPdf, openPdf } from "./pdfjs";
import type { TDocumentSource } from "./types";

export type TLoadedDocument =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "unsupported" }
  | { status: "pdf"; pdf: PDFDocumentProxy }
  | { status: "image"; src: string };

const toArrayBuffer = async (data: Blob | ArrayBuffer): Promise<ArrayBuffer> =>
  data instanceof ArrayBuffer ? data : data.arrayBuffer();

/** The original bytes of a source, from its fetch function or its URL. */
export const fetchSourceBytes = async (source: TDocumentSource, signal: AbortSignal): Promise<ArrayBuffer> => {
  if (source.fetchFile) return toArrayBuffer(await source.fetchFile(signal));
  const response = await fetch(source.url, {
    credentials: getFetchCredentials(source.url, window.location.origin),
    signal,
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.arrayBuffer();
};

/**
 * Loads a source for display. PDFs are opened with pdf.js (destroyed again on unmount or when the
 * source changes); images from a URL are shown from that URL, and images from a fetch function
 * through a short-lived object URL.
 */
export const useLoadedDocument = (source: TDocumentSource): TLoadedDocument => {
  const kind = getPreviewKind(source.mimeType, source.name);
  const needsFetch = kind === "pdf" || (kind === "image" && !source.url);
  // Keyed by source id, so a stale result is never shown for the next source.
  const [loaded, setLoaded] = useState<{ id: string; value: TLoadedDocument } | undefined>(undefined);

  // react-doctor-disable-next-line no-fetch-in-effect -- the result is a live pdf.js document that must be destroyed when the viewer closes, not a cacheable value for SWR
  useEffect(() => {
    if (!needsFetch) return;
    const controller = new AbortController();
    let pdf: PDFDocumentProxy | undefined;
    let objectUrl: string | undefined;
    const settle = (value: TLoadedDocument) => {
      if (!controller.signal.aborted) setLoaded({ id: source.id, value });
    };

    (async () => {
      try {
        const bytes = await fetchSourceBytes(source, controller.signal);
        if (controller.signal.aborted) return;
        if (kind === "image") {
          // The blob gets the declared type so an SVG still renders through <img>.
          // react-doctor-disable-next-line no-create-object-url-without-revoke -- revoked in this effect's cleanup below
          objectUrl = URL.createObjectURL(new Blob([bytes], { type: source.mimeType || "" }));
          settle({ status: "image", src: objectUrl });
          return;
        }
        pdf = await openPdf(bytes);
        if (controller.signal.aborted) {
          destroyPdf(pdf);
          return;
        }
        settle({ status: "pdf", pdf });
      } catch (error) {
        settle({ status: "error", error });
      }
    })();

    return () => {
      controller.abort();
      if (pdf) destroyPdf(pdf);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
    // A source is identified by its id; a new object with the same id is the same file.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source.id, kind, needsFetch]);

  if (kind === "unsupported") return { status: "unsupported" };
  if (kind === "image" && source.url) return { status: "image", src: source.url };
  return loaded?.id === source.id ? loaded.value : { status: "loading" };
};
